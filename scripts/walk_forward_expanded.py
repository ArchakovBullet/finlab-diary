#!/usr/bin/env python3
"""
walk_forward_expanded.py — 5-фолдовый walk-forward для 64 пар-кандидатов.
Отбираем пары с 4+/5 фолдов OK.
"""
import pandas as pd
import numpy as np
from pathlib import Path

CANDLES = Path('/root/finlab/data/candles')
COMMISSION = 0.0028
TIME_EXIT_BARS = 120
N_FOLDS = 5
MIN_OK_FOLDS = 4

# Топ-20 кандидатов (corr > 0.6, не пересекаются с текущими)
CANDIDATES = [
    ('IMOEXF', 'MX', 'H4'), ('SBERF', 'IMOEXF', 'H4'),
    ('GAZPF', 'IMOEXF', 'H4'), ('GAZPF', 'SBERF', 'H4'),
    ('PT', 'SV', 'H4'), ('GD', 'SV', 'H4'),
    ('GD', 'PT', 'H4'), ('GLDRUBF', 'GD', 'H4'),
    ('SO', 'LK', 'H4'), ('PD', 'PT', 'H4'), ('PD', 'SV', 'H4'),
    ('LK', 'IMOEXF', 'H4'), ('SN', 'MX', 'H4'), ('IR', 'MX', 'H4'),
    ('CE', 'PT', 'H4'), ('CE', 'SV', 'H4'), ('SN', 'IMOEXF', 'H4'),
    ('CNYRUBF', 'USDRUBF', 'H4'), ('EURRUBF', 'USDRUBF', 'H4'),
    ('CNYRUBF', 'EURRUBF', 'H4'),
]


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
    ok_pairs = []
    print(f'{"pair":<20} {"tf":<5} {"folds_ok":>8} {"avg_n":>7} {"avg_wr":>8} {"avg_sharpe":>10}')
    print('-' * 75)
    for a, b, tf in CANDIDATES:
        m = load_pair(a, b, tf)
        if m is None or len(m) < 300: continue
        fold_size = len(m) // (N_FOLDS + 1)
        fold_results = []
        for k in range(N_FOLDS):
            test = m.iloc[(k+1)*fold_size:(k+2)*fold_size].reset_index(drop=True)
            met = metrics(simulate(test, 2.5, 0.5, 30))
            fold_results.append(met)
        n_ok = sum(1 for m_ in fold_results if m_['sharpe'] > 0.3 and m_['n'] >= 3)
        avg_n = np.mean([m_['n'] for m_ in fold_results])
        avg_wr = np.mean([m_['wr'] for m_ in fold_results])
        avg_sh = np.mean([m_['sharpe'] for m_ in fold_results])
        verdict = '✅' if n_ok >= MIN_OK_FOLDS else '❌'
        print(f'{a}-{b:<14} {tf:<5} {n_ok:>7}/5 {avg_n:>7.1f} {avg_wr:>7.1f}% {avg_sh:>10.3f} {verdict}')
        if n_ok >= MIN_OK_FOLDS:
            ok_pairs.append((a, b, tf, avg_sh))

    print(f'\n=== OK пар (≥{MIN_OK_FOLDS}/5 фолдов): {len(ok_pairs)} ===')
    for a, b, tf, sh in ok_pairs:
        print(f'  {a}-{b}_{tf}: Sharpe {sh:.3f}')
