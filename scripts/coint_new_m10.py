#!/usr/bin/env python3
"""coint_new_m10.py — cointegration test для новых пар на M10."""
import pandas as pd
import numpy as np
from pathlib import Path
from statsmodels.tsa.stattools import coint

CANDLES = Path('/root/finlab/data/candles')

NEW_PAIRS = [
    ('BR', 'GAZPF'), ('BR', 'CE'), ('BR', 'PD'),
    ('GD', 'SV'), ('PT', 'SV'), ('GD', 'PT'),
    ('SBERF', 'IMOEXF'), ('LK', 'IMOEXF'),
    ('GAZPF', 'SBERF'),
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
    print(f'{"pair":<20} {"M10_n":>6} {"H1_n":>6} {"corr":>8} {"coint_p":>9} {"verdict":>8}')
    print('-' * 75)
    for a, b in NEW_PAIRS:
        # M10
        sa = load_close(a, 'M10'); sb = load_close(b, 'M10')
        if sa is None or sb is None:
            print(f'{a}-{b}: нет M10')
            continue
        m = pd.merge(sa, sb, left_index=True, right_index=True, suffixes=('_a', '_b')).dropna()
        if len(m) < 100:
            print(f'{a}-{b}: мало M10 ({len(m)})')
            continue
        log_a = np.log(m['close_a']); log_b = np.log(m['close_b'])
        corr = log_a.corr(log_b)
        try:
            coint_p = coint(log_a, log_b)[1]
        except Exception:
            coint_p = 1.0
        # H1
        sa_h1 = load_close(a, 'H1'); sb_h1 = load_close(b, 'H1')
        h1_n = 0
        if sa_h1 is not None and sb_h1 is not None:
            m_h1 = pd.merge(sa_h1, sb_h1, left_index=True, right_index=True, suffixes=('_a', '_b')).dropna()
            h1_n = len(m_h1)
        verdict = '✅' if coint_p < 0.05 else '❌'
        print(f'{a}-{b:<14} {len(m):>6} {h1_n:>6} {corr:>8.3f} {coint_p:>9.3f} {verdict:>8}')
