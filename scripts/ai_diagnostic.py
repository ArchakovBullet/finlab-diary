#!/usr/bin/env python3
"""ai_diagnostic.py — ИИ-диагностика логов робота через VseGPT (DeepSeek).

Читает robot.log, отправляет в DeepSeek, сохраняет разбор.
Не трогает прод — только чтение + запись в logs/.

Использование:
  python scripts/ai_diagnostic.py
  python scripts/ai_diagnostic.py --lines 1000 --log robots/robot.log
  python scripts/ai_diagnostic.py --model deepseek/deepseek-r1
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path('/root/finlab')
load_dotenv(ROOT / '.env')

VSEGPT_URL = 'https://api.vsegpt.ru/v1/chat/completions'
DEFAULT_MODEL = 'deepseek/deepseek-chat'
DEFAULT_LOG = ROOT / 'robots' / 'robot.log'
STATE_FILE = ROOT / 'robots' / 'robot_state.json'
OUT_DIR = ROOT / 'logs'
CONTEXT_FILE = ROOT / 'scripts' / 'ai_context.md'

# Читаем контекст (если есть)
_context = ''
if CONTEXT_FILE.exists():
    _context = CONTEXT_FILE.read_text(encoding='utf-8')

SYSTEM_PROMPT = """Ты — диагност торгового робота FinLab (парная торговля).
Тебе дают лог робота и его состояние. Твоя задача:
1. Найти ошибки, исключения, аномалии.
2. Объяснить, почему робот не открыл позиции (если не открыл).
3. Отметить, что работает нормально.
4. Дать 1-3 конкретные рекомендации.

Отвечай кратко, по делу, на русском. Без воды. Формат:
## Ошибки и аномалии
## Почему нет сделок
## Что работает
## Рекомендации

ВАЖНО: ниже — контекст проекта. Учитывай его. Если что-то
указано как "ИЗВЕСТНЫЕ ФАКТЫ" — НЕ считай это аномалией.

=== КОНТЕКСТ ПРОЕКТА ===
""" + _context


def read_log(path, lines):
    if not path.exists():
        return None
    with open(path, 'r', errors='replace') as f:
        all_lines = f.readlines()
    return ''.join(all_lines[-lines:])


def read_state():
    if not STATE_FILE.exists():
        return {}
    try:
        return json.load(open(STATE_FILE))
    except Exception:
        return {}


def call_vsegpt(model, system_prompt, user_content, api_key, timeout=60):
    r = requests.post(
        VSEGPT_URL,
        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
        json={
            'model': model,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_content},
            ],
            'max_tokens': 1500,
            'temperature': 0.2,
        },
        timeout=timeout,
    )
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lines', type=int, default=500, help='Сколько строк лога читать')
    ap.add_argument('--log', type=str, default=str(DEFAULT_LOG), help='Путь к логу')
    ap.add_argument('--model', type=str, default=DEFAULT_MODEL, help='Модель VseGPT')
    ap.add_argument('--out', type=str, default=None, help='Путь для сохранения .md')
    args = ap.parse_args()

    api_key = os.getenv('VSEGPT_API_KEY', '')
    if not api_key:
        print('ERROR: VSEGPT_API_KEY не найден в .env')
        sys.exit(1)

    log_path = Path(args.log)
    log_text = read_log(log_path, args.lines)
    if log_text is None:
        print(f'ERROR: лог не найден: {log_path}')
        sys.exit(1)

    state = read_state()

    user_content = f"""=== robot_state.json ===
{json.dumps(state, ensure_ascii=False, indent=2)}

=== robot.log (последние {args.lines} строк) ===
{log_text}
"""

    print(f'📤 Отправка в VseGPT ({args.model}), строк: {args.lines}, размер промпта: {len(user_content)} символов...')
    r = call_vsegpt(args.model, SYSTEM_PROMPT, user_content, api_key)

    if r.status_code != 200:
        print(f'ERROR: HTTP {r.status_code}')
        print(r.text[:500])
        sys.exit(1)

    data = r.json()
    answer = data['choices'][0]['message']['content']
    usage = data.get('usage', {})

    out_dir = OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_path = Path(args.out) if args.out else out_dir / f'ai_diagnostic_{ts}.md'

    with open(out_path, 'w') as f:
        f.write(f'# AI-диагностика {ts}\n\n')
        f.write(f'- Модель: {args.model}\n')
        f.write(f'- Лог: {log_path}\n')
        f.write(f'- Строк: {args.lines}\n')
        f.write(f'- Токенов: prompt={usage.get("prompt_tokens", "?")}, completion={usage.get("completion_tokens", "?")}\n\n')
        f.write('---\n\n')
        f.write(answer)

    print(f'✅ Сохранено: {out_path}')
    print()
    print('=' * 60)
    print(answer)


if __name__ == '__main__':
    main()
