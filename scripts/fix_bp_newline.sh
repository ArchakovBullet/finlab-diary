#!/bin/bash
cd /root/finlab
FILE=robots/pairs_robot.py
cp "$FILE" "$FILE.bak_bp_fix_$(date +%Y%m%d_%H%M%S)"

/root/finlab/venv/bin/python << 'PYEOF'
from pathlib import Path

p = Path('/root/finlab/robots/pairs_robot.py')
text = p.read_text()

# Фикс: # Параметры            _bp = ...
old = "            # Параметры            _bp = pair_data.get('best_params', {})"
new = "            # Параметры\n            _bp = pair_data.get('best_params', {})"

if old in text:
    text = text.replace(old, new)
    p.write_text(text)
    print('OK: _bp — фикс склейки')
else:
    print('НЕ НАЙДЕНО: паттерн _bp')
    # Показать строку 951
    lines = text.split('\n')
    if len(lines) > 950:
        print('Строка 951:', repr(lines[950]))
PYEOF

echo ""
echo "=== Синтаксис ==="
/root/finlab/venv/bin/python -m py_compile "$FILE" && echo "OK"
