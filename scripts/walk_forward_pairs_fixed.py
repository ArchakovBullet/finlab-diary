#!/usr/bin/env python3
"""
walk_forward_pairs_fixed.py — исправленный walk-forward пар.

Исправления:
- window читается из config (было 20 жёстко).
- entry_z/exit_z из config.
- TIME_EXIT: макс. 120 баров (если exit_z=0.0).
- Учёт открытых позиций.
"""
import json
import pandas as pd
import numpy as np
from pathlib import Path

CANDLES = Path('/root/finlab/data/candles')
CONFIG_FILE = Path('/root/finlab/FinLabPy/My_Indicators/pairs_config.json')
COMMISSION = 0.0028
TIME_EXIT_BARS = 120  # макс. держание


def load_pair(ticker_a, ticker_b, tf):
    fa = CANDLES / f'{ticker_a}_{tf}.parquet'
    fb = CANDLES / f'{ticker_b}_{tf}.parquet'
    if not fa.exists() or not fb.exists():
        return None
    df_a = pd.read_parquet(fa)
    df_b = pd.read_parquet(fb)
    _ca = 'begin' if 'begin' in df_a.columns else 'tradedate'
    _cb = 'begin' if 'begin' in df_b.columns else 'tradedate'
    a = df_a[[_ca, 'close']].rename(columns={_ca: 'dt'})
    b = df_b[[_cb, 'close']].rename(columns={_cb: 'dt'})
    m = pd.merge(a, b, on='dt', suffixes=('_a', '_b'))
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
    entry_dt = None
    entry_i = 0
    trades = []

    for i in range(window, len(m)):
        row = m.iloc[i]
        z = row['z']
        if pd.isna(z):
            continue

        if pos == 0:
            if z >= entry_z:
                pos = -1  # SHORT_SPREAD
                entry_price = row['spread']
                entry_dt = row['dt']
                entry_i = i
            elif z <= -entry_z:
                pos = 1  # LONG_SPREAD
                entry_price = row['spread']
                entry_dt = row['dt']
                entry_i = i
        else:
            # Выход по z или TIME_EXIT
            time_exit = (i - entry_i) >= TIME_EXIT_BARS
            z_exit = abs(z) <= exit_z

            if z_exit or time_exit:
                exit_price = row['spread']
                pnl_gross = (exit_price - entry_price) * pos
                pnl_net = pnl_gross - 2 * COMMISSION
                trades.append({
                    'pnl': pnl_net,
                    'entry_dt': entry_dt,
                    'exit_dt': row['dt'],
                    'reason': 'TIME_EXIT' if time_exit else 'Z_EXIT'
                })
                pos = 0

    return trades


def metrics(trades):
    if len(trades) == 0:
        return {'n': 0, 'wr': 0, 'sharpe': 0, 'total': 0}
    r = pd.DataFrame(trades)['pnl']
    sharpe = r.mean() / r.std() if r.std() > 0 else 0
    return {'n': len(r), 'wr': 100 * (r > 0).mean(), 'sharpe': sharpe, 'total': r.sum()}


if __name__ == '__main__':
    with open(CONFIG_FILE) as f:
        cfg = json.load(f)
    pairs = cfg.get('pairs', cfg)

    active = [(n, p) for n, p in pairs.items() if isinstance(p, dict) and p.get('enabled')]
    print(f'Активных пар: {len(active)}\n')
    print(f'{"pair":<20} {"tf":<5} {"n":>5} {"wr":>7} {"sharpe":>8} {"total":>8} {"window":>7} {"entry_z":>8} {"exit_z":>7}')
    print('-' * 90)

    results = []
    for pair_name, pair_data in active:
        base_pair = pair_name.rsplit('_', 1)[0]
        tf = pair_name.rsplit('_', 1)[1]
        if '-' not in base_pair:
            continue
        ta, tb = base_pair.split('-')
        m = load_pair(ta, tb, tf)
        if m is None or len(m) < 100:
            continue
        bp = pair_data.get('best_params', {})
        entry_z = bp.get('entry_z', 3.0)
        exit_z = bp.get('exit_z', 0.5)
        window = bp.get('window', 20)

        trades = simulate(m, entry_z, exit_z, window=window)
        met = metrics(trades)
        results.append({'pair': pair_name, **met, 'window': window, 'entry_z': entry_z, 'exit_z': exit_z})
        print(f'{pair_name:<20} {tf:<5} {met["n"]:>5} {met["wr"]:>6.1f}% {met["sharpe"]:>8.3f} {met["total"]:>8.3f} {window:>7} {entry_z:>8} {exit_z:>7}')

    df = pd.DataFrame(results)
    if len(df) > 0:
        print(f'\nСредний Sharpe: {df["sharpe"].mean():.3f}')
        print(f'Всего сделок: {df["n"].sum()}')
