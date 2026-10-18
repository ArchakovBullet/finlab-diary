#!/usr/bin/env python3
"""kalman_walk_forward.py — 5-фолдовый walk-forward: Fixed vs Kalman (H4)."""
import pandas as pd
import numpy as np
from pathlib import Path

CANDLES = Path('/root/finlab/data/candles')
COMMISSION = 0.0028
WINDOW = 20
ENTRY_Z = 2.0
EXIT_Z = 0.5
TIME_EXIT_BARS = 120
N_FOLDS = 5

PAIRS = [
    ('GD', 'SV', 'H4'),
    ('PD', 'SV', 'H4'),
    ('PT', 'SV', 'H4'),
    ('GD', 'PT', 'H4'),
    ('LK', 'IMOEXF', 'H4'),
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


def kalman_beta(y, x, delta=1e-4, R=1e-3):
    n = len(y)
    beta = np.zeros(n)
    P = np.zeros(n)
    beta[0] = 1.0
    P[0] = 1.0
    Q = delta
    for t in range(1, n):
        beta_pred = beta[t-1]
        P_pred = P[t-1] + Q
        H = x[t]
        S = H * P_pred * H + R
        K = P_pred * H / S
        beta[t] = beta_pred + K * (y[t] - H * beta_pred)
        P[t] = (1 - K * H) * P_pred
    return beta


def simulate(m, entry_z, exit_z, use_kalman):
    m = m.copy()
    if use_kalman:
        beta = kalman_beta(m['close_a'].values, m['close_b'].values)
        m['spread'] = np.log(m['close_a']) - beta * np.log(m['close_b'])
    m['mean'] = m['spread'].rolling(WINDOW).mean()
    m['std'] = m['spread'].rolling(WINDOW).std()
    m['z'] = (m['spread'] - m['mean']) / m['std']
    pos = 0; entry_price = 0; entry_i = 0; trades = []
    for i in range(WINDOW, len(m)):
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


def stats(trades):
    if not trades:
        return {'n': 0, 'pnl': 0, 'wr': 0, 'sharpe': 0}
    t = np.array(trades)
    return {
        'n': len(t),
        'pnl': float(t.sum()),
        'wr': float((t > 0).mean()),
        'sharpe': float(t.mean() / t.std() * np.sqrt(252)) if t.std() > 0 else 0,
    }


def main():
    print(f'{"Pair":<15} {"Fold":>4} {"Method":<8} {"n":>5} {"PnL":>10} {"WR":>6} {"Sharpe":>8}')
    print('-' * 70)
    all_results = []
    for a, b, tf in PAIRS:
        m = load_pair(a, b, tf)
        if m is None or len(m) < 500:
            print(f'{a}-{b}_{tf}: нет данных')
            continue
        pair_name = f'{a}-{b}_{tf}'
        fold_size = len(m) // N_FOLDS
        for fold in range(N_FOLDS):
            start = fold * fold_size
            end = start + fold_size if fold < N_FOLDS - 1 else len(m)
            sub = m.iloc[start:end].reset_index(drop=True)
            if len(sub) < 100:
                continue
            s_fixed = stats(simulate(sub, ENTRY_Z, EXIT_Z, use_kalman=False))
            s_kalman = stats(simulate(sub, ENTRY_Z, EXIT_Z, use_kalman=True))
            print(f'{pair_name:<15} {fold:>4} {"Fixed":<8} {s_fixed["n"]:>5} {s_fixed["pnl"]:>10.4f} {s_fixed["wr"]:>6.2f} {s_fixed["sharpe"]:>8.2f}')
            print(f'{pair_name:<15} {fold:>4} {"Kalman":<8} {s_kalman["n"]:>5} {s_kalman["pnl"]:>10.4f} {s_kalman["wr"]:>6.2f} {s_kalman["sharpe"]:>8.2f}')
            all_results.append({
                'pair': pair_name, 'fold': fold,
                'fixed_pnl': s_fixed['pnl'], 'fixed_wr': s_fixed['wr'], 'fixed_sharpe': s_fixed['sharpe'],
                'kalman_pnl': s_kalman['pnl'], 'kalman_wr': s_kalman['wr'], 'kalman_sharpe': s_kalman['sharpe'],
            })
        print()

    df = pd.DataFrame(all_results)
    if df.empty:
        print('Нет данных.')
        return

    print('=' * 70)
    print('СВОДКА ПО ФОЛДАМ (среднее по парам)')
    print('=' * 70)
    summary = df.groupby('fold').agg(
        fixed_pnl=('fixed_pnl', 'sum'),
        fixed_wr=('fixed_wr', 'mean'),
        fixed_sharpe=('fixed_sharpe', 'mean'),
        kalman_pnl=('kalman_pnl', 'sum'),
        kalman_wr=('kalman_wr', 'mean'),
        kalman_sharpe=('kalman_sharpe', 'mean'),
    ).round(4)
    print(summary)

    print()
    print('=' * 70)
    print('ИТОГО (все фолды)')
    print('=' * 70)
    print(f'Fixed:  PnL={df["fixed_pnl"].sum():.4f}, WR={df["fixed_wr"].mean():.2f}, Sharpe={df["fixed_sharpe"].mean():.2f}')
    print(f'Kalman: PnL={df["kalman_pnl"].sum():.4f}, WR={df["kalman_wr"].mean():.2f}, Sharpe={df["kalman_sharpe"].mean():.2f}')


if __name__ == '__main__':
    main()
