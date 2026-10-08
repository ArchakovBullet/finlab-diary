#!/usr/bin/env python3
"""coint_new_ideas.py — cointegration test для новых пар."""
import pandas as pd
import numpy as np
from pathlib import Path
from statsmodels.tsa.stattools import coint

CANDLES = Path('/root/finlab/data/candles')

NEW_PAIRS = [
    # Нефтяные
    ('BR', 'GAZPF', 'H4'),
    ('BR', 'CE', 'H4'),
    ('BR', 'PD', 'H4'),
    # Металлы
    ('GD', 'SV', 'H4'),
    ('PT', 'SV', 'H4'),
    ('GD', 'PT', 'H4'),
    ('GLDRUBF', 'GD', 'H4'),
    # Кросс-рыночные
    ('SBERF', 'IMOEXF', 'H4'),
    ('LK', 'IMOEXF', 'H4'),
    ('GAZPF', 'SBERF', 'H4'),
    # Бензин (если есть)
    ('AI92', 'BR', 'H4'),
    ('AI95', 'BR', 'H4'),
]


def load_close(ticker, tf):
    f = CANDLES / f'{ticker}_{tf}.parquet'
    if not f.exists(): return None
    df = pd.read_parquet(f)
    col = 'begin' if 'begin' in df.columns else 'tradedate'
    df['dt'] = pd.to_datetime(df[col])
    df['close'] = df['close'].apply(lambda x: float(x) if not isinstance(x, bytes) else 0.0)
    return df.set_index('dt')['close'].sort_index()


if __name__ == '__main__':
    print(f'{"pair":<20} {"tf":<5} {"n":>6} {"corr":>8} {"coint_p":>9} {"verdict":>8}')
    print('-' * 70)
    for a, b, tf in NEW_PAIRS:
        sa = load_close(a, tf); sb = load_close(b, tf)
        if sa is None or sb is None:
            print(f'{a}-{b}_{tf}: нет данных')
            continue
        m = pd.merge(sa, sb, left_index=True, right_index=True, suffixes=('_a', '_b')).dropna()
        if len(m) < 100:
            print(f'{a}-{b}_{tf}: мало ({len(m)})')
            continue
        log_a = np.log(m['close_a']); log_b = np.log(m['close_b'])
        corr = log_a.corr(log_b)
        try:
            coint_p = coint(log_a, log_b)[1]
        except Exception:
            coint_p = 1.0
        verdict = '✅' if coint_p < 0.05 else '❌'
        print(f'{a}-{b:<14} {tf:<5} {len(m):>6} {corr:>8.3f} {coint_p:>9.3f} {verdict:>8}')
