#!/bin/bash
cd /root/finlab
FILE=robots/pairs_robot_algopack.py
cp "$FILE" "$FILE.bak_algopack_filter_$(date +%Y%m%d_%H%M%S)"

/root/finlab/venv/bin/python << 'PYEOF'
from pathlib import Path

p = Path('/root/finlab/robots/pairs_robot_algopack.py')
text = p.read_text()

# Добавить функцию get_algopack_signal после is_new_contract
old_func = """def load_tf_fresh_state():"""
new_func = """def get_algopack_signal(ticker, direction='BUY'):
    \"\"\"Algopack-подтверждение для ноги пары.
    direction: 'BUY' или 'SELL' — направление ноги.
    Возвращает: (ok, reason) — True/False + причина.
    \"\"\"
    import pandas as _pd
    try:
        f = ROOT / 'data' / 'tradestats' / f'{ticker}_tradestats.parquet'
        if not f.exists():
            return True, 'no_data'
        df = _pd.read_parquet(f)
        df['tradedate'] = _pd.to_datetime(df['tradedate'])
        # Последний день
        last_date = df['tradedate'].max()
        last = df[df['tradedate'] == last_date]
        if len(last) == 0:
            return True, 'no_last'
        disb = last['disb'].mean() if 'disb' in last.columns else 0
        im = last['im'].mean() if 'im' in last.columns else 0

        # Фильтр: disb должен подтверждать направление
        if direction == 'BUY':
            if disb > 0.3:
                return True, f'disb={disb:.2f}'
            elif disb < -0.3:
                return False, f'disb={disb:.2f} против LONG'
        else:  # SELL
            if disb < -0.3:
                return True, f'disb={disb:.2f}'
            elif disb > 0.3:
                return False, f'disb={disb:.2f} против SHORT'
        return True, 'neutral'
    except Exception as e:
        return True, f'err: {e}'


def load_tf_fresh_state():"""

if old_func in text:
    text = text.replace(old_func, new_func, 1)
    print('  OK: get_algopack_signal добавлен')
else:
    print('  НЕ НАЙДЕНО: load_tf_fresh_state')

p.write_text(text)
PYEOF

echo "=== Синтаксис ==="
/root/finlab/venv/bin/python -m py_compile "$FILE" && echo "OK"
