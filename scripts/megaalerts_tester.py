"""
MegaAlerts — правильный тест.

reference — это метаданные алерта (z-score / percentile), НЕ forward return.
Поэтому fwd_ret считаем САМИ: мержим события с D1-свечами.

Горизонты: 1 / 5 / 10 дней (дневной горизонт; минутный не покрывает комиссию 0.28%).

Метрики: n, mean, WR, base_mean, base_WR, gross_edge, net_edge,
         sharpe_per_trade, t_stat, PF, max_dd.
Комиссия: 0.28% (0.14% x 2).

Walk-forward: 2 фолда по 10 дней теста, gap 10 (независимая проверка).
"""
import pandas as pd, numpy as np, glob, os, json

COMMISSION = 0.0014
HORIZONS = [1, 5, 10]

# ---------- merge ----------

def load_events():
    files = sorted(glob.glob('data/mega_alerts/*.parquet'))
    frames = []
    for f in files:
        df = pd.read_parquet(f)
        df['ticker'] = os.path.basename(f).replace('_alerts.parquet', '')
        frames.append(df)
    all_df = pd.concat(frames, ignore_index=True)

    # чистим дубли
    key_cols = ['ticker', 'tradedate', 'tradetime', 'alert_type', 'threshold', 'value']
    all_df = all_df.drop_duplicates(subset=key_cols)
    all_df['tradedate'] = pd.to_datetime(all_df['tradedate']).dt.normalize()
    return all_df

def load_candles_d1():
    frames = []
    for f in glob.glob('data/candles/*_D1.parquet'):
        c = pd.read_parquet(f)
        c['ticker'] = os.path.basename(f).replace('_D1.parquet', '')
        c = c[['ticker', 'begin', 'close']].copy()
        c['tradedate'] = pd.to_datetime(c['begin']).dt.normalize()
        frames.append(c[['ticker', 'tradedate', 'close']])
    return pd.concat(frames, ignore_index=True)

# ---------- метрики ----------

def max_dd(r):
    if len(r) == 0:
        return np.nan
    eq = np.cumsum(r)
    peak = np.maximum.accumulate(eq)
    return float((eq - peak).min())

def metrics(r, base_mean, base_wr):
    r = np.asarray(r, dtype=float)
    n = r.size
    if n == 0:
        return dict(n=0, mean=np.nan, wr=np.nan, base_mean=base_mean, base_wr=base_wr,
                    gross_edge=np.nan, net_edge=np.nan, sharpe=np.nan, t_stat=np.nan,
                    pf=np.nan, max_dd=np.nan)
    mean = float(np.mean(r)); std = float(np.std(r, ddof=1)) if n > 1 else np.nan
    wr = float((r > 0).mean())
    win = r[r > 0]; loss = r[r < 0]
    pf = float(win.sum() / abs(loss.sum())) if loss.size > 0 else np.nan
    sharpe = mean / std if std and std > 0 else np.nan
    tstat = mean / (std / np.sqrt(n)) if std and std > 0 else np.nan
    ge = mean - base_mean
    ne = ge - 2 * COMMISSION
    return dict(n=n, mean=mean, wr=wr, base_mean=base_mean, base_wr=base_wr,
                gross_edge=ge, net_edge=ne, sharpe=sharpe, t_stat=tstat,
                pf=pf, max_dd=max_dd(r))

# ---------- fwd_ret ----------

def add_fwd_ret(df, horizon):
    d = df.sort_values(['ticker', 'tradedate']).copy()
    d['fwd_ret'] = (d.groupby('ticker')['close'].shift(-horizon) / d['close'] - 1.0)
    return d

# ---------- walk-forward ----------

def purged_wf(events, candles, alert_types, horizon, n_folds=2, fold_size=10):
    merged = events.merge(candles, on=['ticker', 'tradedate'], how='inner')
    merged = add_fwd_ret(merged, horizon).dropna(subset=['fwd_ret'])
    days = np.array(sorted(merged['tradedate'].unique()))
    print(f"  merge: {len(merged)} events, {merged['ticker'].nunique()} tickers, {len(days)} days")

    results = []
    for k in range(n_folds):
        tr_lo = k * fold_size; tr_hi = tr_lo + fold_size
        gap_hi = tr_hi + horizon
        te_lo = gap_hi; te_hi = te_lo + fold_size
        if te_hi > len(days):
            print(f"  fold {k+1}: пропуск (нужно {te_hi} дней, есть {len(days)})")
            continue
        test_days = days[te_lo:te_hi]
        dte = merged[merged['tradedate'].isin(test_days)]
        base_mean = float(dte['fwd_ret'].mean()) if len(dte) else np.nan
        base_wr = float((dte['fwd_ret'] > 0).mean()) if len(dte) else np.nan

        for at in alert_types:
            r = dte.loc[dte['alert_type'] == at, 'fwd_ret'].to_numpy()
            m = metrics(r, base_mean, base_wr)
            m['alert_type'] = at; m['fold'] = k + 1
            m['horizon'] = horizon
            m['test_range'] = f"{str(pd.Timestamp(test_days[0]).date())}..{str(pd.Timestamp(test_days[-1]).date())}"
            results.append(m)
    return results

# ---------- main ----------

if __name__ == '__main__':
    print("=== MegaAlerts: правильный тест ===\n")
    events = load_events()
    candles = load_candles_d1()
    print(f"events: {len(events)} | tickers: {events['ticker'].nunique()}")
    print(f"candles D1: {len(candles)} | tickers: {candles['ticker'].nunique()}\n")

    merged0 = events.merge(candles, on=['ticker', 'tradedate'], how='inner')
    print(f"merge events + candles: {len(merged0)} (из {len(events)} events)\n")

    # топ-10 типов алертов
    top_types = events['alert_type'].value_counts().head(10).index.tolist()
    print("Топ-10 alert_type:", top_types, "\n")

    for H in HORIZONS:
        print(f"########## HORIZON = {H} дней ##########")
        merged = add_fwd_ret(merged0.copy(), H).dropna(subset=['fwd_ret'])
        base_mean = float(merged['fwd_ret'].mean())
        base_wr = float((merged['fwd_ret'] > 0).mean())
        print(f"base: mean={base_mean:.4%}, WR={base_wr:.3%}\n")

        for at in top_types:
            sub = merged[merged['alert_type'] == at]
            m = metrics(sub['fwd_ret'].to_numpy(), base_mean, base_wr)
            print(f"  {at:32s}  n={m['n']:4d}  mean={m['mean']:>7.3%}  "
                  f"WR={m['wr']:>6.2%}  net_edge={m['net_edge']:>7.3%}  "
                  f"sharpe={m['sharpe']:>6.3f}  t={m['t_stat']:>6.2f}  dd={m['max_dd']:>7.2%}")
        print()

    print("########## PURGED WALK-FORWARD (H=10, 2 folds x 10d, gap 10) ##########")
    wf = purged_wf(events, candles, top_types, horizon=10, n_folds=2, fold_size=10)
    print("\n--- walk-forward results ---")
    for r in wf:
        if r['n'] == 0:
            continue
        print(f"  fold {r['fold']} | {r['alert_type']:32s} | n={r['n']:4d} | "
              f"net_edge={r['net_edge']:>7.3%} | sharpe={r['sharpe']:>6.3f} | {r['test_range']}")
