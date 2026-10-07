#!/bin/bash
FILE=finlab_dashboard/app_v2.py
cp "$FILE" "$FILE.bak_pairs_overview_v2_$(date +%Y%m%d_%H%M%S)"
echo "Бэкап создан"

/root/finlab/venv/bin/python << 'PYEOF'
from pathlib import Path

p = Path('/root/finlab/finlab_dashboard/app_v2.py')
text = p.read_text()

old = """        # Парный робот — выключен, в Обзор не включаем

        # Algopack-робот (заменяет старый «Робот фьючерсов»)"""

new = """        # Парный робот
        _pairs_db = Path('/root/finlab/robots/pairs_robot.db')
        if _pairs_db.exists():
            _conn = _sqlite3.connect(_pairs_db)
            try:
                _closed_pairs = pd.read_sql_query('SELECT * FROM positions WHERE status="CLOSED"', _conn)
                _open_pairs = pd.read_sql_query('SELECT * FROM positions WHERE status="OPEN"', _conn)
            except Exception:
                _closed_pairs = pd.DataFrame()
                _open_pairs = pd.DataFrame()
            _conn.close()
            _pairs_pnl = float(_closed_pairs['pnl'].sum()) if len(_closed_pairs) > 0 else 0.0
            _pairs_wr = _calc_wr(_closed_pairs) if len(_closed_pairs) > 0 else 0
            _robots_stats['📊 Парная торговля'] = {
                'open': len(_open_pairs),
                'pnl': _pairs_pnl,
                'wr': _pairs_wr,
                'db': _pairs_db,
                'is_pairs': True,
            }

        # Algopack-робот (заменяет старый «Робот фьючерсов»)"""

if old in text:
    text = text.replace(old, new)
    print('  OK: блок pairs_robot добавлен')
else:
    print('  НЕ НАЙДЕНО: паттерн не совпал')

p.write_text(text)
PYEOF

echo ""
echo "=== Синтаксис ==="
/root/finlab/venv/bin/python -m py_compile "$FILE" && echo "OK"
