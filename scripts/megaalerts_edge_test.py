"""
MegaAlerts — поиск edge (не «сигнал после алерта», а паттерн вокруг алерта).

Тесты:
  1. fwd_ret на 1/3/5 ДНЕЙ после алерта (дневной горизонт > 0.28% комиссии)
  2. кластеры: 2+ алерта одного типа за час -> усиление эффекта
  3. back_ret: движение ДО алерта (проверка «опаздывает?»)
"""
import pandas as pd, numpy as np, glob, os
from collections import defaultdict

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
events['dt'] = pd.to_datetime(events['tradedate'].astype(str) + ' ' + events['tradetime'].astype(str))
events = events[events['tradedate'] >= '2026-08-01'].copy()
print(f"события (08-01+): {len(events)}")

# --- D1 свечи ---
frames = []
for f in glob.glob('data/candles/*_D1.parquet'):
    c = pd.read_parquet(f)
    c['ticker'] = os.path.basename(f).replace('_D1.parquet', '')
    c['tradedate'] = pd.to_datetime(c['begin']).dt.normalize()
    c = c[['ticker','tradedate','close']].copy()
    frames.append(c)
candles = pd.concat(frames, ignore_index=True)
candles = candles.sort_values(['ticker','tradedate']).reset_index(drop=True)

for h in (1, 3, 5, 10):
    candles[f'fwd_{h}d'] = candles.groupby('ticker')['close'].shift(-h) / candles['close'] - 1.0

# --- merge событие с ближайшим днём ---
merged = events.merge(candles, on=['ticker','tradedate'], how='inner')
print(f"смержилось: {len(merged)} из {len(events)}")

print("\n=== baseline (D1, все дни) ===")
for h in (1, 3, 5, 10):
    sub = candles[f'fwd_{h}d'].dropna()
    print(f"  h={h}d | mean={sub.mean():+.4%} | std={sub.std():.4%} | n={len(sub)}")

# --- 1. fwd_ret после алерта по типам ---
print("\n=== fwd_ret после алерта (дневной горизонт) ===")
top_types = merged['alert_type'].value_counts().head(12).index.tolist()
for at in top_types:
    sub = merged[merged['alert_type'] == at]
    row = f"  {at:32s} | n={len(sub):4d}"
    for h in (1, 3, 5, 10):
        m = sub[f'fwd_{h}d'].mean()
        row += f" | {h:2d}d: {m:+.3%}" if pd.notna(m) else f" | {h:2d}d:   nan"
    print(row)

# --- 2. кластеры: 2+ алерта за час ---
print("\n=== кластеры алертов (2+ за час) ===")
events_sorted = events.sort_values(['ticker','dt']).copy()
events_sorted['prev_dt'] = events_sorted.groupby(['ticker','alert_type'])['dt'].shift(1)
events_sorted['delta_min'] = (events_sorted['dt'] - events_sorted['prev_dt']).dt.total_seconds() / 60
events_sorted['is_cluster'] = (events_sorted['delta_min'] <= 60).fillna(False)

merged_cl = events_sorted.merge(candles, on=['ticker','tradedate'], how='inner')
for at in top_types[:6]:
    sub = merged_cl[merged_cl['alert_type'] == at]
    single = sub[~sub['is_cluster']]
    cluster = sub[sub['is_cluster']]
    row = f"  {at:32s} | single n={len(single):3d} fwd_5d={single['fwd_5d'].mean():+.3%} | cluster n={len(cluster):3d} fwd_5d={cluster['fwd_5d'].mean():+.3%}"
    print(row)

# --- 3. back_ret: движение до алерта ---
print("\n=== движение ДО алерта (back_ret) ===")
candles_back = candles.copy()
for h in (1, 3, 5):
    candles_back[f'back_{h}d'] = candles_back['close'] / candles_back.groupby('ticker')['close'].shift(h) - 1.0

merged_back = events.merge(candles_back, on=['ticker','tradedate'], how='inner')
for at in top_types[:8]:
    sub = merged_back[merged_back['alert_type'] == at]
    row = f"  {at:32s} | n={len(sub):4d}"
    for h in (1, 3, 5):
        m = sub[f'back_{h}d'].mean()
        row += f" | back_{h}d: {m:+.3%}" if pd.notna(m) else f" | back_{h}d:   nan"
    print(row)
