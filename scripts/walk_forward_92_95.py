#!/usr/bin/env python3
"""walk_forward_92_95.py — 5-фолдовый walk-forward для 92-95."""
import pandas as pd
import numpy as np
from pathlib import Path

CANDLES = Path('/root/finlab/data/candles')
COMMISSION = 0.0028
TIME_EXIT_BARS = 120
N_FOLDS = 5


def load_pair(a, b, tf):
    fa = CANDLES / f'{a}_{tf}.parquet'
    fb = CANDLES / f'{b}_{tf}.parquet'
    if not fa.exists() or not fb.exists(): return None
    da = pd.read_parquet(fa); db = pd.read_parquet(fb)
    _ca = 'begin' if 'begin' in da.columns else 'tradedate'
    _cb = 'begin' if 'begin' in db.columns else 'tradedate'
    a_df = da[[_ca, 'close']].rename(columns={_ca: 'dt'})
    b_df = db[[_cb, 'close']].rename(columns={_cb: 'dt'})
    m = pd.merge(a_df, b_df, on='dt', suffixes=('_a', '_b')).sort_values('dt').reset_index(drop=True)
    m['close_a'] = m['close_a'].apply(lambda x: float(x) if not isinstance(x, bytes) else 0.0)
    m['close_b'] = m['close_b'].apply(lambda x: float(x) if not isinstance(x, bytes) else 0.0)
    m['log_a'] = np.log(m['close_a'].replace(0, np.nan))
    m['log_b'] = np.log(m['close_b'].replace(0, np.nan))
    return m


def compute_residuals(m, resid_window=30):
    from statsmodels.regression.linear_model import OLS
    from statsmodels.tools import add_constant
    resid = []
    for i in range(len(m)):
        if i < resid_window:
            resid.append(np.nan); continue
        y = m['log_a'].iloc[i-resid_window:i].values
        x = add_constant(m['log_b'].iloc[i-resid_window:i].values)
        try:
            model = OLS(y, x).fit()
            beta = model.params[1]; alpha = model.params[0]
            r = m['log_a'].iloc[i] - beta * m['log_b'].iloc[i] - alpha
            resid.append(r)
        except Exception:
            resid.append(np.nan)
    m['resid'] = resid
    return m


def simulate(m, entry_z, exit_z, window=20):
    m = m.copy()
    m['mean'] = m['resid'].rolling(window).mean()
    m['std'] = m['resid'].rolling(window).std()
    m['z'] = (m['resid'] - m['mean']) / m['std']
    pos = 0; entry_price = 0; entry_i = 0; trades = []
    for i in range(window, len(m)):
        z = m['z'].iloc[i]
        if pd.isna(z): continue
        if pos == 0:
            if z >= entry_z: pos = -1; entry_price = m['resid'].iloc[i]; entry_i = i
            elif z <= -entry_z: pos = 1; entry_price = m['resid'].iloc[i]; entry_i = i
        else:
            if (i - entry_i) >= TIME_EXIT_BARS or abs(z) <= exit_z:
                pnl = (m['resid'].iloc[i] - entry_price) * pos - 2 * COMMISSION
                trades.append(pnl); pos = 0
    return trades


def metrics(trades):
    if len(trades) == 0: return {'n':0,'wr':0,'sharpe':0,'total':0}
    r = pd.Series(trades)
    return {'n': len(r), 'wr': 100*(r>0).mean(), 'sharpe': r.mean()/r.std() if r.std()>0 else 0, 'total': r.sum()}


if __name__ == '__main__':
    for tf in ['H1', 'H4']:
        m = load_pair('92', '95', tf)
        if m is None or len(m) < 50: continue
        m = compute_residuals(m, resid_window=20)
        fold_size = len(m) // (N_FOLDS + 1)
        print(f'\n=== 92-95_{tf} (n={len(m)}) ===')
        n_ok = 0
        for k in range(N_FOLDS):
            test = m.iloc[(k+1)*fold_size:(k+2)*fold_size].reset_index(drop=True)
            met = metrics(simulate(test, 2.0, 0.5, 20))
            verdict = '✅' if met['sharpe'] > 0.3 and met['n'] >= 3 else '❌'
            if verdict == '✅': n_ok += 1
            print(f'  fold {k+1}: n={met["n"]}, WR={met["wr"]:.1f}%, Sharpe={met["sharpe"]:.3f} {verdict}')
        print(f'  → {n_ok}/{N_FOLDS} фолдов OK')
