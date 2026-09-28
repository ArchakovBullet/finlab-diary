"""
TradeStats: проверка дополнительных метрик с учётом того,
что oi_* есть не во всех файлах.
"""
import pandas as pd, numpy as np, glob, os

frames = []
for f in glob.glob('data/tradestats/*.parquet'):
    df = pd.read_parquet(f)
    df['ticker'] = os.path.basename(f).replace('_tradestats.parquet','')
    df['tradedate'] = pd.to_datetime(df['tradedate']).dt.normalize()

    # какие колонки есть
    have = set(df.columns)
    keep = ['ticker','tradedate']
    # обязательные
    for c in ['disb','trades_b','trades_s','val_b','val_s']:
        if c in have:
            keep.append(c)
    # опциональные (oi)
    for c in ['oi_open','oi_close']:
        if c in have:
            keep.append(c)

    frames.append(df[keep].copy())

ts = pd.concat(frames, ignore_index=True)
print(f"TradeStats all: {len(ts)} строк, колонки: {list(ts.columns)}")

# агрегация
agg = {
    'disb': 'sum', 'trades_b': 'sum', 'trades_s': 'sum',
    'val_b': 'sum', 'val_s': 'sum',
}
if 'oi_open' in ts.columns:
    agg['oi_open'] = 'first'
if 'oi_close' in ts.columns:
    agg['oi_close'] = 'last'

ts_daily = ts.groupby(['ticker','tradedate']).agg(agg).reset_index()

# производные
if 'trades_b' in ts_daily.columns and 'trades_s' in ts_daily.columns:
    ts_daily['trades_net'] = ts_daily['trades_b'] - ts_daily['trades_s']
if 'val_b' in ts_daily.columns and 'val_s' in ts_daily.columns:
    ts_daily['val_net'] = ts_daily['val_b'] - ts_daily['val_s']
if 'oi_open' in ts_daily.columns and 'oi_close' in ts_daily.columns:
    ts_daily['oi_delta'] = ts_daily['oi_close'] - ts_daily['oi_open']

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

merged = ts_daily.merge(candles, on=['ticker','tradedate'], how='inner').dropna(subset=['fwd_5d'])
print(f"TradeStats + candles: {len(merged)} строк")

FEATURES = [f for f in ['oi_delta','trades_net','val_net','disb'] if f in merged.columns]
print(f"Тестируем метрики: {FEATURES}")

for feat in FEATURES:
    print(f"\n=== {feat} ===")
    for h in (1, 5):
        top = merged[merged[feat] > merged[feat].quantile(0.8)]
        bot = merged[merged[feat] < merged[feat].quantile(0.2)]
        base = merged[f'fwd_{h}d'].mean()
        print(f"  H={h}d | top(n={len(top):3d}): {top[f'fwd_{h}d'].mean():+.3%} | "
              f"bot(n={len(bot):3d}): {bot[f'fwd_{h}d'].mean():+.3%} | base: {base:+.3%}")
