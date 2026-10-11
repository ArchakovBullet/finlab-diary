#!/usr/bin/env python3
"""half_life_analysis.py — расчёт half-life для enabled-пар.

Half-life = период полураспада отклонения спреда от среднего.
Метод: AR(1) на спреде (rolling OLS residuals).
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path
from statsmodels.regression.linear_model import OLS
from statsmodels.tools import add_constant

ROOT = Path('/root/finlab')
CANDLES = ROOT / 'data' / 'candles'
CONFIG = ROOT / 'FinLabPy' / 'My_Indicators' / 'pairs_config.json'

# Enabled-пары (актуально на 11.10.2026)
PAIRS = [
    ('SFIN', 'SH', 'M10'),
    ('BANE', 'BN', 'M10'),
    ('BELU', 'NB', 'M10'),
    ('BR', 'GAZPF', 'H4'),
    ('GAZPF', 'SBERF', 'H4'),
    ('GD', 'PT', 'H4'),
    ('GD', 'SV', 'H4'),
    ('GLDRUBF', 'GD', 'H4'),
    ('LK', 'IMOEXF', 'H4'),
    ('PD', 'SV', 'H4'),
    ('PT', 'SV', 'H4'),
]


def load_pair(a, b, tf):
    fa = CANDLES / f'{a}_{tf}.parquet'
    fb = CANDLES / f'{b}_{tf}.parquet'
    if not fa.exists() or not fb.exists():
        return None
    da = pd.read_parquet(fa); db = pd.read_parquet(fb)
    ca = 'begin' if 'begin' in da.columns else 'tradedate'
    cb = 'begin' if 'begin' in db.columns else 'tradedate'
    a_df = da[[ca, 'close']].rename(columns={ca: 'dt'})
    b_df = db[[cb, 'close']].rename(columns={cb: 'dt'})
    m = pd.merge(a_df, b_df, on='dt', suffixes=('_a', '_b')).sort_values('dt').reset_index(drop=True)
    m['close_a'] = m['close_a'].apply(lambda x: float(x) if not isinstance(x, bytes) else 0.0)
    m['close_b'] = m['close_b'].apply(lambda x: float(x) if not isinstance(x, bytes) else 0.0)
    m['log_a'] = np.log(m['close_a'].replace(0, np.nan))
    m['log_b'] = np.log(m['close_b'].replace(0, np.nan))
    return m


def half_life(spread):
    """Half-life через AR(1): Δspread = λ * spread_lag + ε."""
    spread = spread.dropna()
    if len(spread) < 10:
        return None
    spread_lag = spread.shift(1).dropna()
    spread_diff = (spread - spread.shift(1)).dropna()
    # Выравниваем
    spread_lag = spread_lag.iloc[1:]
    spread_diff = spread_diff.iloc[1:]
    if len(spread_lag) < 10:
        return None
    X = add_constant(spread_lag.values)
    y = spread_diff.values
    try:
        model = OLS(y, X).fit()
        lam = model.params[1]
        if lam >= 0:
            return None  # не mean-reverting
        hl = -np.log(2) / lam
        return float(hl)
    except Exception:
        return None


def compute_spread(m, window=30, resid_window=60):
    """Rolling OLS residuals (как в роботе)."""
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
    return pd.Series(resid)


def main():
    cfg = json.load(open(CONFIG))
    pairs_cfg = cfg.get('pairs', cfg)

    print(f'{"Пара":<20} {"n":>6} {"half_life":>12} {"status":>20}')
    print('-' * 65)

    results = []
    for a, b, tf in PAIRS:
        pair_name = f'{a}-{b}_{tf}'
        m = load_pair(a, b, tf)
        if m is None:
            print(f'{pair_name:<20} — нет данных')
            continue
        bp = pairs_cfg.get(pair_name, {}).get('best_params', {})
        window = bp.get('window', 30)
        resid_window = bp.get('resid_window', 60)
        spread = compute_spread(m, window, resid_window)
        hl = half_life(spread)
        n = len(spread.dropna())

        if hl is None:
            status = '❌ не реверсирует'
            hl_str = '—'
        else:
            if hl < 5:
                status = '⚠️ слишком быстро'
            elif hl > 60:
                status = '⚠️ слишком медленно'
            else:
                status = '✅ здоровый'
            hl_str = f'{hl:.1f}'
        print(f'{pair_name:<20} {n:>6} {hl_str:>12} {status:>20}')
        results.append({'pair': pair_name, 'hl': hl, 'n': n, 'status': status})

    print()
    print('Легенда:')
    print('  < 5   — слишком быстро (шум, комиссии)')
    print('  5-60  — здоровый диапазон')
    print('  > 60  — слишком медленно (не реверсирует)')


if __name__ == '__main__':
    main()
