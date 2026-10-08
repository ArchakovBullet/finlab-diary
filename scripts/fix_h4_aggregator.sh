#!/bin/bash
cd /root/finlab
FILE=FinLabPy/DataCollectors/futures_h4_aggregator.py
cp "$FILE" "$FILE.bak_h4_fix_$(date +%Y%m%d_%H%M%S)"

/root/finlab/venv/bin/python << 'PYEOF'
from pathlib import Path

p = Path('/root/finlab/FinLabPy/DataCollectors/futures_h4_aggregator.py')
text = p.read_text()

# Фикс: убрать lookback_dates (обрабатывать всю историю)
old = """    lookback_dates = [(date.today() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(3)]
    total_new = 0"""
new = """    total_new = 0"""
if old in text:
    text = text.replace(old, new)
    print('  OK: lookback_dates убрано')
else:
    print('  ПРОПУСК: lookback_dates не найдено')

# Фикс: убрать фильтр по lookback_dates
old2 = """        # Фильтруем последние 3 дня
        df_recent = df.filter(pl.col('tradedate').is_in(lookback_dates))
        if df_recent.is_empty():
            continue"""
new2 = """        df_recent = df"""
if old2 in text:
    text = text.replace(old2, new2)
    print('  OK: фильтр по lookback_dates убран')
else:
    print('  ПРОПУСК: фильтр не найден')

# Фикс: merge с существующим H4 (append)
# Найти запись parquet
old3 = """        # Запись
        """
# Покажем, что там — после блока h4_rows
import re
m = re.search(r'h4_rows\.append\(\{[^}]+\}\)', text, re.DOTALL)
if m:
    print(f'  Найден h4_rows.append')

# Показать конец функции
idx = text.find('def aggregate_all')
end = text.find('\ndef ', idx+1)
if end == -1:
    end = len(text)
print('  Конец aggregate_all:')
print(text[end-500:end])

p.write_text(text)
PYEOF

echo ""
/root/finlab/venv/bin/python -m py_compile "$FILE" && echo "Синтаксис OK"
