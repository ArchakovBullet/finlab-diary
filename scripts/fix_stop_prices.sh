#!/bin/bash
cd /root/finlab
FILE=robots/pairs_robot.py
cp "$FILE" "$FILE.bak_stop_fix_$(date +%Y%m%d_%H%M%S)"

/root/finlab/venv/bin/python << 'PYEOF'
from pathlib import Path

p = Path('/root/finlab/robots/pairs_robot.py')
text = p.read_text()

# Добавить функцию close_all_positions перед main() или после close_position
old_marker = "def main():"
new_func = '''def close_all_positions(reason='STOP'):
    """Закрыть все открытые позиции по M10 close (реальные цены)."""
    for pos in get_open_positions():
        _pid = pos[0]; _pair = pos[1]; _base = pos[2]; _tf = pos[3]
        _ta = pos[16] if len(pos) > 16 else None
        _tb = pos[18] if len(pos) > 18 else None
        _pa = 0.0; _pb = 0.0
        try:
            if _ta:
                _fa = CANDLES_DIR / f'{_ta}_{_tf}.parquet'
                if _fa.exists():
                    _pa = float(pd.read_parquet(_fa)['close'].iloc[-1])
            if _tb:
                _fb = CANDLES_DIR / f'{_tb}_{_tf}.parquet'
                if _fb.exists():
                    _pb = float(pd.read_parquet(_fb)['close'].iloc[-1])
        except Exception as e:
            print(f'  ⚠️ close_all_positions({_pair}): {e}')
        close_position(_pid, _pair, _base, _tf, 0, _pa, _pb)


def main():'''

if old_marker in text and 'def close_all_positions' not in text:
    text = text.replace(old_marker, new_func, 1)
    print('  OK: close_all_positions добавлена')
else:
    print('  ПРОПУСК: close_all_positions уже есть или main не найден')

# Заменить оба close_position(pos[0], pos[1], pos[2], pos[3], 0, 0, 0) → close_all_positions()
old_call = "close_position(pos[0], pos[1], pos[2], pos[3], 0, 0, 0)"
count = text.count(old_call)
if count > 0:
    text = text.replace(old_call, "close_all_positions()")
    print(f'  OK: заменено {count} вызовов')
else:
    print('  НЕ НАЙДЕНО: close_position(..., 0, 0, 0)')

p.write_text(text)
PYEOF

echo ""
echo "=== Синтаксис ==="
/root/finlab/venv/bin/python -m py_compile "$FILE" && echo "OK"
