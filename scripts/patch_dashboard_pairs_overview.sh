#!/bin/bash
FILE=finlab_dashboard/app_v2.py
cp "$FILE" "$FILE.bak_pairs_overview_$(date +%Y%m%d_%H%M%S)"
echo "Бэкап создан"

/root/finlab/venv/bin/python << 'PYEOF'
from pathlib import Path

p = Path('/root/finlab/finlab_dashboard/app_v2.py')
text = p.read_text()

# Найти маркер, после которого добавляем блок pairs
# Ищем блок парного робота (закомментированный) или начало _robots_stats
marker = "_robots_stats = {}"
if marker not in text:
    print('  ❌ Не найден _robots_stats = {}')
else:
    # Показать, что вокруг
    idx = text.find(marker)
    print('  Найден _robots_stats = {} на позиции', idx)
    print('  Контекст после маркера:')
    print(repr(text[idx:idx+800]))
PYEOF
