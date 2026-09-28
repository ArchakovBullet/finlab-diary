"""
Валидация результата MegaAlerts + FutOI:
  - распределение fwd_ret (median, quantiles, max)
  - распределение по тикерам
  - распределение по датам
  - проверка look-ahead: сдвиг fiz_net на -1 день
"""
import pandas as pd, numpy as np, glob, os

# --- MegaAlerts ---
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

# --- D1 ---
frames = []
for f in glob.glob('data/candles/*_D1.parquet'):
    c = pd.read_parquet(f)
    c['ticker'] = os.path.basename(f).replace('_D1.parquet', '')
    c['tradedate'] = pd.to_datetime(c['begin']).dt.normalize()
    frames.append(c[['ticker','tradedate','close']])
candles = pd.concat(frames, ignore_index=True).sort_values(['ticker','tradedate']).reset_index(drop=True)
for h in (1, 3, 5):
    candles[f'fwd_{h}d'] = candles.groupby('ticker')['close'].shift(-h) / candles['close'] - 1.0

# --- FutOI ---
futoi = pd.read_parquet('data/futoi_1h/futoi_1h.parquet')
futoi['tradedate'] = pd.to_datetime(futoi['hour']).dt.normalize()
futoi_daily = futoi.groupby(['ticker','tradedate']).agg({
    'fiz_long': 'last', 'fiz_short': 'last',
}).reset_index()
futoi_daily['fiz_net'] = futoi_daily['fiz_long'] - futoi_daily['fiz_short']

# --- Merge ---
merged = events.merge(candles, on=['ticker','tradedate'], how='inner')
merged = merged.merge(futoi_daily[['ticker','tradedate','fiz_net']],
                      on=['ticker','tradedate'], how='left')

# --- Композит ---
LONG_MA  = ['oi_low_min','net_vol_99_9_pctl+','vol_b_99_9_pctl']
SHORT_MA = ['pr_change_99_9_pctl-','net_vol_99_9_pctl-','pr_high_max']

sub_long  = merged[merged['alert_type'].isin(LONG_MA)].dropna(subset=['fiz_net','fwd_5d'])
sub_short = merged[merged['alert_type'].isin(SHORT_MA)].dropna(subset=['fiz_net','fwd_5d'])

long_ok  = sub_long[sub_long['fiz_net'] < 0]    # физлица в шорте
short_ok = sub_short[sub_short['fiz_net'] > 0]  # физлица в лонге

print("=== ЛОНГ-композит подтверждён (n={}) ===".format(len(long_ok)))
if len(long_ok) > 0:
    r = long_ok['fwd_5d']
    print(f"  mean={r.mean():+.3%} | median={r.median():+.3%} | std={r.std():.3%}")
    print(f"  p10={r.quantile(0.1):+.3%} | p25={r.quantile(0.25):+.3%} | "
          f"p75={r.quantile(0.75):+.3%} | p90={r.quantile(0.9):+.3%}")
    print(f"  min={r.min():+.3%} | max={r.max():+.3%}")
    print(f"  WR>0: {(r>0).mean():.1%}")
    print(f"  топ-5 по тикерам:")
    print(long_ok.groupby('ticker')['fwd_5d'].agg(['count','mean']).sort_values('mean',ascending=False).head(5).to_string())
    print(f"  топ-5 по датам:")
    print(long_ok.groupby('tradedate')['fwd_5d'].agg(['count','mean']).sort_values('mean',ascending=False).head(5).to_string())

print("\n=== ШОРТ-композит подтверждён (n={}) ===".format(len(short_ok)))
if len(short_ok) > 0:
    r = short_ok['fwd_5d']
    print(f"  mean={r.mean():+.3%} | median={r.median():+.3%} | std={r.std():.3%}")
    print(f"  p10={r.quantile(0.1):+.3%} | p25={r.quantile(0.25):+.3%} | "
          f"p75={r.quantile(0.75):+.3%} | p90={r.quantile(0.9):+.3%}")
    print(f"  min={r.min():+.3%} | max={r.max():+.3%}")
    print(f"  WR>0: {(r>0).mean():.1%}")
    print(f"  топ-5 по тикерам:")
    print(short_ok.groupby('ticker')['fwd_5d'].agg(['count','mean']).sort_values('mean',ascending=False).head(5).to_string())
    print(f"  топ-5 по датам:")
    print(short_ok.groupby('tradedate')['fwd_5d'].agg(['count','mean']).sort_values('mean',ascending=False).head(5).to_string())

# --- Проверка look-ahead: сдвиг fiz_net ---
print("\n=== Look-ahead check: fiz_net сдвиг на -1 день ===")
futoi_shifted = futoi_daily.copy()
futoi_shifted['tradedate'] = futoi_shifted['tradedate'] + pd.Timedelta(days=1)
merged_shifted = events.merge(candles, on=['ticker','tradedate'], how='inner')
merged_shifted = merged_shifted.merge(
    futoi_shifted[['ticker','tradedate','fiz_net']],
    on=['ticker','tradedate'], how='left')

sub_long_s  = merged_shifted[merged_shifted['alert_type'].isin(LONG_MA)].dropna(subset=['fiz_net','fwd_5d'])
sub_short_s = merged_shifted[merged_shifted['alert_type'].isin(SHORT_MA)].dropna(subset=['fiz_net','fwd_5d'])

long_ok_s  = sub_long_s[sub_long_s['fiz_net'] < 0]
short_ok_s = sub_short_s[sub_short_s['fiz_net'] > 0]
print(f"  лонг подтверждён (n={len(long_ok_s)}): {long_ok_s['fwd_5d'].mean() if len(long_ok_s) else float('nan'):+.3%}")
print(f"  шорт подтверждён (n={len(short_ok_s)}): {short_ok_s['fwd_5d'].mean() if len(short_ok_s) else float('nan'):+.3%}")

# --- Уникальные события ---
print("\n=== Проверка дублей ===")
long_unique = long_ok.drop_duplicates(subset=['ticker','tradedate'])
short_unique = short_ok.drop_duplicates(subset=['ticker','tradedate'])
print(f"  лонг: {len(long_ok)} событий, {len(long_unique)} уникальных (ticker,tradedate)")
print(f"  шорт: {len(short_ok)} событий, {len(short_unique)} уникальных")
