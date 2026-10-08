#!/usr/bin/env python3
"""
reoptimize_fail_pairs.py — grid search для FAIL-пар.

Перебираем entry_z, exit_z, window. Считаем Sharpe.
Осторожно: p-hacking. Нужен walk-forward на out-of-sample.
"""
import pandas as pd
import numpy as np
from pathlib import Path
import itertools

CANDLES = Path('/root/finlab/data/candles')
COMMISSION = 0.0028
TIME_EXIT_BARS = 120

FAIL_PAIRS = [
    ('WUSH', 'WU', 'M10'),
    ('POSI', 'PS', 'M10'),
    ('HY', 'IR', 'H1'),
]


def load_pair(a, b, tf):
    fa = CANDLES / f'{a}_{tf}.parquet'
    fb = CANDLES / f'{b}_{tf}.parquet'
    if not fa.exists() or not fb.exists():
        return None
    da = pd.read_parquet(fa)
    db = pd.read_parquet(fb)
    _ca = 'begin' if 'begin' in da.columns else 'tradedate'
    _cb = 'begin' if 'begin' in db.columns else 'tradedate'
    a_df = da[[_ca, 'close']].rename(columns={_ca: 'dt'})
    b_df = db[[_cb, 'close']].rename(columns={_cb: 'dt'})
    m = pd.merge(a_df, b_df, on='dt', suffixes=('_a', '_b'))
    m['close_a'] = m['close_a'].apply(lambda x: float(x) if not isinstance(x, bytes) else 0.0)
    m['close_b'] = m['close_b'].apply(lambda x: float(x) if not isinstance(x, bytes) else 0.0)
    m['spread'] = np.log(m['close_a']) - np.log(m['close_b'])
    return m.sort_values('dt').reset_index(drop=True)


def simulate(m, entry_z, exit_z, window=20):
    m = m.copy()
    m['mean'] = m['spread'].rolling(window).mean()
    m['std'] = m['spread'].rolling(window).std()
    m['z'] = (m['spread'] - m['mean']) / m['std']

    pos = 0
    entry_price = 0
    entry_i = 0
    trades = []

    for i in range(window, len(m)):
        z = m['z'].iloc[i]
        if pd.isna(z):
            continue
        if pos == 0:
            if z >= entry_z:
                pos = -1; entry_price = m['spread'].iloc[i]; entry_i = i
            elif z <= -entry_z:
                pos = 1; entry_price = m['spread'].iloc[i]; entry_i = i
        else:
            time_exit = (i - entry_i) >= TIME_EXIT_BARS
            z_exit = abs(z) <= exit_z
            if z_exit or time_exit:
                exit_price = m['spread'].iloc[i]
                pnl = (exit_price - entry_price) * pos - 2 * COMMISSION
                trades.append(pnl)
                pos = 0
    return trades


def metrics(trades):
    if len(trades) == 0:
        return {'n': 0, 'wr': 0, 'sharpe': 0, 'total': 0}
    r = pd.Series(trades)
    sharpe = r.mean() / r.std() if r.std() > 0 else 0
    return {'n': len(r), 'wr': 100 * (r > 0).mean(), 'sharpe': sharpe, 'total': r.sum()}


if __name__ == '__main__':
    entry_grid = [1.5, 2.0, 2.5, 3.0]
    exit_grid = [0.0, 0.25, 0.5, 1.0]
    window_grid = [20, 30, 40, 60]

    for a, b, tf in FAIL_PAIRS:
        m = load_pair(a, b, tf)
        if m is None:
            print(f'{a}-{b}_{tf}: нет данных')
            continue
        print(f'\n=== {a}-{b}_{tf} ===')
        results = []
        for ez, xz, w in itertools.product(entry_grid, exit_grid, window_grid):
            trades = simulate(m, ez, xz, window=w)
            met = metrics(trades)
            if met['n'] >= 5:  # минимум 5 сделок
                results.append({
                    'entry_z': ez, 'exit_z': xz, 'window': w,
                    'n': met['n'], 'wr': met['wr'], 'sharpe': met['sharpe']
                })
        df = pd.DataFrame(results)
        if len(df) == 0:
            print('Нет результатов с n>=5')
            continue
        # Топ-10 по Sharpe
        df = df.sort_values('sharpe', ascending=False)
        print('Топ-10 по Sharpe:')
        print(df.head(10).to_string(index=False))
