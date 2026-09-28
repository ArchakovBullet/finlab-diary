"""
FutOI: проверка дополнительных метрик (buy_ratio, ratio_delta).
"""
import pandas as pd, numpy as np, glob, os

futoi = pd.read_parquet('data/futoi_1h/futoi_1h.parquet')
futoi['tradedate'] = pd.to_datetime(futoi['hour']).dt.normalize()

have = set(futoi.columns)
print(f"FutOI колонки: {sorted(have)}")

# собираем только то, что есть
agg = {}
for c in ['fiz_long','fiz_short','yur_long','yur_short','fiz_buy_ratio','yur_buy_ratio',
          'fiz_ratio_delta','yur_ratio_delta','fiz_total','yur_total']:
    if c in have:
        agg[c] = 'last'

futoi_daily = futoi.groupby(['ticker','tradedate']).agg(agg).reset_index()

# производные
if 'fiz_long' in futoi_daily.columns and 'fiz_short' in futoi_daily.columns:
    futoi_daily['fiz_net'] = futoi_daily['fiz_long'] - futoi_daily['fiz_short']
if 'yur_long' in futoi_daily.columns and 'yur_short' in futoi_daily.columns:
    futoi_daily['yur_net'] = futoi_daily['yur_long'] - futoi_daily['yur_short']

# D1
frames = []
for f in glob.glob('data/candles/*_D1.parquet'):
    c = pd.read_parquet(f)
    c['ticker'] = os.path.basename(f).replace('_D1.parquet','')
    c['tradedate'] = pd.to_datetime(c['begin']).dt.normalize()
    frames.append(c[['ticker','tradedate','close']])
candles = pd.concat(frames, ignore_index=True).sort_values(['ticker','tradedate']).reset_index(drop=True)
for h in (1, 5):
    candles[f'fwd_{h}d'] = candles.groupby('ticker')['close'].shift(-h) / candles['close'] - 1.0

merged = futoi_daily.merge(candles, on=['ticker','tradedate'], how='inner').dropna(subset=['fwd_5d'])
print(f"FutOI + candles: {len(merged)} строк")

FEATURES = [f for f in ['fiz_buy_ratio','yur_buy_ratio','fiz_ratio_delta','yur_ratio_delta',
                        'fiz_net','yur_net'] if f in merged.columns]
print(f"Тестируем метрики: {FEATURES}")

for feat in FEATURES:
    print(f"\n=== {feat} ===")
    for h in (1, 5):
        top = merged[merged[feat] > merged[feat].quantile(0.8)]
        bot = merged[merged[feat] < merged[feat].quantile(0.2)]
        base = merged[f'fwd_{h}d'].mean()
        print(f"  H={h}d | top(n={len(top):3d}): {top[f'fwd_{h}d'].mean():+.3%} | "
              f"bot(n={len(bot):3d}): {bot[f'fwd_{h}d'].mean():+.3%} | base: {base:+.3%}")
