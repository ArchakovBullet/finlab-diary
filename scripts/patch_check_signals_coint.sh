#!/bin/bash
cd /root/finlab
FILE=robots/pairs_robot.py
cp "$FILE" "$FILE.bak_check_signals_coint_$(date +%Y%m%d_%H%M%S)"

/root/finlab/venv/bin/python << 'PYEOF'
from pathlib import Path

p = Path('/root/finlab/robots/pairs_robot.py')
text = p.read_text()

# Патч: передать use_coint и resid_window
old = """            window = pair_data.get('best_params', {}).get('window', 20)
            entry_z = pair_data.get('best_params', {}).get('entry_z', ENTRY_Z_DEFAULT)
            exit_z = pair_data.get('best_params', {}).get('exit_z', EXIT_Z_DEFAULT)

            # Z-score
            result = calculate_zscore(df_a, df_b, window=window)"""

new = """            _bp = pair_data.get('best_params', {})
            window = _bp.get('window', 20)
            entry_z = _bp.get('entry_z', ENTRY_Z_DEFAULT)
            exit_z = _bp.get('exit_z', EXIT_Z_DEFAULT)
            use_coint = _bp.get('use_coint', False)
            resid_window = _bp.get('resid_window', 60)

            # Z-score (с поддержкой cointegration residuals)
            result = calculate_zscore(df_a, df_b, window=window,
                                      use_coint=use_coint,
                                      resid_window=resid_window)"""

if old in text:
    text = text.replace(old, new)
    p.write_text(text)
    print('OK: check_signals_by_tf — use_coint передан')
else:
    print('НЕ НАЙДЕНО: паттерн check_signals_by_tf')
    # Показать контекст
    import re
    m = re.search(r'window = pair_data\.get[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*calculate_zscore[^\n]*', text)
    if m:
        print('Контекст:')
        print(m.group(0))
PYEOF

echo ""
echo "=== Синтаксис ==="
/root/finlab/venv/bin/python -m py_compile "$FILE" && echo "OK"
