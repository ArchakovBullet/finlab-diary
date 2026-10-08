#!/usr/bin/env python3
"""
walk_forward_fail_pairs.py — walk-forward для FAIL-пар.

In-sample 70% → оптимизация entry_z, exit_z, window.
Out-of-sample 30% → проверка.
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
    entry_grid = [2.0, 2.5, 3.0]
    exit_grid = [0.0, 0.5, 1.0]
    window_grid = [20, 30, 40]

    for a, b, tf in FAIL_PAIRS:
        m = load_pair(a, b, tf)
        if m is None or len(m) < 200:
            print(f'{a}-{b}_{tf}: недостаточно данных')
            continue

        # In-sample 70% / out-sample 30%
        split = int(len(m) * 0.7)
        m_in = m.iloc[:split].reset_index(drop=True)
        m_out = m.iloc[split:].reset_index(drop=True)

        print(f'\n=== {a}-{b}_{tf} (in={len(m_in)}, out={len(m_out)}) ===')

        # Оптимизация на in-sample
        best = None
        for ez, xz, w in itertools.product(entry_grid, exit_grid, window_grid):
            trades = simulate(m_in, ez, xz, window=w)
            met = metrics(trades)
            if met['n'] < 5:
                continue
            if best is None or met['sharpe'] > best['sharpe']:
                best = {**met, 'entry_z': ez, 'exit_z': xz, 'window': w}

        if best is None:
            print('Нет оптимальных параметров')
            continue

        print(f'IN: entry_z={best["entry_z"]}, exit_z={best["exit_z"]}, window={best["window"]} → Sharpe {best["sharpe"]:.3f}, WR {best["wr"]:.1f}%, n={best["n"]}')

        # Проверка на out-sample
        trades_out = simulate(m_out, best['entry_z'], best['exit_z'], window=best['window'])
        met_out = metrics(trades_out)
        print(f'OUT: Sharpe {met_out["sharpe"]:.3f}, WR {met_out["wr"]:.1f}%, n={met_out["n"]}, total={met_out["total"]:.3f}')

        if met_out['sharpe'] > 0.3 and met_out['n'] >= 5:
            print(f'  ✅ OK: устойчив')
        else:
            print(f'  ❌ FAIL: нестабилен')
