#!/usr/bin/env python3
"""ai_weekly_report.py — недельный отчёт через VseGPT + email.

Читает daily-отчёты за неделю, pairs_robot.db за неделю, ai_context.md.
Отправляет в DeepSeek, сохраняет в logs/ai_weekly/, шлёт email.
"""
import argparse
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
