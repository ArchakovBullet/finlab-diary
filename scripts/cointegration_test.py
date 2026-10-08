#!/usr/bin/env python3
"""cointegration_test.py — Engle-Granger test для пар."""
import pandas as pd
import numpy as np
from pathlib import Path

try:
    from statsmodels.tsa.stattools import adfuller, coint
except ImportError:
    print('Установите statsmodels: pip install statsmodels')
    raise SystemExit(1)

CANDLES = Path('/root/finlab/data/candles')

# Все 30 пар (10 текущих + 20 кандидатов)
PAIRS = [
    ('WUSH', 'WU', 'M10'), ('SFIN', 'SH', 'M10'), ('POSI', 'PS', 'M10'),
    ('BANE', 'BN', 'M10'), ('BELU', 'NB', 'M10'),
    ('SFIN', 'SH', 'H1'), ('SOFL', 'S0', 'H1'), ('RASP', 'RA', 'H1'),
    ('LK', 'HY', 'H1'), ('HY', 'IR', 'H1'),
    ('IMOEXF', 'MX', 'H4'), ('SBERF', 'IMOEXF', 'H4'),
    ('GAZPF', 'IMOEXF', 'H4'), ('GAZPF', 'SBERF', 'H4'),
    ('PT', 'SV', 'H4'), ('GD', 'SV', 'H4'), ('GD', 'PT', 'H4'),
    ('GLDRUBF', 'GD', 'H4'), ('SO', 'LK', 'H4'), ('PD', 'PT', 'H4'),
    ('PD', 'SV', 'H4'), ('LK', 'IMOEXF', 'H4'), ('SN', 'MX', 'H4'),
    ('IR', 'MX', 'H4'), ('CE', 'PT', 'H4'), ('CE', 'SV', 'H4'),
    ('SN', 'IMOEXF', 'H4'),
    ('CNYRUBF', 'USDRUBF', 'H4'), ('EURRUBF', 'USDRUBF', 'H4'),
    ('CNYRUBF', 'EURRUBF', 'H4'),
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
    print(f'{"pair":<20} {"tf":<5} {"n":>6} {"corr":>8} {"adf_p":>8} {"coint_p":>9} {"verdict":>8}')
    print('-' * 70)
    for a, b, tf in PAIRS:
        sa = load_close(a, tf); sb = load_close(b, tf)
        if sa is None or sb is None: continue
        m = pd.merge(sa, sb, left_index=True, right_index=True, suffixes=('_a', '_b')).dropna()
        if len(m) < 100: continue
        log_a = np.log(m['close_a']); log_b = np.log(m['close_b'])
        corr = log_a.corr(log_b)
        spread = log_a - log_b

        # ADF на спред
        try:
            adf_result = adfuller(spread, maxlag=1)
            adf_p = adf_result[1]
        except Exception:
            adf_p = 1.0

        # Engle-Granger cointegration
        try:
            coint_result = coint(log_a, log_b)
            coint_p = coint_result[1]
        except Exception:
            coint_p = 1.0

        verdict = '✅' if coint_p < 0.05 and adf_p < 0.05 else '❌'
        print(f'{a}-{b:<14} {tf:<5} {len(m):>6} {corr:>8.3f} {adf_p:>8.3f} {coint_p:>9.3f} {verdict:>8}')
