"""
MegaAlerts + FutOI + TradeStats — синергия на пересечении тикеров.
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

# --- 2. D1 свечи ---
frames = []
for f in glob.glob('data/candles/*_D1.parquet'):
    c = pd.read_parquet(f)
    c['ticker'] = os.path.basename(f).replace('_D1.parquet', '')
    c['tradedate'] = pd.to_datetime(c['begin']).dt.normalize()
    frames.append(c[['ticker','tradedate','close','volume']])
candles = pd.concat(frames, ignore_index=True).sort_values(['ticker','tradedate']).reset_index(drop=True)
for h in (1, 3, 5):
    candles[f'fwd_{h}d'] = candles.groupby('ticker')['close'].shift(-h) / candles['close'] - 1.0

# --- 3. FutOI daily ---
futoi = pd.read_parquet('data/futoi_1h/futoi_1h.parquet')
futoi['tradedate'] = pd.to_datetime(futoi['hour']).dt.normalize()
futoi_daily = futoi.groupby(['ticker','tradedate']).agg({
    'fiz_long': 'last', 'fiz_short': 'last',
    'yur_long': 'last', 'yur_short': 'last',
}).reset_index()
futoi_daily['fiz_net'] = futoi_daily['fiz_long'] - futoi_daily['fiz_short']
futoi_daily['yur_net'] = futoi_daily['yur_long'] - futoi_daily['yur_short']

# --- 4. TradeStats daily ---
frames = []
for f in glob.glob('data/tradestats/*.parquet'):
    df = pd.read_parquet(f)
    df['ticker'] = os.path.basename(f).replace('_tradestats.parquet','')
    df['tradedate'] = pd.to_datetime(df['tradedate']).dt.normalize()
    frames.append(df[['ticker','tradedate','disb','vol']])
ts = pd.concat(frames, ignore_index=True)
ts_daily = ts.groupby(['ticker','tradedate']).agg({'disb': 'sum', 'vol': 'sum'}).reset_index()

# --- 5. Merge ---
merged = events.merge(candles, on=['ticker','tradedate'], how='inner')
merged = merged.merge(futoi_daily[['ticker','tradedate','fiz_net','yur_net']],
                      on=['ticker','tradedate'], how='left')
merged = merged.merge(ts_daily[['ticker','tradedate','disb','vol']].rename(columns={'vol':'ts_vol'}),
                      on=['ticker','tradedate'], how='left')
print(f"После merge: {len(merged)} событий")

# --- 6. Синергия с FutOI ---
print("\n=== 1. MegaAlerts + FutOI ===")
KEY = ['vol_b_99_9_pctl','vol_s_99_9_pctl','vol_99_9_pctl','net_vol_99_9_pctl+','net_vol_99_9_pctl-',
       'pr_low_min','pr_high_max','pr_change_99_9_pctl-','pr_change_99_9_pctl+',
       'oi_close_change_99_9_pctl+','oi_close_change_99_9_pctl-']
for at in KEY:
    sub = merged[merged['alert_type'] == at].dropna(subset=['fiz_net','fwd_5d'])
    if len(sub) < 10:
        continue
    fiz_long  = sub[sub['fiz_net'] > 0]
    fiz_short = sub[sub['fiz_net'] < 0]
    row = f"  {at:32s} | n={len(sub):3d}"
    if len(fiz_long) >= 5:
        row += f" | fiz ЛОНГ (n={len(fiz_long):2d}): {fiz_long['fwd_5d'].mean():+.3%}"
    if len(fiz_short) >= 5:
        row += f" | fiz ШОРТ (n={len(fiz_short):2d}): {fiz_short['fwd_5d'].mean():+.3%}"
    print(row)

# --- 7. Синергия с TradeStats ---
print("\n=== 2. MegaAlerts + TradeStats (disb) ===")
for at in KEY:
    sub = merged[merged['alert_type'] == at].dropna(subset=['disb','fwd_5d'])
    if len(sub) < 10:
        continue
    disb_pos = sub[sub['disb'] > 0]
    disb_neg = sub[sub['disb'] < 0]
    row = f"  {at:32s} | n={len(sub):3d}"
    if len(disb_pos) >= 5:
        row += f" | disb>0 (n={len(disb_pos):2d}): {disb_pos['fwd_5d'].mean():+.3%}"
    if len(disb_neg) >= 5:
        row += f" | disb<0 (n={len(disb_neg):2d}): {disb_neg['fwd_5d'].mean():+.3%}"
    print(row)

# --- 8. Все три ---
print("\n=== 3. Все три совпадают (лонг: fiz ШОРТ + disb>0; шорт: fiz ЛОНГ + disb<0) ===")
for at in KEY:
    sub = merged[merged['alert_type'] == at].dropna(subset=['fiz_net','disb','fwd_5d'])
    if len(sub) < 5:
        continue
    combo_long  = sub[(sub['fiz_net'] < 0) & (sub['disb'] > 0)]
    combo_short = sub[(sub['fiz_net'] > 0) & (sub['disb'] < 0)]
    row = f"  {at:32s} | n={len(sub):3d}"
    if len(combo_long) >= 3:
        row += f" | ВСЕ ЛОНГ (n={len(combo_long):2d}): {combo_long['fwd_5d'].mean():+.3%}"
    if len(combo_short) >= 3:
        row += f" | ВСЕ ШОРТ (n={len(combo_short):2d}): {combo_short['fwd_5d'].mean():+.3%}"
    print(row)

# --- 9. Baseline ---
base = candles['fwd_5d'].mean()
print(f"\nBaseline fwd_5d (все дни): {base:+.3%}")

# --- 10. Композитный сигнал ---
print("\n=== 4. Композитный сигнал MegaAlerts + FutOI ===")
LONG_MA = ['oi_low_min','net_vol_99_9_pctl+','vol_b_99_9_pctl']
SHORT_MA = ['pr_change_99_9_pctl-','net_vol_99_9_pctl-','pr_high_max']

sub_long = merged[merged['alert_type'].isin(LONG_MA)].dropna(subset=['fiz_net'])
sub_short = merged[merged['alert_type'].isin(SHORT_MA)].dropna(subset=['fiz_net'])

# лонг при подтверждении: fiz_net < 0 (физлица в шорте)
long_ok = sub_long[sub_long['fiz_net'] < 0]
long_not = sub_long[sub_long['fiz_net'] >= 0]
print(f"лонг-композит:")
print(f"  подтверждён FutOI (n={len(long_ok):3d}): {long_ok['fwd_5d'].mean():+.3%}")
print(f"  не подтверждён    (n={len(long_not):3d}): {long_not['fwd_5d'].mean():+.3%}")

# шорт при подтверждении: fiz_net > 0 (физлица в лонге)
short_ok = sub_short[sub_short['fiz_net'] > 0]
short_not = sub_short[sub_short['fiz_net'] <= 0]
print(f"шорт-композит:")
print(f"  подтверждён FutOI (n={len(short_ok):3d}): {short_ok['fwd_5d'].mean():+.3%}")
print(f"  не подтверждён    (n={len(short_not):3d}): {short_not['fwd_5d'].mean():+.3%}")
