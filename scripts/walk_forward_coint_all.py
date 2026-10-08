#!/usr/bin/env python3
"""walk_forward_coint_all.py — cointegration walk-forward для всех пар."""
import pandas as pd
import numpy as np
from pathlib import Path
from statsmodels.regression.linear_model import OLS
from statsmodels.tools import add_constant

CANDLES = Path('/root/finlab/data/candles')
COMMISSION = 0.0028
TIME_EXIT_BARS = 120
N_FOLDS = 5
MIN_OK = 4

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
    m = m.copy()
    m['log_a'] = np.log(m['close_a'])
    m['log_b'] = np.log(m['close_b'])
    residuals = []
    for i in range(len(m)):
        if i < window:
            residuals.append(np.nan); continue
        y = m['log_a'].iloc[i-window:i].values
        x = add_constant(m['log_b'].iloc[i-window:i].values)
        try:
            model = OLS(y, x).fit()
            beta = model.params[1]; alpha = model.params[0]
            resid = m['log_a'].iloc[i] - beta * m['log_b'].iloc[i] - alpha
            residuals.append(resid)
        except Exception:
            residuals.append(np.nan)
    m['residual'] = residuals
    return m


def simulate(m, entry_z, exit_z, window=30):
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
    ok_pairs = []
    print(f'{"pair":<20} {"tf":<5} {"folds_ok":>9} {"avg_n":>7} {"avg_wr":>8} {"avg_sharpe":>11} {"verdict":>8}')
    print('-' * 80)
    for a, b, tf in PAIRS:
        m = load_pair(a, b, tf)
        if m is None or len(m) < 300: continue
        m = compute_residuals(m, window=60)
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
        verdict = '✅' if n_ok >= MIN_OK else '❌'
        print(f'{a}-{b:<14} {tf:<5} {n_ok:>7}/5 {avg_n:>7.1f} {avg_wr:>7.1f}% {avg_sh:>11.3f} {verdict:>8}')
        if n_ok >= MIN_OK:
            ok_pairs.append((a, b, tf, avg_sh))

    print(f'\n=== OK пар (≥{MIN_OK}/5): {len(ok_pairs)} ===')
    for a, b, tf, sh in ok_pairs:
        print(f'  {a}-{b}_{tf}: Sharpe {sh:.3f}')
