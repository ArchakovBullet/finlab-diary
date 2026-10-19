"""d1_test.py — walk-forward на D1: Kalman vs OLS для SFIN-SH, BANE-BN, BELU-NB."""
import numpy as np, pandas as pd
from pathlib import Path

CANDLES = Path('/root/finlab/data/candles')
COMMISSION = 0.0028
SLIPPAGE = 0.0002
COST = 2 * COMMISSION + 2 * SLIPPAGE
N_FOLDS = 3
WINDOW = 20
EXIT_Z = 0.5
TIME_EXIT_D1 = 30
ENTRY_Z_GRID = [1.2, 1.5, 1.8, 2.0, 2.5, 3.0]
PAIRS = [('SFIN', 'SH'), ('BANE', 'BN'), ('BELU', 'NB')]
TF = 'D1'


def load_pair(a, b, tf):
    fa = CANDLES / f'{a}_{tf}.parquet'
    fb = CANDLES / f'{b}_{tf}.parquet'
    if not fa.exists() or not fb.exists():
        return None
    da = pd.read_parquet(fa)
    db = pd.read_parquet(fb)
    _ca = 'begin' if 'begin' in da.columns else 'tradedate'
    _cb = 'begin' if 'begin' in db.columns else 'tradedate'
    m = pd.merge(
        da[[_ca, 'close']].rename(columns={_ca: 'dt'}),
        db[[_cb, 'close']].rename(columns={_cb: 'dt'}),
        on='dt', suffixes=('_a', '_b')
    )
    m['close_a'] = m['close_a'].apply(lambda x: float(x) if not isinstance(x, bytes) else 0.0)
    m['close_b'] = m['close_b'].apply(lambda x: float(x) if not isinstance(x, bytes) else 0.0)
    m = m[(m['close_a'] > 0) & (m['close_b'] > 0)].reset_index(drop=True)
    if len(m) < 50:
        return None
    return m.sort_values('dt').reset_index(drop=True)


def kalman_beta(y, x, delta):
    n = len(y)
    beta = np.zeros(n)
    P = np.zeros(n)
    beta[0] = 1.0
    P[0] = 1.0
    Q = delta
    R = 1e-3
    for t in range(1, n):
        bp = beta[t-1]
        Pp = P[t-1] + Q
        H = x[t]
        S = H * Pp * H + R
        K = Pp * H / S
        beta[t] = bp + K * (y[t] - H * bp)
        P[t] = (1 - K * H) * Pp
    return beta


def simulate(m, entry_z, delta, use_kalman, window=WINDOW, exit_z=EXIT_Z,
             time_exit=TIME_EXIT_D1, warmup=50):
    df = m.copy()
    la = np.log(df['close_a'].values)
    lb = np.log(df['close_b'].values)
    if use_kalman:
        beta = kalman_beta(la, lb, delta)
        df['spread'] = la - beta * lb
    else:
        beta_ols = np.sum(la * lb) / np.sum(lb * lb)
        df['spread'] = la - beta_ols * lb
    df['mean'] = df['spread'].rolling(window).mean()
    df['std'] = df['spread'].rolling(window).std()
    df['z'] = (df['spread'] - df['mean']) / df['std']
    pos = 0
    ep = 0
    ei = 0
    gross = []
    for i in range(max(window, warmup), len(df)):
        z = df['z'].iloc[i]
        if pd.isna(z):
            continue
        if pos == 0:
            if z >= entry_z:
                pos = -1
                ep = df['spread'].iloc[i]
                ei = i
            elif z <= -entry_z:
                pos = 1
                ep = df['spread'].iloc[i]
                ei = i
        else:
            if (i - ei) >= time_exit or abs(z) <= exit_z:
                gross.append((df['spread'].iloc[i] - ep) * pos)
                pos = 0
    net = [g - COST for g in gross]
    return gross, net


def stats(t):
    if not t:
        return {'n': 0, 'pnl': 0, 'wr': 0, 'sharpe': 0}
    t = np.array(t)
    std = t.std()
    return {
        'n': len(t),
        'pnl': float(t.sum()),
        'wr': float((t > 0).mean()),
        'sharpe': float(t.mean() / std * np.sqrt(252)) if std > 0 else 0.0,
    }


def main():
    print(f"TF={TF}, COST={COST:.6f}, N_FOLDS={N_FOLDS}, TIME_EXIT={TIME_EXIT_D1}")
    rows = []
    for a, b in PAIRS:
        pair_name = f'{a}-{b}_{TF}'
        m = load_pair(a, b, TF)
        if m is None:
            print(f"  [skip] {pair_name}: no data")
            continue
        n = len(m)
        fs = max(n // N_FOLDS, 100)
        print(f"\n== {pair_name} (rows={n}, fold_size={fs})")
        la = np.log(m['close_a'])
        lb = np.log(m['close_b'])
        beta_ols = np.sum(la * lb) / np.sum(lb * lb)
        sp = (la - beta_ols * lb).abs()
        print(f"  |spread_ols| mean={sp.mean():.5f} median={sp.median():.5f} p90={sp.quantile(0.9):.5f}  (cost={COST})")
        for use_k in [False, True]:
            label = "Kalman" if use_k else "OLS   "
            for ez in ENTRY_Z_GRID:
                fold_results = []
                for f in range(N_FOLDS):
                    s = f * fs
                    e = (f + 1) * fs if f < N_FOLDS - 1 else n
                    sub = m.iloc[s:e].reset_index(drop=True)
                    if len(sub) < WINDOW + 20:
                        continue
                    g, net = simulate(sub, ez, 1e-4, use_k)
                    fold_results.append(stats(net))
                if not fold_results:
                    continue
                tn = sum(r['n'] for r in fold_results)
                npnl = sum(r['pnl'] for r in fold_results)
                nz = [r for r in fold_results if r['n'] > 0]
                awr = float(np.mean([r['wr'] for r in nz])) if nz else 0.0
                ash = float(np.mean([r['sharpe'] for r in nz])) if nz else 0.0
                print(f"  {label} ez={ez:.2f}: n={tn:4d} NET={npnl:9.4f} wr={awr:.3f} net_sharpe={ash:7.3f}")
                rows.append({'pair': pair_name, 'method': label.strip(), 'entry_z': ez,
                             'n': tn, 'net_pnl': npnl, 'wr': awr, 'net_sharpe': ash})
    out = Path('/root/finlab/logs') / f'd1_test_{pd.Timestamp.now().date()}.csv'
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"\nOK CSV: {out}")
    if rows:
        df = pd.DataFrame(rows)
        print("\n=== ЛУЧШИЙ (method, entry_z) ПО ПАРЕ (net_pnl>0) ===")
        for pair in df['pair'].unique():
            sub = df[(df['pair'] == pair) & (df['net_pnl'] > 0)]
            if sub.empty:
                print(f"  {pair:20s}: NO POSITIVE")
                continue
            best = sub.loc[sub['net_sharpe'].idxmax()]
            print(f"  {pair:20s}: {best['method']} entry_z={best['entry_z']:.2f} net_pnl={best['net_pnl']:9.4f} net_sharpe={best['net_sharpe']:7.3f} n={int(best['n'])}")


if __name__ == '__main__':
    main()
