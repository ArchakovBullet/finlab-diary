#!/usr/bin/env python3
"""walk_forward_5folds.py — 5-фолдовый walk-forward для пар."""
import pandas as pd
import numpy as np
from pathlib import Path
import itertools

CANDLES = Path('/root/finlab/data/candles')
CONFIG_FILE = Path('/root/finlab/FinLabPy/My_Indicators/pairs_config.json')
COMMISSION = 0.0028
TIME_EXIT_BARS = 120
N_FOLDS = 5


def load_pair(a, b, tf):
    fa = CANDLES / f'{a}_{tf}.parquet'
    fb = CANDLES / f'{b}_{tf}.parquet'
    if not fa.exists() or not fb.exists():
        return None
    da = pd.read_parquet(fa); db = pd.read_parquet(fb)
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
    pos = 0; entry_price = 0; entry_i = 0; trades = []
    for i in range(window, len(m)):
        z = m['z'].iloc[i]
        if pd.isna(z): continue
        if pos == 0:
            if z >= entry_z: pos = -1; entry_price = m['spread'].iloc[i]; entry_i = i
            elif z <= -entry_z: pos = 1; entry_price = m['spread'].iloc[i]; entry_i = i
        else:
            if (i - entry_i) >= TIME_EXIT_BARS or abs(z) <= exit_z:
                pnl = (m['spread'].iloc[i] - entry_price) * pos - 2 * COMMISSION
                trades.append(pnl); pos = 0
    return trades


def metrics(trades):
    if len(trades) == 0: return {'n':0,'wr':0,'sharpe':0,'total':0}
    r = pd.Series(trades)
    return {'n': len(r), 'wr': 100*(r>0).mean(), 'sharpe': r.mean()/r.std() if r.std()>0 else 0, 'total': r.sum()}


if __name__ == '__main__':
    import json
    with open(CONFIG_FILE) as f:
        cfg = json.load(f)
    pairs = cfg.get('pairs', cfg)
    active = [(n, p) for n, p in pairs.items() if isinstance(p, dict) and p.get('enabled')]

    print(f'{"pair":<20} {"tf":<5} {"fold":<5} {"n":>5} {"wr":>7} {"sharpe":>8} {"verdict":>8}')
    print('-' * 70)

    for pair_name, pair_data in active:
        base_pair = pair_name.rsplit('_', 1)[0]
        tf = pair_name.rsplit('_', 1)[1]
        if '-' not in base_pair: continue
        a, b = base_pair.split('-')
        m = load_pair(a, b, tf)
        if m is None or len(m) < 200: continue

        bp = pair_data.get('best_params', {})
        ez = bp.get('entry_z', 3.0); xz = bp.get('exit_z', 0.5); w = bp.get('window', 20)

        fold_size = len(m) // (N_FOLDS + 1)
        fold_results = []
        for k in range(N_FOLDS):
            test_start = (k + 1) * fold_size
            test_end = test_start + fold_size
            test = m.iloc[test_start:test_end].reset_index(drop=True)
            trades = simulate(test, ez, xz, w)
            met = metrics(trades)
            fold_results.append(met)
            verdict = '✅' if met['sharpe'] > 0.3 and met['n'] >= 3 else '❌'
            print(f'{pair_name:<20} {tf:<5} {k+1:<5} {met["n"]:>5} {met["wr"]:>6.1f}% {met["sharpe"]:>8.3f} {verdict:>8}')
        # Сводка
        n_ok = sum(1 for m_ in fold_results if m_['sharpe'] > 0.3 and m_['n'] >= 3)
        print(f'  → {n_ok}/{N_FOLDS} фолдов OK')
