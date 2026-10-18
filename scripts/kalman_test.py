#!/usr/bin/env python3
"""kalman_test.py — тест фильтра Кальмана на одной паре (GD-PT_H4)."""
import pandas as pd
import numpy as np
from pathlib import Path

CANDLES = Path('/root/finlab/data/candles')
PAIR = 'GD-PT'
TF = 'H4'
COMMISSION = 0.0028
WINDOW = 20
ENTRY_Z = 2.0
EXIT_Z = 0.5
TIME_EXIT_BARS = 120


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
    """Кальман для beta: y = beta * x + eps."""
    n = len(y)
    beta = np.zeros(n)
    P = np.zeros(n)
    beta[0] = 1.0
    P[0] = 1.0
    Q = delta * np.eye(1)
    for t in range(1, n):
        # Predict
        beta_pred = beta[t-1]
        P_pred = P[t-1] + Q[0, 0]
        # Update
        H = x[t]
        S = H * P_pred * H + R
        K = P_pred * H / S
        beta[t] = beta_pred + K * (y[t] - H * beta_pred)
        P[t] = (1 - K * H) * P_pred
    return beta


def simulate_kalman(m, entry_z, exit_z, window=WINDOW):
    m = m.copy()
    # Кальман-бета (адаптивная)
    beta = kalman_beta(m['close_a'].values, m['close_b'].values)
    m['beta'] = beta
    m['spread'] = np.log(m['close_a']) - m['beta'] * np.log(m['close_b'])
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


def simulate_fixed(m, entry_z, exit_z, window=WINDOW):
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
    m = load_pair('GD', 'PT', TF)
    if m is None:
        print('❌ Нет данных')
        return
    print(f'Пара: {PAIR}_{TF}, rows={len(m)}')
    print(f'entry_z={ENTRY_Z}, exit_z={EXIT_Z}, window={WINDOW}')
    print()

    # Fixed beta
    trades_fixed = simulate_fixed(m, ENTRY_Z, EXIT_Z)
    s_fixed = stats(trades_fixed)
    print('=== Fixed beta ===')
    print(s_fixed)

    # Kalman
    trades_kalman = simulate_kalman(m, ENTRY_Z, EXIT_Z)
    s_kalman = stats(trades_kalman)
    print('=== Kalman beta ===')
    print(s_kalman)

    # Сравнение
    print()
    print('=== Сравнение ===')
    print(f'Fixed:  n={s_fixed["n"]}, pnl={s_fixed["pnl"]:.4f}, wr={s_fixed["wr"]:.2f}, sharpe={s_fixed["sharpe"]:.2f}')
    print(f'Kalman: n={s_kalman["n"]}, pnl={s_kalman["pnl"]:.4f}, wr={s_kalman["wr"]:.2f}, sharpe={s_kalman["sharpe"]:.2f}')


if __name__ == '__main__':
    main()
