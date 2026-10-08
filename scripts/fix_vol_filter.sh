#!/bin/bash
cd /root/finlab
FILE=robots/pairs_robot.py
cp "$FILE" "$FILE.bak_vol_fix_$(date +%Y%m%d_%H%M%S)"

/root/finlab/venv/bin/python << 'PYEOF'
from pathlib import Path

p = Path('/root/finlab/robots/pairs_robot.py')
text = p.read_text()

old = """                # Фильтр волатильности: std не должна быть аномально высокой
                _std = result.get('std', 0)
                _mean = result.get('mean', 0)
                _vol_ok = True
                if _std and _mean and abs(_mean) > 0.0001:
                    _vol_ratio = _std / abs(_mean)
                    if _vol_ratio > 0.02:  # Волатильность > 2% от среднего — аномально
                        _vol_ok = False"""

new = """                # Фильтр волатильности: только для простого spread
                # (для cointegration residuals — не применять)
                _std = result.get('std', 0)
                _mean = result.get('mean', 0)
                _vol_ok = True
                if not use_coint and _std and _mean and abs(_mean) > 0.0001:
                    _vol_ratio = _std / abs(_mean)
                    if _vol_ratio > 0.02:
                        _vol_ok = False"""

if old in text:
    text = text.replace(old, new)
    p.write_text(text)
    print('OK: _vol_ok — только для use_coint=False')
else:
    print('НЕ НАЙДЕНО: паттерн _vol_ok')
    import re
    m = re.search(r'# Фильтр волатильности[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*', text)
    if m:
        print('Контекст:')
        print(m.group(0)[:500])

PYEOF

echo ""
echo "=== Синтаксис ==="
/root/finlab/venv/bin/python -m py_compile "$FILE" && echo "OK"
