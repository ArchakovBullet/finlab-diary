#!/usr/bin/env python3
"""ai_daily_report.py — ежедневный отчёт через VseGPT + email.

Читает robot.log за 24ч, robot_state.json, pairs_robot.db.
Отправляет в DeepSeek, сохраняет в logs/ai_daily/, шлёт email.
"""
import argparse
import json
import os
import smtplib
import sqlite3
import sys
from datetime import datetime, timedelta
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


def send_email(subject, body, email_from, email_pass, email_to):
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = Header(subject, 'utf-8')
    msg['From'] = email_from
    msg['To'] = email_to
    with smtplib.SMTP_SSL('smtp.yandex.ru', 465, timeout=30) as s:
        s.login(email_from, email_pass)
        s.send_message(msg)


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

    user_content = f"""=== Контекст ===
{context}

=== robot_state.json ===
{json.dumps(state, ensure_ascii=False, indent=2)}

=== DB stats (за {args.hours}ч) ===
{json.dumps(db_stats, ensure_ascii=False, indent=2)}

=== robot.log (последние 2000 строк) ===
{log_text}
"""

    system_prompt = """Ты — аналитик FinLab. Составь ЕЖЕДНЕВНЫЙ отчёт.

Формат:
# Daily Report YYYY-MM-DD

## PnL и сделки
- Открыто, закрыто, PnL, WR.

## ML-фильтр
- PASS/BLOCK по парам.

## Аномалии
- Что не так.

## Рекомендации
- 1-3 конкретных.

Отвечай кратко, по делу, на русском."""

    print(f'📤 Отправка в VseGPT ({args.model})...')
    r = call_vsegpt(args.model, system_prompt, user_content, api_key)
    if r.status_code != 200:
        print(f'ERROR: HTTP {r.status_code}')
        print(r.text[:500])
        sys.exit(1)

    data = r.json()
    answer = data['choices'][0]['message']['content']

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

    print()
    print('=' * 60)
    print(answer)


if __name__ == '__main__':
    main()
