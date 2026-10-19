#!/usr/bin/env python3
"""
kalman_walk_forward_entry_z.py — перебор entry_z для Кальмана (v3).

По образцу kalman_walk_forward_slip.py (Kalman-β + simulate).
Отличие: перебирает entry_z по сетке, покрывает все 8 enabled-пар v3 (M10 + H4).
Комиссия: 0.28% (0.14% × 2). Slippage: 0.02%.
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path

CANDLES = Path('/root/finlab/data/candles')
CONFIG_FILE = Path('/root/finlab/FinLabPy/My_Indicators/pairs_config_v3.json')

COMMISSION = 0.0028
SLIPPAGE = 0.0002
TIME_EXIT_BARS_M10 = 120  # 20 часов на M10
TIME_EXIT_BARS_H4 = 30    # 120 часов на H4 (=30*4ч)
KALMAN_WARMUP = 100       # прогрев: первые 100 строк β не считаем
N_FOLDS = 5
ENTRY_Z_GRID = [1.2, 1.5, 1.8, 2.0, 2.5, 3.0]
EXIT_Z = 0.5
WINDOW = 20


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
    m = m[(m['close_a'] > 0) & (m['close_b'] > 0)].reset_index(drop=True)
    if len(m) < 200:
        return None
    return m.sort_values('dt').reset_index(drop=True)


def kalman_beta(y, x, delta=1e-4, R=1e-3):
    """Кальман-β (как в kalman_walk_forward_slip.py)."""
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


def simulate(m, entry_z, exit_z, window, time_exit_bars, use_kalman=True, slippage=SLIPPAGE, warmup=KALMAN_WARMUP):
    """Gross PnL (без cost) + отдельно net PnL (с cost). Прогрев Кальмана."""
    df = m.copy()
    log_a = np.log(df['close_a'].values)
    log_b = np.log(df['close_b'].values)
    if use_kalman:
        beta = kalman_beta(log_a, log_b)
        df['beta'] = beta
        df['spread'] = log_a - beta * log_b
    else:
        df['spread'] = log_a - log_b
    df['mean'] = df['spread'].rolling(window).mean()
    df['std'] = df['spread'].rolling(window).std()
    df['z'] = (df['spread'] - df['mean']) / df['std']

    pos = 0; entry_price = 0; entry_i = 0; trades_gross = []
    start_i = max(window, warmup)
    for i in range(start_i, len(df)):
        z = df['z'].iloc[i]
        if pd.isna(z):
            continue
        if pos == 0:
            if z >= entry_z:
                pos = -1; entry_price = df['spread'].iloc[i]; entry_i = i
            elif z <= -entry_z:
                pos = 1; entry_price = df['spread'].iloc[i]; entry_i = i
        else:
            if (i - entry_i) >= time_exit_bars or abs(z) <= exit_z:
                raw_pnl = (df['spread'].iloc[i] - entry_price) * pos
                trades_gross.append(raw_pnl)
                pos = 0
    cost = 2 * COMMISSION + 2 * slippage
    trades_net = [t - cost for t in trades_gross]
    return trades_gross, trades_net


def stats(trades):
    if not trades:
        return {'n': 0, 'pnl': 0.0, 'wr': 0.0, 'sharpe': 0.0, 'avg': 0.0}
    t = np.array(trades)
    std = t.std()
    return {
        'n': int(len(t)),
        'pnl': float(t.sum()),
        'wr': float((t > 0).mean()),
        'sharpe': float(t.mean() / std * np.sqrt(252)) if std > 0 else 0.0,
        'avg': float(t.mean()),
    }


def main():
    cfg = json.loads(CONFIG_FILE.read_text())
    pairs = [(k, v) for k, v in cfg['pairs'].items() if v.get('enabled')]
    print(f'Enabled-пар: {len(pairs)}')
    print(f'Entry_z grid: {ENTRY_Z_GRID}')
    print(f'Фолдов: {N_FOLDS}, window={WINDOW}, exit_z={EXIT_Z}')
    print(f'Commission={COMMISSION}, Slippage={SLIPPAGE}')
    print()

    rows = []
    for pair_name, pcfg in pairs:
        tf = 'M10' if '_M10' in pair_name else 'H4'
        base = pair_name.replace('_M10', '').replace('_H4', '')
        parts = base.split('-')
        if len(parts) != 2:
            print(f'  [skip] {pair_name}: bad base_pair')
            continue
        a, b = parts
        m = load_pair(a, b, tf)
        if m is None:
            print(f'  [skip] {pair_name}: no data')
            continue
        n = len(m)
        fold_size = n // N_FOLDS
        print(f'\n== {pair_name} (tf={tf}, rows={n}, fold_size={fold_size})')
        for ez in ENTRY_Z_GRID:
            fold_results = []
            for f in range(N_FOLDS):
                start = f * fold_size
                end = (f + 1) * fold_size if f < N_FOLDS - 1 else n
                sub = m.iloc[start:end].reset_index(drop=True)
                if len(sub) < WINDOW + 20:
                    continue
                teb = TIME_EXIT_BARS_M10 if tf=='M10' else TIME_EXIT_BARS_H4
                tg, tn = simulate(sub, ez, EXIT_Z, WINDOW, teb, use_kalman=True)
                s_g = stats(tg); s_n = stats(tn)
                s_g['net_pnl']=s_n['pnl']; s_g['net_wr']=s_n['wr']; s_g['net_sharpe']=s_n['sharpe']
                fold_results.append(s_g)
            if not fold_results:
                continue
            total_n = sum(r['n'] for r in fold_results)
            gross_pnl = sum(r['pnl'] for r in fold_results)
            net_pnl = sum(r['net_pnl'] for r in fold_results)
            nz=[r for r in fold_results if r['n']>0]
            avg_wr = float(np.mean([r['wr'] for r in nz])) if nz else 0.0
            avg_sharpe = float(np.mean([r['sharpe'] for r in nz])) if nz else 0.0
            avg_net_sharpe = float(np.mean([r['net_sharpe'] for r in nz])) if nz else 0.0
            print(f'  entry_z={ez:.2f}: n={total_n:4d} GROSS={gross_pnl:9.4f} NET={net_pnl:9.4f} wr={avg_wr:.3f} sharpe={avg_sharpe:7.3f} net_sharpe={avg_net_sharpe:7.3f}')
            rows.append({
                'pair': pair_name, 'tf': tf, 'entry_z': ez,
                'n': total_n, 'gross_pnl': gross_pnl, 'net_pnl': net_pnl,
                'wr': avg_wr, 'gross_sharpe': avg_sharpe, 'net_sharpe': avg_net_sharpe,
            })

    out = Path('/root/finlab/logs') / 'kalman_wf_entry_z.csv'
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f'\n✅ CSV: {out}')

    # Итог: лучший entry_z по каждой паре (по Sharpe)
    if rows:
        print('\n=== ЛУЧШИЙ entry_z ПО ПАРЕ (по Sharpe) ===')
        df = pd.DataFrame(rows)
        for pair in df['pair'].unique():
            sub = df[df['pair'] == pair]
            best = sub.loc[sub['net_sharpe'].idxmax()]
            print(f"  {pair:20s}: entry_z={best['entry_z']:.2f}  net_sharpe={best['net_sharpe']:7.3f}  gross={best['gross_pnl']:9.4f}  net={best['net_pnl']:9.4f}  wr={best['wr']:.3f}  n={int(best['n'])}")


if __name__ == '__main__':
    main()
