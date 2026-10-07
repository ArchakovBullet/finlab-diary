#!/bin/bash
FILE=finlab_dashboard/app_v2.py
cp "$FILE" "$FILE.bak_pairs_unrealized_$(date +%Y%m%d_%H%M%S)"

/root/finlab/venv/bin/python << 'PYEOF'
from pathlib import Path

p = Path('/root/finlab/finlab_dashboard/app_v2.py')
text = p.read_text()

old = """        for _rname, _rstat in _robots_stats.items():
            _conn = _sqlite3.connect(_rstat['db'])
            try:
                _open_df = pd.read_sql_query('SELECT ticker, direction, entry_price FROM algopack_positions WHERE status="OPEN"', _conn)
            except Exception:
                _open_df = pd.DataFrame()
            _conn.close()"""

new = """        for _rname, _rstat in _robots_stats.items():
            _conn = _sqlite3.connect(_rstat['db'])
            if _rstat.get('is_pairs'):
                # Для пар — unrealized пока 0 (двухногая логика — отдельно)
                _open_df = pd.DataFrame()
            else:
                try:
                    _open_df = pd.read_sql_query('SELECT ticker, direction, entry_price FROM algopack_positions WHERE status="OPEN"', _conn)
                except Exception:
                    _open_df = pd.DataFrame()
            _conn.close()"""

if old in text:
    text = text.replace(old, new)
    print('  OK: unrealized для пар — обработка добавлена')
else:
    print('  НЕ НАЙДЕНО: паттерн unrealized не совпал')
    import re
    m = re.search(r'for _rname, _rstat in _robots_stats\.items\(\):[\s\S]{0,500}', text)
    if m:
        print('  Текущий код:')
        print(m.group(0)[:600])

p.write_text(text)
PYEOF

echo ""
echo "=== Синтаксис ==="
/root/finlab/venv/bin/python -m py_compile "$FILE" && echo "OK"
