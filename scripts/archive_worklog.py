#!/usr/bin/env python3
"""archive_worklog.py — архивация старых записей WORK_LOG.

Разделяет WORK_LOG.md:
- до CUTOFF_DATE → WORK_LOG_ARCHIVE_YYYY_MM.md
- после → остаётся в WORK_LOG.md
- в начало WORK_LOG → ссылка на архив.
"""
import re
from pathlib import Path
from datetime import datetime

WORKLOG = Path('/root/finlab/WORK_LOG.md')
CUTOFF_DATE = '2026-10-01'  # дата отсечки
ARCHIVE_DIR = Path('/root/finlab/archive')
ARCHIVE_DIR.mkdir(exist_ok=True)

# Определяем имя архива по месяцу до отсечки
cutoff_dt = datetime.strptime(CUTOFF_DATE, '%Y-%m-%d')
prev_month = (cutoff_dt.replace(day=1) - __import__('datetime').timedelta(days=1))
archive_name = f'WORK_LOG_ARCHIVE_{prev_month.strftime("%Y_%m")}.md'
ARCHIVE = ARCHIVE_DIR / archive_name

text = WORKLOG.read_text(encoding='utf-8')
lines = text.splitlines(keepends=True)

# Ищем границу: первая строка, начинающаяся с "## 2026-10-01" или позже
cutoff_re = re.compile(r'^## (\d{4}-\d{2}-\d{2})')
cutoff_idx = None
for i, line in enumerate(lines):
    m = cutoff_re.match(line)
    if m:
        date_str = m.group(1)
        if date_str >= CUTOFF_DATE:
            cutoff_idx = i
            break

if cutoff_idx is None:
    print('❌ Не найдена дата отсечки. Проверь CUTOFF_DATE.')
    exit(1)

# Ищем начало блока (--- перед ##)
start_idx = cutoff_idx
for j in range(cutoff_idx - 1, max(0, cutoff_idx - 5), -1):
    if lines[j].strip() == '---':
        start_idx = j
        break

old_part = ''.join(lines[:start_idx]).rstrip()
new_part = ''.join(lines[start_idx:])

# Ссылка на архив в начало WORK_LOG
header = f"""# FinLab — WORK_LOG (живая история)

> **Архив:** [{archive_name}](archive/{archive_name}) — записи до {CUTOFF_DATE}.

---

"""

WORKLOG.write_text(header + new_part, encoding='utf-8')
ARCHIVE.write_text(old_part + '\n', encoding='utf-8')

old_size = len(old_part) / 1024
new_size = len(header + new_part) / 1024
print(f'✅ Архив: {ARCHIVE} ({old_size:.1f} КБ)')
print(f'✅ WORK_LOG: {WORKLOG} ({new_size:.1f} КБ)')
