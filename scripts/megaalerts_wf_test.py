"""
MegaAlerts: walk-forward + проверка на выбросы + композитный сигнал.
"""
import pandas as pd, numpy as np, glob, os

# --- события ---
files = sorted(glob.glob('data/mega_alerts/*.parquet'))
frames = []
for f in files:
    df = pd.read_parquet(f)
    df['ticker'] = os.path.basename(f).replace('_alerts.parquet', '')
    frames.append(df)
events = pd.concat(frames, ignore_index=True)
key_cols = ['ticker','tradedate','tradetime','alert_type','threshold','value']
events = events.drop_duplicates(subset=key_cols)
events['tradedate'] = pd.to_datetime(events['tradedate']).dt.normalize()
events = events[events['tradedate'] >= '2026-08-01'].copy()

# --- D1 свечи ---
frames = []
for f in glob.glob('data/candles/*_D1.parquet'):
    c = pd.read_parquet(f)
    c['ticker'] = os.path.basename(f).replace('_D1.parquet', '')
    c['tradedate'] = pd.to_datetime(c['begin']).dt.normalize()
    frames.append(c[['ticker','tradedate','close']])
candles = pd.concat(frames, ignore_index=True).sort_values(['ticker','tradedate']).reset_index(drop=True)

for h in (1, 3, 5, 10):
    candles[f'fwd_{h}d'] = candles.groupby('ticker')['close'].shift(-h) / candles['close'] - 1.0

merged = events.merge(candles, on=['ticker','tradedate'], how='inner')

# --- 1. распределение: mean vs median для ключевых алертов ---
print("=== mean vs median (проверка на выбросы) ===")
for at in ['pr_high_max','pr_change_99_9_pctl-','oi_low_min','net_vol_99_9_pctl+','vol_b_99_9_pctl']:
    sub = merged[merged['alert_type'] == at]
    for h in (1, 5):
        r = sub[f'fwd_{h}d'].dropna()
        if len(r) == 0: continue
        print(f"  {at:32s} | {h}d | n={len(r):4d} | mean={r.mean():+.3%} | median={r.median():+.3%} | "
              f"p10={r.quantile(0.1):+.3%} | p90={r.quantile(0.9):+.3%} | std={r.std():.3%}")

# --- 2. walk-forward на дневном горизонте ---
print("\n=== walk-forward (H=5д, 2 фолда по 10 дней теста, gap 10) ===")
days = np.array(sorted(merged['tradedate'].unique()))
print(f"уникальных дней: {len(days)}, диапазон: {days[0]} .. {days[-1]}")

for k in range(2):
    tr_lo = k * 10; tr_hi = tr_lo + 10
    gap_hi = tr_hi + 5
    te_lo = gap_hi; te_hi = te_lo + 10
    if te_hi > len(days):
        print(f"  fold {k+1}: пропуск (нужно {te_hi} дней, есть {len(days)})")
        continue
    test_days = days[te_lo:te_hi]
    dte = merged[merged['tradedate'].isin(test_days)]
    base_mean = dte['fwd_5d'].mean() if len(dte) else np.nan
    print(f"\n  fold {k+1}: test {test_days[0]} .. {test_days[-1]} | base_mean={base_mean:+.3%}")
    for at in ['oi_low_min','net_vol_99_9_pctl+','vol_b_99_9_pctl',
               'pr_change_99_9_pctl-','pr_high_max','net_vol_99_9_pctl-']:
        sub = dte[dte['alert_type'] == at]
        r = sub['fwd_5d'].dropna()
        if len(r) < 5:
            print(f"    {at:32s} | n={len(r):3d} | мало данных")
            continue
        net = r.mean() - base_mean - 0.0028
        print(f"    {at:32s} | n={len(r):3d} | mean={r.mean():+.3%} | "
              f"excess={r.mean()-base_mean:+.3%} | net={net:+.3%} | WR={(r>0).mean():.1%}")

# --- 3. композитный сигнал ---
print("\n=== композитный сигнал ===")
LONG_TYPES  = ['oi_low_min','net_vol_99_9_pctl+','vol_b_99_9_pctl']
SHORT_TYPES = ['pr_change_99_9_pctl-','net_vol_99_9_pctl-','pr_high_max']

long_events  = merged[merged['alert_type'].isin(LONG_TYPES)]
short_events = merged[merged['alert_type'].isin(SHORT_TYPES)]

print(f"\nлонг-композит: n={len(long_events)}")
print(f"  fwd_1d: mean={long_events['fwd_1d'].mean():+.3%}")
print(f"  fwd_3d: mean={long_events['fwd_3d'].mean():+.3%}")
print(f"  fwd_5d: mean={long_events['fwd_5d'].mean():+.3%}")

print(f"\nшорт-композит: n={len(short_events)}")
print(f"  fwd_1d: mean={short_events['fwd_1d'].mean():+.3%}")
print(f"  fwd_3d: mean={short_events['fwd_3d'].mean():+.3%}")
print(f"  fwd_5d: mean={short_events['fwd_5d'].mean():+.3%}")
