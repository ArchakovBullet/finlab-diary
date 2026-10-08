#!/bin/bash
cd /root/finlab
FILE=robots/pairs_robot.py
cp "$FILE" "$FILE.bak_check_regex_$(date +%Y%m%d_%H%M%S)"

/root/finlab/venv/bin/python << 'PYEOF'
from pathlib import Path
import re

p = Path('/root/finlab/robots/pairs_robot.py')
text = p.read_text()

# Regex: от "window = pair_data.get..." до "calculate_zscore(...)"
pattern = re.compile(
    r"(\s+window = pair_data\.get\('best_params', \{\}\)\.get\('window', 20\)\n"
    r"\s+entry_z = pair_data\.get\('best_params', \{\}\)\.get\('entry_z', ENTRY_Z_DEFAULT\)\n"
    r"\s+exit_z = pair_data\.get\('best_params', \{\}\)\.get\('exit_z', EXIT_Z_DEFAULT\)\n"
    r"\s+\n"
    r"\s+# Z-score\n"
    r"\s+result = calculate_zscore\(df_a, df_b, window=window\))",
    re.MULTILINE
)

replacement = """            _bp = pair_data.get('best_params', {})
            window = _bp.get('window', 20)
            entry_z = _bp.get('entry_z', ENTRY_Z_DEFAULT)
            exit_z = _bp.get('exit_z', EXIT_Z_DEFAULT)
            use_coint = _bp.get('use_coint', False)
            resid_window = _bp.get('resid_window', 60)

            # Z-score (с поддержкой cointegration residuals)
            result = calculate_zscore(df_a, df_b, window=window,
                                      use_coint=use_coint,
                                      resid_window=resid_window)"""

if pattern.search(text):
    text = pattern.sub(replacement, text, count=1)
    p.write_text(text)
    print('OK: check_signals_by_tf заменён через regex')
else:
    print('НЕ НАЙДЕНО: паттерн через regex')
    # Показать как есть
    m = re.search(r'window = pair_data[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*calculate_zscore[^\n]*', text)
    if m:
        print('Текущий код:')
        print(repr(m.group(0)[:400]))
PYEOF

echo ""
echo "=== Синтаксис ==="
/root/finlab/venv/bin/python -m py_compile "$FILE" && echo "OK"
