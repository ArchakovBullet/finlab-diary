#!/bin/bash
cd /root/finlab
FILE=robots/pairs_robot.py
cp "$FILE" "$FILE.bak_np_fix_$(date +%Y%m%d_%H%M%S)"

/root/finlab/venv/bin/python << 'PYEOF'
from pathlib import Path

p = Path('/root/finlab/robots/pairs_robot.py')
text = p.read_text()

old = """def calculate_zscore(df_a, df_b, window=20, use_coint=False, resid_window=60):
    \"\"\"Z-score спреда.

    Если use_coint=True — rolling OLS residuals:
        log_a = beta * log_b + alpha + resid
        z-score по resid.
    Иначе — простой spread = log_a - log_b.
    \"\"\"
    _ca = 'begin' if 'begin' in df_a.columns else 'tradedate'"""

new = """def calculate_zscore(df_a, df_b, window=20, use_coint=False, resid_window=60):
    \"\"\"Z-score спреда.

    Если use_coint=True — rolling OLS residuals:
        log_a = beta * log_b + alpha + resid
        z-score по resid.
    Иначе — простой spread = log_a - log_b.
    \"\"\"
    import numpy as np
    _ca = 'begin' if 'begin' in df_a.columns else 'tradedate'"""

if old in text:
    text = text.replace(old, new)
    p.write_text(text)
    print('OK: np импорт добавлен')
else:
    print('НЕ НАЙДЕНО: паттерн calculate_zscore')
    # показать начало функции
    import re
    m = re.search(r'def calculate_zscore[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*', text)
    if m:
        print(m.group(0))
PYEOF

echo ""
echo "=== Синтаксис ==="
/root/finlab/venv/bin/python -m py_compile "$FILE" && echo "OK"
