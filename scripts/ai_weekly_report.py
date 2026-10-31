#!/usr/bin/env python3
"""ai_weekly_report.py — недельный отчёт через VseGPT + email.

Читает daily-отчёты за неделю, pairs_robot.db за неделю, ai_context.md.
Отправляет в DeepSeek, сохраняет в logs/ai_weekly/, шлёт email.
"""
import argparse
from ai_data_context import get_index_divergence, get_index_algopack
import json
import os
import smtplib
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.header import Header
from pathlib import Path
# Импорт AI-контекста (v4 + discovery)
from ai_data_context import (
    get_robot_state_v4,
    get_trades_history_v4,
    get_signals_summary_v4,
    get_discovery_summary,
)


import requests
from dotenv import load_dotenv

ROOT = Path('/root/finlab')
load_dotenv(ROOT / '.env')

VSEGPT_URL = 'https://api.vsegpt.ru/v1/chat/completions'
DEFAULT_MODEL = 'deepseek/deepseek-chat'
DB_FILE = ROOT / 'robots' / 'pairs_robot.db'
CONTEXT_FILE = ROOT / 'scripts' / 'ai_context.md'
DAILY_DIR = ROOT / 'logs' / 'ai_daily'
OUT_DIR = ROOT / 'logs' / 'ai_weekly'


def read_daily_reports(days=7):
    if not DAILY_DIR.exists():
        return ''
    cutoff = datetime.now() - timedelta(days=days)
    out = []
    for f in sorted(DAILY_DIR.glob('*.md')):
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime >= cutoff:
                out.append(f'=== {f.name} ===\n' + f.read_text(encoding='utf-8'))
        except Exception:
            pass
    return '\n\n'.join(out)


def read_db_stats(days=7):
    if not DB_FILE.exists():
        return {}
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        cur.execute("SELECT COUNT(*) FROM positions WHERE entry_time >= ?", (cutoff,))
        n_opened = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM positions WHERE status='CLOSED' AND exit_time >= ?", (cutoff,))
        n_closed = cur.fetchone()[0]
        cur.execute("SELECT COALESCE(SUM(pnl), 0) FROM positions WHERE status='CLOSED' AND exit_time >= ?", (cutoff,))
        pnl = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM positions WHERE status='CLOSED' AND exit_time >= ? AND pnl > 0", (cutoff,))
        n_win = cur.fetchone()[0]
        wr = (n_win / n_closed * 100) if n_closed else 0
        cur.execute("SELECT pair_name, COUNT(*), ROUND(SUM(pnl), 2) FROM positions WHERE status='CLOSED' AND exit_time >= ? GROUP BY pair_name ORDER BY SUM(pnl) DESC", (cutoff,))
        by_pair = cur.fetchall()
        conn.close()
        return {'opened': n_opened, 'closed': n_closed, 'pnl': pnl, 'wr': wr, 'by_pair': by_pair}
    except Exception as e:
        return {'error': str(e)}


def read_context():
    if CONTEXT_FILE.exists():
        return CONTEXT_FILE.read_text(encoding='utf-8')
    return ''


def call_vsegpt(model, system_prompt, user_content, api_key):
    return requests.post(
        VSEGPT_URL,
        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
        json={
            'model': model,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_content},
            ],
            'max_tokens': 2500,
            'temperature': 0.2,
        },
        timeout=120,
    )


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
        with smtplib.SMTP_SSL('smtp.yandex.ru', 465, timeout=30) as s:
            s.login(email_from, email_pass)
            s.send_message(msg)
    finally:
        socket.getaddrinfo = _orig


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', default=DEFAULT_MODEL)
    ap.add_argument('--days', type=int, default=7)
    ap.add_argument('--no-email', action='store_true')
    args = ap.parse_args()

    api_key = os.getenv('VSEGPT_API_KEY', '')
    email_from = os.getenv('YANDEX_EMAIL', '')
    email_pass = os.getenv('YANDEX_APP_PASSWORD', '')
    email_to = os.getenv('REPORT_EMAIL_TO', email_from)

    if not api_key:
        print('ERROR: VSEGPT_API_KEY не задан')
        sys.exit(1)

    daily = read_daily_reports(args.days)
    db_stats = read_db_stats(args.days)
    context = read_context()
    discovery = get_discovery_summary()

    # Собираем реальный контекст данных
    try:
        _dc = subprocess.check_output(
            ['/root/finlab/venv/bin/python', '/root/finlab/scripts/ai_data_context.py'],
            text=True, timeout=60,
        )
    except Exception as e:
        _dc = f'{{"error": "{e}"}}'

    user_content = f"""=== ДАННЫЕ (РЕАЛЬНЫЕ, ИСТОЧНИК ИСТИНЫ) ===
{_dc}

=== DB stats (за {args.days} дней) ===
{json.dumps(db_stats, ensure_ascii=False, indent=2, default=str)}

=== Контекст проекта ===
{context}

=== DISCOVERY (новые активы) ===
{discovery}

=== Daily-отчёты (ИСТОРИЧЕСКИЕ, за {args.days} дней) ===
{daily}
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
                _lines.append(f"FutOI ({_f.get('hour')}, H1 last {_f.get('h1_last_begin')}): price={_f.get('price')} delta_1h={_f.get('delta_1h')} fiz_buy={_f.get('fiz_buy_ratio')} yur_buy={_f.get('yur_buy_ratio')}")
                _lines.append(f"HI2 ({_h.get('tradedate')} {_h.get('tradetime')}): buy={_h.get('hhi_buy')} sell={_h.get('hhi_sell')} netflow_buy={_h.get('hhi_netflow_buy')} netflow_sell={_h.get('hhi_netflow_sell')} price_at_time={_h.get('price_at_time')} price_now={_h.get('price_now')} delta_1d={_h.get('delta_1d')}")
                _mega_items = _m.get("items") or []
                if _mega_items:
                    _lines.append(f"MegaAlerts ({_m.get('count')}): " + "; ".join([f"{it.get('tradedate')} {it.get('tradetime')} price={it.get('price')} val={it.get('value')} type={it.get('type')}" for it in _mega_items]))
                else:
                    _lines.append(f"MegaAlerts: 0")
                _lines.append(f"TradeStats ({_ts.get('tradedate')} {_ts.get('tradetime')}): price={_ts.get('price')} price_prev={_ts.get('price_prev')} delta_1d={_ts.get('delta_1d')} disb={_ts.get('disb')} vol={_ts.get('vol')}")
                _lines.append(f"RVI ({_r.get('begin')}): rvi={_r.get('rvi')} price_at_rvi_date_date={_r.get('price_at_rvi_date_date')} price_now={_r.get('price_now')}")
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
    system_prompt = """Ты — аналитик FinLab. Составь НЕДЕЛЬНЫЙ отчёт.

ВАЖНО: в user_content есть раздел "ДАННЫЕ (РЕАЛЬНЫЕ)" — это источник истины.
Он содержит:
- freshness (свежесть данных);
- config (enabled-пары, правила);
- quarantine (карантин);
- trades_history (сделки с z_entry, z_exit, PnL);
- signals_summary (сигналы: EXECUTED / MISSED / BLOCKED с причинами);
- rules (правила торговли);
- cron (расписание).

ПРАВИЛА:
1. Если данные и логи противоречат — ВЕРЬ ДАННЫМ.
2. Если данных нет — НЕ ДОДУМЫВАЙ.
3. Анализируй свободно — не ограничивайся шаблоном.

ЗАДАЧА:
1. Какие условия данных благоприятствуют лучшим сделкам? (z, corr, beta, время, TF)
2. Что мешало зайти в сделки, которые не состоялись? (причины MISSED / BLOCKED)
3. Что нужно изменить, улучшить? — на твоё усмотрение.

ФОРМАТ (гибкий, можешь добавлять свои разделы):
# Weekly Report YYYY-WW

## PnL и сделки
## Лучшие и худшие сделки (с паттернами)
## Упущенные сигналы (причины, статистика)
## Паттерны (что общего у прибыльных / убыточных)
## Рекомендации (что изменить — на твоё усмотрение)

Отвечай по делу, на русском. Будь конкретным."""

    print(f'📤 Отправка в VseGPT ({args.model})...')
    r = call_vsegpt(args.model, system_prompt, user_content, api_key)
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


    # === Algopack-фон SBER/GAZP (в answer) ===
    try:
        _apk = get_index_algopack()
        if _apk:
            _lines = ["\n\n=== ALGOPACK-ФОН SBER/GAZP (price + time + delta) ===",
                      "Связи: цена vs FutOI/HI2/MegaAlerts/TradeStats/RVI. Гипотезы — для walk-forward (не внедрять без WF)."]
            for _t, _d in _apk.items():
                _lines.append(f"\n--- {_t} ---")
                _f = _d.get("futoi") or {}
                _h = _d.get("hi2") or {}
                _m = _d.get("mega") or {}
                _ts = _d.get("tradestats") or {}
                _r = _d.get("rvi") or {}
                _lines.append(f"FutOI ({_f.get('hour')}, H1 last {_f.get('h1_last_begin')}): price={_f.get('price')} delta_1h={_f.get('delta_1h')} fiz_buy={_f.get('fiz_buy_ratio')} yur_buy={_f.get('yur_buy_ratio')}")
                _lines.append(f"HI2 ({_h.get('tradedate')} {_h.get('tradetime')}): buy={_h.get('hhi_buy')} sell={_h.get('hhi_sell')} netflow_buy={_h.get('hhi_netflow_buy')} netflow_sell={_h.get('hhi_netflow_sell')} price_at_time={_h.get('price_at_time')} price_now={_h.get('price_now')} delta_1d={_h.get('delta_1d')}")
                _mega_items = _m.get("items") or []
                if _mega_items:
                    _lines.append(f"MegaAlerts ({_m.get('count')}): " + "; ".join([f"{it.get('tradedate')} {it.get('tradetime')} price={it.get('price')} val={it.get('value')} type={it.get('type')}" for it in _mega_items]))
                else:
                    _lines.append(f"MegaAlerts: 0")
                _lines.append(f"TradeStats ({_ts.get('tradedate')} {_ts.get('tradetime')}): price={_ts.get('price')} price_prev={_ts.get('price_prev')} delta_1d={_ts.get('delta_1d')} disb={_ts.get('disb')} vol={_ts.get('vol')}")
                _lines.append(f"RVI ({_r.get('begin')}): rvi={_r.get('rvi')} price_at_rvi_date_date={_r.get('price_at_rvi_date_date')} price_now={_r.get('price_now')}")
            answer = answer + "\n".join(_lines)
    except Exception as _e:
        answer = answer + f"\n[algopack block error: {_e}]\n"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    iso = datetime.now().isocalendar()
    ts = f'{iso[0]}-W{iso[1]:02d}'
    out_path = OUT_DIR / f'{ts}.md'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(answer)
    print(f'✅ Сохранено: {out_path}')

    if not args.no_email and email_from and email_pass:
        subject = f'FinLab Weekly Report {ts}'
        try:
            send_email(subject, answer, email_from, email_pass, email_to)
            print(f'✅ Email отправлен на {email_to}')
        except Exception as e:
            print(f'❌ Email ошибка: {e}')

    print()
    print('=' * 60)
    print(answer)


if __name__ == '__main__':
    main()
