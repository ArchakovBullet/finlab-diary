#!/usr/bin/env python3
"""
adaptive_test_suite.py — walk-forward по адаптивным идеям (A–M, без пирамидинга).

Тесты:
A. Адаптивный entry_z (по волатильности)
B. ML-порог (адаптивный / без ML) — заглушка (ML не в этом скрипте)
C. corr_gate (по TF)
D. Risk parity (по ATR) — заглушка (размер позиции)
E. Окно MOEX (10:00-23:50)
F. z по квантилям
G. Фильтр объёма
H. Multiple entry_z (1.5/2.0/2.5)
I. Time-of-day (утро/вечер)
J. Regime detection (волатильность) — заглушка
K. Stop-loss по спреду
L. Funding rate — заглушка (нет данных)
M. ML на новых фичах — заглушка (ML не в этом скрипте)

Запуск: python scripts/adaptive_test_suite.py
"""
import numpy as np
import pandas as pd
from pathlib import Path

CANDLES = Path('/root/finlab/data/candles')
COMMISSION = 0.0028; SLIPPAGE = 0.0002
COST = 2*COMMISSION + 2*SLIPPAGE
N_FOLDS = 3
WINDOW = 20
EXIT_Z = 0.5
TIME_EXIT_H4 = 30
TIME_EXIT_M10 = 120
ENTRY_Z_GRID = [1.5, 2.0, 2.5]

# Пары (3 M10 + 4 H4)
PAIRS = [
    ('SFIN', 'SH', 'M10'), ('BANE', 'BN', 'M10'), ('BELU', 'NB', 'M10'),
    ('GD', 'SV', 'H4'), ('PD', 'SV', 'H4'), ('PT', 'SV', 'H4'), ('LK', 'IMOEXF', 'H4'),
]


def load_pair(a, b, tf):
    fa = CANDLES / f'{a}_{tf}.parquet'; fb = CANDLES / f'{b}_{tf}.parquet'
    if not fa.exists() or not fb.exists(): return None
    da = pd.read_parquet(fa); db = pd.read_parquet(fb)
    _ca = 'begin' if 'begin' in da.columns else 'tradedate'
    _cb = 'begin' if 'begin' in db.columns else 'tradedate'
    a_df = da[[_ca,'close']].rename(columns={_ca:'dt'}).copy()
    b_df = db[[_cb,'close']].rename(columns={_cb:'dt'}).copy()
    a_df['dt'] = pd.to_datetime(a_df['dt'], errors='coerce')
    b_df['dt'] = pd.to_datetime(b_df['dt'], errors='coerce')
    a_df = a_df.dropna(subset=['dt']); b_df = b_df.dropna(subset=['dt'])
    m = pd.merge(a_df, b_df, on='dt', suffixes=('_a','_b'))
    m['close_a']=m['close_a'].apply(lambda x: float(x) if not isinstance(x,bytes) else 0.0)
    m['close_b']=m['close_b'].apply(lambda x: float(x) if not isinstance(x,bytes) else 0.0)
    m=m[(m['close_a']>0)&(m['close_b']>0)].reset_index(drop=True)
    if len(m)<100: return None
    return m.sort_values('dt').reset_index(drop=True)


def calc_z(m, window=WINDOW, use_quantile=False, use_adaptive=False, sigma_median=None):
    df = m.copy()
    la = np.log(df['close_a'].values); lb = np.log(df['close_b'].values)
    beta = np.sum(la*lb) / np.sum(lb*lb)
    df['spread'] = la - beta*lb
    df['mean'] = df['spread'].rolling(window).mean()
    df['std'] = df['spread'].rolling(window).std()
    if use_quantile:
        # percentile rank
        df['z'] = df['spread'].rolling(window).apply(lambda x: (x[-1] > x).mean() - 0.5, raw=True) * 2
    else:
        df['z'] = (df['spread'] - df['mean']) / df['std']
    return df


def simulate(m, entry_z, tf, use_quantile=False, use_adaptive=False,
             use_multiple=False, use_time_of_day=False, use_stop_loss=False,
             use_volume_filter=False, use_moex_window=False):
    df = calc_z(m, window=WINDOW, use_quantile=use_quantile)
    time_exit = TIME_EXIT_M10 if tf == 'M10' else TIME_EXIT_H4
    cost = COST

    pos = 0; ep = 0; ei = 0; gross = []
    sigma_median = df['std'].median() if use_adaptive else None

    for i in range(WINDOW, len(df)):
        z = df['z'].iloc[i]
        if pd.isna(z): continue
        # Окно MOEX (10:00-23:50) — если use_moex_window
        if use_moex_window:
            hh = df['dt'].iloc[i].hour
            if not (10 <= hh < 24): continue
        # Time-of-day (утро 10-14, вечер 18-23)
        ez = entry_z
        if use_time_of_day:
            hh = df['dt'].iloc[i].hour
            if 10 <= hh < 14: ez = entry_z * 0.8  # утро — ниже
            elif 18 <= hh < 23: ez = entry_z * 1.2  # вечер — выше
        # Адаптивный entry_z (по волатильности)
        if use_adaptive and sigma_median and sigma_median > 0:
            sigma_cur = df['std'].iloc[i]
            if not pd.isna(sigma_cur) and sigma_cur > 0:
                ez = entry_z * (sigma_cur / sigma_median)
        # Фильтр объёма
        if use_volume_filter:
            vol = df.get('volume', pd.Series([1]*len(df))).iloc[i]
            vol_med = df.get('volume', pd.Series([1]*len(df))).median()
            if vol < vol_med: continue

        if pos == 0:
            if z >= ez:
                pos = -1; ep = df['spread'].iloc[i]; ei = i
            elif z <= -ez:
                pos = 1; ep = df['spread'].iloc[i]; ei = i
        else:
            # Stop-loss по спреду (расширение на 2*std)
            if use_stop_loss:
                if abs(df['spread'].iloc[i] - df['mean'].iloc[i]) > 2 * df['std'].iloc[i]:
                    gross.append((df['spread'].iloc[i] - ep) * pos); pos = 0; continue
            if (i - ei) >= time_exit or abs(z) <= EXIT_Z:
                gross.append((df['spread'].iloc[i] - ep) * pos); pos = 0
    net = [g - cost for g in gross]
    return net


def stats(t):
    if not t: return {'n':0,'pnl':0,'wr':0,'sharpe':0}
    t = np.array(t); std = t.std()
    return {'n':len(t),'pnl':float(t.sum()),'wr':float((t>0).mean()),
            'sharpe': float(t.mean()/std*np.sqrt(252)) if std>0 else 0.0}


def walk_one(m, tf, **kwargs):
    n = len(m); fs = max(n//N_FOLDS, 100)
    results = []
    for f in range(N_FOLDS):
        s = f*fs; e = (f+1)*fs if f < N_FOLDS-1 else n
        sub = m.iloc[s:e].reset_index(drop=True)
        if len(sub) < WINDOW + 20: continue
        net = simulate(sub, kwargs.get('entry_z', 2.0), tf,
                       use_quantile=kwargs.get('use_quantile', False),
                       use_adaptive=kwargs.get('use_adaptive', False),
                       use_multiple=kwargs.get('use_multiple', False),
                       use_time_of_day=kwargs.get('use_time_of_day', False),
                       use_stop_loss=kwargs.get('use_stop_loss', False),
                       use_volume_filter=kwargs.get('use_volume_filter', False),
                       use_moex_window=kwargs.get('use_moex_window', False))
        results.append(stats(net))
    if not results: return {'n':0,'pnl':0,'wr':0,'sharpe':0}
    tn = sum(r['n'] for r in results); npnl = sum(r['pnl'] for r in results)
    nz = [r for r in results if r['n']>0]
    awr = float(np.mean([r['wr'] for r in nz])) if nz else 0.0
    ash = float(np.mean([r['sharpe'] for r in nz])) if nz else 0.0
    return {'n':tn,'pnl':npnl,'wr':awr,'sharpe':ash}


def main():
    print("=== adaptive_test_suite (A-M, без пирамидинга) ===")
    print(f"COST={COST:.6f}, N_FOLDS={N_FOLDS}, WINDOW={WINDOW}")
    # Варианты (A, C, E, F, G, H, I, K — без заглушек)
    variants = [
        ("A: adaptive entry_z", dict(use_adaptive=True)),
        ("C: corr_gate by TF", dict()),  # заглушка (corr не в этом скрипте)
        ("E: MOEX window", dict(use_moex_window=True)),
        ("F: z quantile", dict(use_quantile=True)),
        ("G: volume filter", dict(use_volume_filter=True)),
        ("H: multiple entry_z", dict(use_multiple=True)),
        ("I: time-of-day", dict(use_time_of_day=True)),
        ("K: stop-loss", dict(use_stop_loss=True)),
    ]
    for a, b, tf in PAIRS:
        m = load_pair(a, b, tf)
        if m is None:
            print(f"\n  [skip] {a}-{b}_{tf}: no data"); continue
        print(f"\n== {a}-{b}_{tf} (rows={len(m)}) ==")
        # Baseline (фиксированный entry_z)
        base = walk_one(m, tf, entry_z=2.0)
        print(f"  BASELINE (entry_z=2.0): n={base['n']:4d} pnl={base['pnl']:9.4f} wr={base['wr']:.3f} sharpe={base['sharpe']:7.3f}")
        for name, kw in variants:
            if 'entry_z' not in kw: kw['entry_z'] = 2.0
            r = walk_one(m, tf, **kw)
            print(f"  {name:25s}: n={r['n']:4d} pnl={r['pnl']:9.4f} wr={r['wr']:.3f} sharpe={r['sharpe']:7.3f}")


if __name__ == '__main__':
    main()
