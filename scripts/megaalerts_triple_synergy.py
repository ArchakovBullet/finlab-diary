"""
MegaAlerts + FutOI + TradeStats — тройная синергия.

Гипотезы:
  1. MegaAlerts + FutOI (позиционирование)
  2. MegaAlerts + TradeStats (микроструктура/дисбаланс)
  3. Все три вместе

Только фьючерсы (пересечение тикеров).
"""
import pandas as pd, numpy as np, glob, os

# --- 1. MegaAlerts ---
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
events = events[events['tradedate'] >= '2026-07-01'].copy()
print(f"MegaAlerts: {len(events)} событий, {events['ticker'].nunique()} тикеров")

# --- 2. D1 свечи (forward return) ---
frames = []
for f in glob.glob('data/candles/*_D1.parquet'):
    c = pd.read_parquet(f)
    c['ticker'] = os.path.basename(f).replace('_D1.parquet', '')
    c['tradedate'] = pd.to_datetime(c['begin']).dt.normalize()
    frames.append(c[['ticker','tradedate','close']])
candles = pd.concat(frames, ignore_index=True).sort_values(['ticker','tradedate']).reset_index(drop=True)
for h in (1, 3, 5):
    candles[f'fwd_{h}d'] = candles.groupby('ticker')['close'].shift(-h) / candles['close'] - 1.0

# --- 3. FutOI (1h) ---
futoi = pd.read_parquet('data/futoi_1h/futoi_1h.parquet')
print(f"FutOI: {len(futoi)} строк, {futoi['ticker'].nunique()} тикеров")
print(f"FutOI cols: {list(futoi.columns)}")

# колонка 'hour' — datetime? нормализуем к tradedate
if 'hour' in futoi.columns:
    futoi['tradedate'] = pd.to_datetime(futoi['hour']).dt.normalize()
    # агрегируем по дню: последнее значение за день
    futoi_daily = futoi.groupby(['ticker','tradedate']).agg({
        'fiz_long': 'last', 'fiz_short': 'last',
        'yur_long': 'last', 'yur_short': 'last',
    }).reset_index()
    futoi_daily['fiz_net'] = futoi_daily['fiz_long'] - futoi_daily['fiz_short']
    futoi_daily['yur_net'] = futoi_daily['yur_long'] - futoi_daily['yur_short']
    print(f"FutOI daily: {len(futoi_daily)} строк")

# --- 4. TradeStats (5min) ---
frames = []
for f in glob.glob('data/tradestats/*.parquet'):
    df = pd.read_parquet(f)
    df['ticker'] = os.path.basename(f).replace('_tradestats.parquet', '')
    df['tradedate'] = pd.to_datetime(df['tradedate']).dt.normalize()
    frames.append(df[['ticker','tradedate','tradetime','disb','vol']])
ts = pd.concat(frames, ignore_index=True)
# агрегируем по дню: сумма disb, сумма vol
ts_daily = ts.groupby(['ticker','tradedate']).agg({
    'disb': 'sum', 'vol': 'sum',
}).reset_index()
print(f"TradeStats daily: {len(ts_daily)} строк, {ts_daily['ticker'].nunique()} тикеров")

# --- 5. Общее пересечение тикеров ---
ticks_events = set(events['ticker'].unique())
ticks_futoi = set(futoi_daily['ticker'].unique())
ticks_ts = set(ts_daily['ticker'].unique())
common = ticks_events & ticks_futoi & ticks_ts
print(f"\nПересечение тикеров (MegaAlerts ∩ FutOI ∩ TradeStats): {len(common)}")
print(f"  {sorted(common)[:20]}...")

# --- 6. Merge ---
events_f = events[events['ticker'].isin(common)]
merged = events_f.merge(candles, on=['ticker','tradedate'], how='inner')
merged = merged.merge(futoi_daily[['ticker','tradedate','fiz_net','yur_net']],
                      on=['ticker','tradedate'], how='left')
merged = merged.merge(ts_daily[['ticker','tradedate','disb','vol']],
                      on=['ticker','tradedate'], how='left')
print(f"После merge: {len(merged)} событий")

# --- 7. Синергия ---
print("\n=== 1. MegaAlerts + FutOI ===")
for at in ['oi_low_min','vol_b_99_9_pctl','pr_high_max','net_vol_99_9_pctl-','pr_change_99_9_pctl-']:
    sub = merged[merged['alert_type'] == at].dropna(subset=['fiz_net','fwd_5d'])
    if len(sub) < 10:
        print(f"  {at:32s} | мало данных (n={len(sub)})")
        continue
    # fiz_net > 0 — физлица лонгуют; fiz_net < 0 — шортят
    fiz_long = sub[sub['fiz_net'] > 0]
    fiz_short = sub[sub['fiz_net'] < 0]
    print(f"  {at:32s}")
    if len(fiz_long) >= 3:
        print(f"    физлица ЛОНГ  (n={len(fiz_long):3d}) fwd_5d={fiz_long['fwd_5d'].mean():+.3%}")
    if len(fiz_short) >= 3:
        print(f"    физлица ШОРТ  (n={len(fiz_short):3d}) fwd_5d={fiz_short['fwd_5d'].mean():+.3%}")

print("\n=== 2. MegaAlerts + TradeStats (disb) ===")
for at in ['oi_low_min','vol_b_99_9_pctl','pr_high_max','net_vol_99_9_pctl-','pr_change_99_9_pctl-']:
    sub = merged[merged['alert_type'] == at].dropna(subset=['disb','fwd_5d'])
    if len(sub) < 10:
        print(f"  {at:32s} | мало данных (n={len(sub)})")
        continue
    disb_pos = sub[sub['disb'] > 0]
    disb_neg = sub[sub['disb'] < 0]
    print(f"  {at:32s}")
    if len(disb_pos) >= 3:
        print(f"    disb > 0 (n={len(disb_pos):3d}) fwd_5d={disb_pos['fwd_5d'].mean():+.3%}")
    if len(disb_neg) >= 3:
        print(f"    disb < 0 (n={len(disb_neg):3d}) fwd_5d={disb_neg['fwd_5d'].mean():+.3%}")

print("\n=== 3. Все три вместе ===")
for at in ['oi_low_min','vol_b_99_9_pctl','pr_high_max','net_vol_99_9_pctl-']:
    sub = merged[merged['alert_type'] == at].dropna(subset=['fiz_net','disb','fwd_5d'])
    if len(sub) < 5:
        print(f"  {at:32s} | мало данных (n={len(sub)})")
        continue
    # все три совпадают: для лонга fiz_net>0 и disb>0; для шорта fiz_net<0 и disb<0
    combo_long = sub[(sub['fiz_net'] > 0) & (sub['disb'] > 0)]
    combo_short = sub[(sub['fiz_net'] < 0) & (sub['disb'] < 0)]
    print(f"  {at:32s}")
    if len(combo_long) >= 2:
        print(f"    ВСЕ ЛОНГ   (n={len(combo_long):3d}) fwd_5d={combo_long['fwd_5d'].mean():+.3%}")
    if len(combo_short) >= 2:
        print(f"    ВСЕ ШОРТ   (n={len(combo_short):3d}) fwd_5d={combo_short['fwd_5d'].mean():+.3%}")

# --- 8. Baseline ---
base_mean_5d = candles['fwd_5d'].mean()
print(f"\nBaseline fwd_5d (все дни): {base_mean_5d:+.3%}")
