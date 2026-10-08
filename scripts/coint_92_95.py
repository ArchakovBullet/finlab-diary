#!/usr/bin/env python3
"""coint_92_95.py — cointegration 92-95 на разных ТФ."""
import pandas as pd
import numpy as np
from pathlib import Path
from statsmodels.tsa.stattools import coint

CANDLES = Path('/root/finlab/data/candles')


def load_close(ticker, tf):
    f = CANDLES / f'{ticker}_{tf}.parquet'
    if not f.exists(): return None
    df = pd.read_parquet(f)
    col = 'begin' if 'begin' in df.columns else 'tradedate'
    df['dt'] = pd.to_datetime(df[col])
    df['close'] = df['close'].apply(lambda x: float(x) if not isinstance(x, bytes) else 0.0)
    return df.set_index('dt')['close'].sort_index()


if __name__ == '__main__':
    print(f'{"pair":<20} {"tf":<5} {"n":>5} {"corr":>8} {"coint_p":>9} {"verdict":>8}')
    print('-' * 60)
    for tf in ['M10', 'H1', 'H4', 'D1']:
        sa = load_close('92', tf); sb = load_close('95', tf)
        if sa is None or sb is None:
            continue
        m = pd.merge(sa, sb, left_index=True, right_index=True, suffixes=('_a', '_b')).dropna()
        if len(m) < 30:
            print(f'92-95_{tf}: мало ({len(m)})')
            continue
        log_a = np.log(m['close_a']); log_b = np.log(m['close_b'])
        corr = log_a.corr(log_b)
        try:
            coint_p = coint(log_a, log_b)[1]
        except Exception:
            coint_p = 1.0
        verdict = '✅' if coint_p < 0.05 else '❌'
        print(f'92-95_{tf:<13} {tf:<5} {len(m):>5} {corr:>8.3f} {coint_p:>9.3f} {verdict:>8}')
