#!/usr/bin/env python3
"""
walk_forward_coint.py — walk-forward для коинтегрированных пар.

Использует residuals от OLS:
  spread = log_a - β·log_b - α
  z-score по residuals.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from statsmodels.regression.linear_model import OLS
from statsmodels.tools import add_constant

CANDLES = Path('/root/finlab/data/candles')
COMMISSION = 0.0028
TIME_EXIT_BARS = 120
N_FOLDS = 5

COINT_PAIRS = [
    ('SFIN', 'SH', 'M10'),
    ('BELU', 'NB', 'M10'),
    ('SFIN', 'SH', 'H1'),
]


def load_pair(a, b, tf):
    fa = CANDLES / f'{a}_{tf}.parquet'
    fb = CANDLES / f'{b}_{tf}.parquet'
    if not fa.exists() or not fb.exists(): return None
    da = pd.read_parquet(fa); db = pd.read_parquet(fb)
    _ca = 'begin' if 'begin' in da.columns else 'tradedate'
    _cb = 'begin' if 'begin' in db.columns else 'tradedate'
    a_df = da[[_ca, 'close']].rename(columns={_ca: 'dt'})
    b_df = db[[_cb, 'close']].rename(columns={_cb: 'dt'})
    m = pd.merge(a_df, b_df, on='dt', suffixes=('_a', '_b'))
    m['close_a'] = m['close_a'].apply(lambda x: float(x) if not isinstance(x, bytes) else 0.0)
    m['close_b'] = m['close_b'].apply(lambda x: float(x) if not isinstance(x, bytes) else 0.0)
    return m.sort_values('dt').reset_index(drop=True)


def compute_residuals(m, window=60):
    """Rolling OLS: spread = log_a - β·log_b - α."""
    m = m.copy()
    m['log_a'] = np.log(m['close_a'])
    m['log_b'] = np.log(m['close_b'])
    # Rolling β и α
    residuals = []
    for i in range(len(m)):
        if i < window:
            residuals.append(np.nan)
            continue
        y = m['log_a'].iloc[i-window:i].values
        x = add_constant(m['log_b'].iloc[i-window:i].values)
        try:
            model = OLS(y, x).fit()
            beta = model.params[1]
            alpha = model.params[0]
            resid = m['log_a'].iloc[i] - beta * m['log_b'].iloc[i] - alpha
            residuals.append(resid)
        except Exception:
            residuals.append(np.nan)
    m['residual'] = residuals
    return m


def simulate(m, entry_z, exit_z, window=60):
    m = m.copy()
    m['mean'] = m['residual'].rolling(window).mean()
    m['std'] = m['residual'].rolling(window).std()
    m['z'] = (m['residual'] - m['mean']) / m['std']
    pos = 0; entry_price = 0; entry_i = 0; trades = []
    for i in range(window, len(m)):
        z = m['z'].iloc[i]
        if pd.isna(z): continue
        if pos == 0:
            if z >= entry_z: pos = -1; entry_price = m['residual'].iloc[i]; entry_i = i
            elif z <= -entry_z: pos = 1; entry_price = m['residual'].iloc[i]; entry_i = i
        else:
            if (i - entry_i) >= TIME_EXIT_BARS or abs(z) <= exit_z:
                pnl = (m['residual'].iloc[i] - entry_price) * pos - 2 * COMMISSION
                trades.append(pnl); pos = 0
    return trades


def metrics(trades):
    if len(trades) == 0: return {'n':0,'wr':0,'sharpe':0,'total':0}
    r = pd.Series(trades)
    return {'n': len(r), 'wr': 100*(r>0).mean(), 'sharpe': r.mean()/r.std() if r.std()>0 else 0, 'total': r.sum()}


if __name__ == '__main__':
    for a, b, tf in COINT_PAIRS:
        m = load_pair(a, b, tf)
        if m is None or len(m) < 300: continue
        m = compute_residuals(m, window=60)
        print(f'\n=== {a}-{b}_{tf} ===')
        fold_size = len(m) // (N_FOLDS + 1)
        n_ok = 0
        for k in range(N_FOLDS):
            test = m.iloc[(k+1)*fold_size:(k+2)*fold_size].reset_index(drop=True)
            trades = simulate(test, 2.5, 0.5, window=30)
            met = metrics(trades)
            verdict = '✅' if met['sharpe'] > 0.3 and met['n'] >= 3 else '❌'
            if verdict == '✅': n_ok += 1
            print(f'  fold {k+1}: n={met["n"]}, WR={met["wr"]:.1f}%, Sharpe={met["sharpe"]:.3f} {verdict}')
        print(f'  → {n_ok}/{N_FOLDS} фолдов OK')
