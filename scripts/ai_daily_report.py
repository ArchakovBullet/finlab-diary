#!/usr/bin/env python3
"""ai_daily_report.py — ежедневный отчёт через VseGPT + email.
from ai_data_context import get_robot_state_v4, get_trades_history_v4, get_signals_summary_v4, get_index_divergence, get_index_algopack


Читает robot.log за 24ч, robot_state.json, pairs_robot.db.
Отправляет в DeepSeek, сохраняет в logs/ai_daily/, шлёт email.
"""
import argparse
import json
from ai_data_context import get_index_divergence, get_index_algopack
import os
import smtplib
import sqlite3
import sys
from datetime import datetime, timedelta
import subprocess
from email.mime.text import MIMEText
from email.header import Header
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path('/root/finlab')
load_dotenv(ROOT / '.env')

VSEGPT_URL = 'https://api.vsegpt.ru/v1/chat/completions'
DEFAULT_MODEL = 'deepseek/deepseek-chat'
LOG_FILE = ROOT / 'robots' / 'robot.log'
STATE_FILE = ROOT / 'robots' / 'robot_state.json'
DB_FILE = ROOT / 'robots' / 'pairs_robot.db'
CONTEXT_FILE = ROOT / 'scripts' / 'ai_context.md'
OUT_DIR = ROOT / 'logs' / 'ai_daily'


def read_log_today(path, hours=24):
    if not path.exists():
        return ''
    cutoff = datetime.now() - timedelta(hours=hours)
    lines = []
    with open(path, 'r', errors='replace') as f:
        for line in f:
            # Простая эвристика: если строка начинается с даты — проверяем
            lines.append(line)
    # Возвращаем последние 2000 строк (за сутки обычно хватает)
    return ''.join(lines[-2000:])


def read_state():
    if not STATE_FILE.exists():
        return {}
    try:
        return json.load(open(STATE_FILE))
    except Exception:
        return {}


def read_db_stats(hours=24):
    if not DB_FILE.exists():
        return {}
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cutoff = (datetime.now() - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
        cur.execute("SELECT COUNT(*) FROM positions WHERE entry_time >= ?", (cutoff,))
        n_opened = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM positions WHERE status='CLOSED' AND exit_time >= ?", (cutoff,))
        n_closed = cur.fetchone()[0]
        cur.execute("SELECT COALESCE(SUM(pnl), 0) FROM positions WHERE status='CLOSED' AND exit_time >= ?", (cutoff,))
        pnl = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM trades WHERE time >= ?", (cutoff,))
        n_trades = cur.fetchone()[0]
        conn.close()
        return {'opened': n_opened, 'closed': n_closed, 'pnl': pnl, 'trades': n_trades}
    except Exception as e:
        return {'error': str(e)}


def read_context():
    if CONTEXT_FILE.exists():
        return CONTEXT_FILE.read_text(encoding='utf-8')
    return ''


def call_vsegpt(model, system_prompt, user_content, api_key):
    r = requests.post(
        VSEGPT_URL,
        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
        json={
            'model': model,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_content},
            ],
            'max_tokens': 2000,
            'temperature': 0.2,
        },
        timeout=90,
    )
    return r


def send_vk(subject, body):
    """VK-fallback при ошибке email."""
    vk_token = os.getenv('VK_TOKEN', '')
    vk_group = os.getenv('VK_GROUP_ID', '')
    if not vk_token or not vk_group:
        return False
    try:
        import vk_api
        vk = vk_api.VkApi(token=vk_token).get_api()
        msg = f'{subject}\n\n{body[:3500]}'  # VK лимит ~4096
        vk.messages.send(
            peer_id=int(vk_group),
            message=msg,
            random_id=int(datetime.now().timestamp() * 1000),
        )
        return True
    except Exception as e:
        print(f'❌ VK ошибка: {e}')
        return False


def send_email(subject, body, email_from, email_pass, email_to):
    import socket
    # Форсируем IPv4 (сервер без глобального IPv6)
    _orig = socket.getaddrinfo
    socket.getaddrinfo = lambda host, port, family=0, type=0, proto=0, flags=0: _orig(host, port, socket.AF_INET, type, proto, flags)
    try:
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = Header(subject, 'utf-8')
        msg['From'] = email_from
        msg['To'] = email_to
        # Пробуем 587 (STARTTLS)
        with smtplib.SMTP('smtp.yandex.ru', 587, timeout=30) as s:
            s.starttls()
            s.login(email_from, email_pass)
            s.send_message(msg)
    finally:
        socket.getaddrinfo = _orig


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', default=DEFAULT_MODEL)
    ap.add_argument('--hours', type=int, default=24)
    ap.add_argument('--debug-content', action='store_true', help='print user_content (debug)')
    ap.add_argument('--no-email', action='store_true')
    args = ap.parse_args()

    api_key = os.getenv('VSEGPT_API_KEY', '')
    email_from = os.getenv('YANDEX_EMAIL', '')
    email_pass = os.getenv('YANDEX_APP_PASSWORD', '')
    email_to = os.getenv('REPORT_EMAIL_TO', email_from)

    if not api_key:
        print('ERROR: VSEGPT_API_KEY не задан')
        sys.exit(1)

    log_text = read_log_today(LOG_FILE, args.hours)
    state = read_state()
    db_stats = read_db_stats(args.hours)
    context = read_context()

    # Даты для отчёта
    report_date = datetime.now()
    data_date = report_date  # текущий день (вечерний отчёт)
    report_date_str = report_date.strftime('%Y-%m-%d')
    data_date_str = data_date.strftime('%Y-%m-%d')
    report_date_full = report_date.strftime('%d.%m.%Y')
    report_time = report_date.strftime('%H:%M')
    data_date_full = data_date.strftime('%d.%m.%Y')

    # Собираем реальный контекст данных
    try:
        _dc = subprocess.check_output(
            ['/root/finlab/venv/bin/python', '/root/finlab/scripts/ai_data_context.py'],
            text=True, timeout=30,
        )
    except Exception as e:
        _dc = f'{{"error": "{e}"}}'

    user_content = f"""=== ДАННЫЕ (РЕАЛЬНЫЕ, ИСТОЧНИК ИСТИНЫ) ===
{_dc}

=== robot_state.json (текущий) ===
{json.dumps(state, ensure_ascii=False, indent=2)}

=== DB stats (за {args.hours}ч) ===
{json.dumps(db_stats, ensure_ascii=False, indent=2)}

=== Контекст проекта ===
{context}

=== robot.log (ИСТОРИЧЕСКИЕ ЛОГИ, могут быть устаревшими) ===
ВНИМАНИЕ: логи могут содержать устаревшие данные. Источник истины — раздел "ДАННЫЕ" выше.
{log_text}
"""

    # === Divergence SBER/GAZP vs MOEXFN (в user_content — AI видит и анализирует) ===
    try:
        _idx = get_index_divergence()
        if _idx:
            _lines = ["\n\n=== DIVERGENCE SBER/GAZP vs MOEXFN (D1) ===",
                      "Проанализируй: есть ли сигнал (LONG/SHORT при divergence)? Предложи гипотезы (не внедрять без walk-forward).",
                      "| Тикер | ret_stock | ret_sector | divergence | z | signal | date |",
                      "|---|---|---|---|---|---|---|"]
            for _t, _d in _idx.items():
                _lines.append(f"| {_t} | {_d.get('ret_stock')} | {_d.get('ret_sector')} | {_d.get('divergence')} | {_d.get('z')} | {_d.get('signal')} | {_d.get('date')} |")
            user_content = user_content + "\n".join(_lines)
    except Exception as _e:
        user_content = user_content + f"\n[divergence block error: {_e}]\n"

    # === Algopack-фон SBER/GAZP (FutOI, HI2, MegaAlerts, TradeStats, RVI) — price+time+delta ===
    try:
        _apk = get_index_algopack()
        if _apk:
            _lines = ["\n\n=== ALGOPACK-ФОН SBER/GAZP (price + time + delta) ===",
                      "Проанализируй СВЯЗИ: цена vs FutOI (физ/юр), цена vs HI2 (buy/sell/netflow), цена vs MegaAlerts (sell-аномалии), цена vs TradeStats (disb/vol), RVI. Ищи: divergence, extremes, развороты. Предложи гипотезы для walk-forward (не внедрять без WF)."]
            for _t, _d in _apk.items():
                _lines.append(f"\n--- {_t} ---")
                _f = _d.get("futoi") or {}
                _h = _d.get("hi2") or {}
                _m = _d.get("mega") or {}
                _ts = _d.get("tradestats") or {}
                _r = _d.get("rvi") or {}
                _lines.append(f"FutOI ({_f.get('hour')}): price={_f.get('price')} delta_1h={_f.get('delta_1h')} fiz_buy={_f.get('fiz_buy_ratio')} yur_buy={_f.get('yur_buy_ratio')}")
                _lines.append(f"HI2 ({_h.get('tradedate')} {_h.get('tradetime')}): buy={_h.get('hhi_buy')} sell={_h.get('hhi_sell')} netflow_buy={_h.get('hhi_netflow_buy')} netflow_sell={_h.get('hhi_netflow_sell')} price_at_time={_h.get('price_at_time')} price_now={_h.get('price_now')} delta_1d={_h.get('delta_1d')}")
                _mega_items = _m.get("items") or []
                if _mega_items:
                    _lines.append(f"MegaAlerts ({_m.get('count')}): " + "; ".join([f"{it.get('tradedate')} {it.get('tradetime')} price={it.get('price')} val={it.get('value')} type={it.get('type')}" for it in _mega_items]))
                else:
                    _lines.append(f"MegaAlerts: 0")
                _lines.append(f"TradeStats ({_ts.get('tradedate')} {_ts.get('tradetime')}): price={_ts.get('price')} price_prev={_ts.get('price_prev')} delta_1d={_ts.get('delta_1d')} disb={_ts.get('disb')} vol={_ts.get('vol')}")
                _lines.append(f"RVI ({_r.get('begin')}): rvi={_r.get('rvi')} price_at_rvi_date={_r.get('price_at_rvi_date')}")
            user_content = user_content + "\n".join(_lines)
    except Exception as _e:
        user_content = user_content + f"\n[algopack block error: {_e}]\n"


    # === Контекст: enabled-пары + что уже сделано (чтобы AI не советовал сделанное) ===
    try:
        _cfg_v2 = json.load(open("/root/finlab/FinLabPy/My_Indicators/pairs_config_v2.json"))
        _cfg_v4 = json.load(open("/root/finlab/FinLabPy/My_Indicators/pairs_config_test.json"))
        _en2 = [p for p,c in _cfg_v2.get("pairs",{}).items() if c.get("enabled")]
        _dis2 = [p for p,c in _cfg_v2.get("pairs",{}).items() if not c.get("enabled")]
        _en4 = [p for p,c in _cfg_v4.get("pairs",{}).items() if c.get("enabled")]
        _dis4 = [p for p,c in _cfg_v4.get("pairs",{}).items() if not c.get("enabled")]
        _ctx_lines = ["\n\n=== КОНТЕКСТ: enabled-пары + что уже сделано (НЕ советуй уже сделанное) ===",
                      f"v2 enabled: {_en2}",
                      f"v2 disabled: {_dis2}",
                      f"v4 enabled: {_en4}",
                      f"v4 disabled: {_dis4}",
                      "Уже сделано (НЕ предлагать как новое):",
                      "- MAX_HOLD для M10 — проверен, НЕ работает (Sharpe хуже). Закрыто.",
                      "- freshness DEAD_TICKERS — сделано (oldest 433 → 6ч). Закрыто.",
                      "- exit_z=0.3 / max_z=3.5 — внедрены в v4 (тест, наблюдение 1–2 недели).",
                      "- LKOH-HYDR_H1 — disabled (акция+акция). SFIN-SH_M10 — disabled (карантин corr<0.5).",
                      "- index_robot_v1 — запущен (divergence SBER/GAZP); сделки: см. позиции.",
                      "Если рекомендуешь что-то из этого — пометь как 'уже сделано', не как новое."]
        # индекс-сделки
        try:
            import sqlite3 as _sq
            _c = _sq.connect("/root/finlab/robots/index_robot_v1.db")
            _cl = _sq.connect("/root/finlab/robots/index_robot_v1.db")
            _cur = _c.cursor()
            _cur.execute("select count(*), coalesce(sum(pnl),0) from positions where status='CLOSED'")
            _n, _pnl = _cur.fetchone()
            _cur.execute("select count(*) from positions where status='OPEN'")
            _op = _cur.fetchone()[0]
            _ctx_lines.append(f"index_v1: закрыто={_n}, PnL={_pnl:+.2f}₽, открыто={_op}")
            _c.close()
        except Exception:
            pass
        user_content = user_content + "\n".join(_ctx_lines)
    except Exception as _e:
        user_content = user_content + f"\n[context block error: {_e}]\n"
    system_prompt = """Ты — аналитик FinLab. Составь ЕЖЕДНЕВНЫЙ отчёт.

ВАЖНО: Раздел "ДАННЫЕ (РЕАЛЬНЫЕ)" — ЭТО ИСТОЧНИК ИСТИНЫ. Он содержит:
- legend — ЛЕГЕНДА v1/v2/v3 (роботы, поля signals, фильтры);
- freshness (реальная свежесть файлов M10/H1/H4/D1);
- config (v1) и config_v2 (v2) — РАЗДЕЛЬНО;
- quarantine (реальные карантины);
- algopack (свежесть);
- cron (актуальное расписание).

Логи робота (robot.log) — ИСТОРИЧЕСКИЕ. Они могут содержать устаревшие данные.

ПРАВИЛО 1: РАЗЛИЧАЙ v1, v2 и v3. Указывай [v1], [v2] или [v3] в каждом пункте. НЕ СМЕШИВАЙ.
ПРАВИЛО 2: если данные и логи противоречат — ВЕРЬ ДАННЫМ.
ПРАВИЛО 3: если данных нет — НЕ ДОДУМЫВАЙ. Напиши "нет данных".
ПРАВИЛО 4: проверяй поля — z_entry (вход) vs z_exit (выход), entry_z (правило) vs z_entry (факт).
ПРАВИЛО 5: раздел "rules" содержит правила торговли — используй их для проверки.
ПРИМЕР: если в config GLDRUBF-GD_H4 enabled=False, а в логах он был enabled — верь config.
ПРИМЕР: если в данных H4: 297/297 свежих, а в логах "age=44.7ч" — верь данным.
ПРИМЕР: если в config_v2 BR-GAZPF_H4 enabled=False, а в config enabled=True — верь config_v2 для v2.

Формат:
# Daily Report {report_date}

Отчёт сформирован: {report_date_full}, {report_time} МСК
Анализ за {data_date_full} (данные на {report_time} МСК, все TF закрыты)

## PnL и сделки
- Открыто, закрыто, PnL, WR.

## ML-фильтр
- PASS/BLOCK по парам.

## Аномалии
- Что не так.

## Лучшие и худшие сделки
ВАЖНО: в trades_history есть z_entry (z на входе) и z_exit (z на выходе).
- Вход по правилу: |z_entry| >= entry_z (2.0-2.5).
- Выход по правилу: |z_exit| <= exit_z (0.5).
- Топ-3 прибыльных: pair, z_entry, z_exit, PnL, время.
- Топ-3 убыточных: то же.
- Паттерны: что общего у прибыльных? Что у убыточных?
- Пример: если z_entry=-3.55 → вход корректен. Если z_exit=+0.47 → выход корректен.

## Рекомендации
- 1-3 конкретных.

Отвечай кратко, по делу, на русском."""

    print(f'📤 Отправка в VseGPT ({args.model})...')
    system_prompt_fmt = system_prompt.format(
        report_date=report_date_str,
        report_date_full=report_date_full,
        data_date_full=data_date_full,
        report_time=report_time,
        hours=args.hours,
    )
    if "--debug-content" in sys.argv:
        print(user_content)
    r = call_vsegpt(args.model, system_prompt_fmt, user_content, api_key)
    if r.status_code != 200:
        print(f'ERROR: HTTP {r.status_code}')
        print(r.text[:500])
        sys.exit(1)

    data = r.json()
    answer = data['choices'][0]['message']['content']

    # === Блок: Робот индексный_v1 (divergence SBER/GAZP vs MOEXFN) ===
    try:
        _idx = get_index_divergence()
        if _idx:
            _lines = ["\n---\n\n## 📈 Робот индексный_v1 — divergence SBER/GAZP vs MOEXFN (D1)\n",
                      "| Тикер | ret_stock | ret_sector | divergence | z | signal | date |",
                      "|---|---|---|---|---|---|---|"]
            for _t, _d in _idx.items():
                _lines.append(f"| {_t} | {_d.get('ret_stock')} | {_d.get('ret_sector')} | {_d.get('divergence')} | {_d.get('z')} | {_d.get('signal')} | {_d.get('date')} |")
            _lines.append("\n**Промпт для AI:** На основе divergence SBER/GAZP vs MOEXFN — есть ли сигнал (LONG/SHORT при divergence)? Предложи гипотезы (не внедрять без walk-forward).")
            answer = answer + "\n".join(_lines)
    except Exception as _e:
        answer = answer + f"\n[divergence block error: {_e}]\n"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d')
    out_path = OUT_DIR / f'{ts}.md'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(answer)
    print(f'✅ Сохранено: {out_path}')

    if not args.no_email and email_from and email_pass:
        subject = f'FinLab Daily Report {ts}'
        try:
            send_email(subject, answer, email_from, email_pass, email_to)
            print(f'✅ Email отправлен на {email_to}')
        except Exception as e:
            print(f'❌ Email ошибка: {e}')
            print('📤 Пробую VK-fallback...')
            if send_vk(subject, answer):
                print('✅ VK-fallback отправлен')

    print()
    print('=' * 60)
    print(answer)


if __name__ == '__main__':
    main()
