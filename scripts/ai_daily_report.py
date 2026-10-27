#!/usr/bin/env python3
"""ai_daily_report.py — ежедневный отчёт через VseGPT + email.
from ai_data_context import get_robot_state_v4, get_trades_history_v4, get_signals_summary_v4, get_index_divergence


Читает robot.log за 24ч, robot_state.json, pairs_robot.db.
Отправляет в DeepSeek, сохраняет в logs/ai_daily/, шлёт email.
"""
import argparse
import json
from ai_data_context import get_index_divergence
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
