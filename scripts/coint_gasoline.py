#!/usr/bin/env python3
"""coint_gasoline.py — cointegration test для бензина."""
import pandas as pd
import numpy as np
from pathlib import Path
from statsmodels.tsa.stattools import coint

CANDLES = Path('/root/finlab/data/candles')

PAIRS = [
    ('92', '95'),       # бензин vs бензин
    ('92', 'BR'),       # бензин vs нефть
    ('95', 'BR'),
    ('92', 'GAZPF'),    # бензин vs газпром
    ('95', 'GAZPF'),
    ('92', 'CE'),       # бензин vs нефть (CE)
    ('95', 'CE'),
    ('92', 'PD'),
    ('95', 'PD'),
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
    print(f'{"pair":<20} {"M10_n":>6} {"H1_n":>6} {"D1_n":>5} {"corr_M10":>9} {"coint_M10":>10} {"verdict":>8}')
    print('-' * 80)
    for a, b in PAIRS:
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
        corr_m10 = log_a.corr(log_b)
        try:
            coint_m10 = coint(log_a, log_b)[1]
        except Exception:
            coint_m10 = 1.0

        # H1
        sa_h1 = load_close(a, 'H1'); sb_h1 = load_close(b, 'H1')
        h1_n = 0
        if sa_h1 is not None and sb_h1 is not None:
            m_h1 = pd.merge(sa_h1, sb_h1, left_index=True, right_index=True, suffixes=('_a', '_b')).dropna()
            h1_n = len(m_h1)

        # D1
        sa_d1 = load_close(a, 'D1'); sb_d1 = load_close(b, 'D1')
        d1_n = 0
        if sa_d1 is not None and sb_d1 is not None:
            m_d1 = pd.merge(sa_d1, sb_d1, left_index=True, right_index=True, suffixes=('_a', '_b')).dropna()
            d1_n = len(m_d1)

        verdict = '✅' if coint_m10 < 0.05 else '❌'
        print(f'{a}-{b:<14} {len(m):>6} {h1_n:>6} {d1_n:>5} {corr_m10:>9.3f} {coint_m10:>10.3f} {verdict:>8}')
