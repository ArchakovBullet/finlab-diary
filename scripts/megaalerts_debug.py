"""
Диагностика бага в megaalerts_tester.py: fwd_ret = 0 у всех событий.
"""
import pandas as pd, numpy as np, glob, os

# 1) события
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
print("events:", len(events), "| tickers:", events['ticker'].nunique(),
      "| days:", events['tradedate'].nunique())
print("events date range:", events['tradedate'].min(), "..", events['tradedate'].max())

# 2) свечи
frames = []
for f in glob.glob('data/candles/*_D1.parquet'):
    c = pd.read_parquet(f)
    c['ticker'] = os.path.basename(f).replace('_D1.parquet', '')
    c['tradedate'] = pd.to_datetime(c['begin']).dt.normalize()
    frames.append(c[['ticker','tradedate','close']])
candles = pd.concat(frames, ignore_index=True)
print("\ncandles:", len(candles), "| tickers:", candles['ticker'].nunique(),
      "| days:", candles['tradedate'].nunique())
print("candles date range:", candles['tradedate'].min(), "..", candles['tradedate'].max())

# 3) пересечение
inter_days = set(events['tradedate']) & set(candles['tradedate'])
print("\nпересечение дней events & candles:", len(inter_days))
inter_tickers = set(events['ticker']) & set(candles['ticker'])
print("пересечение тикеров:", len(inter_tickers))

# 4) merge
merged = events.merge(candles, on=['ticker','tradedate'], how='inner')
print("\nmerged:", len(merged))
print("merged days:", merged['tradedate'].nunique(),
      "| range:", merged['tradedate'].min(), "..", merged['tradedate'].max())

# 5) смотрим ОДИН тикер с ОДНИМ событием
print("\n=== один тикер для примера ===")
one = merged[merged['ticker'] == 'SBER'].head(3)
if len(one) == 0:
    one = merged.head(3)
print("ticker:", one['ticker'].iloc[0])
print(one[['ticker','tradedate','alert_type','close']].to_string())

# 6) возьмём candles по этому тикеру за период и посмотрим, разные ли close
tk = one['ticker'].iloc[0]
c_tk = candles[candles['ticker'] == tk].sort_values('tradedate')
print(f"\n=== candles {tk}: {len(c_tk)} строк ===")
print(c_tk.head(10).to_string())
print("close uniq:", c_tk['close'].nunique(), "из", len(c_tk))

# 7) fwd_ret вручную
c_tk = c_tk.copy()
c_tk['fwd_ret_5'] = c_tk['close'].shift(-5) / c_tk['close'] - 1.0
print(f"\n=== {tk}: close.shift(-5)/close - 1 ===")
print(c_tk[['tradedate','close','fwd_ret_5']].head(10).to_string())

# 8) события по этому тикеру — смотрим даты
ev_tk = events[events['ticker'] == tk].sort_values('tradedate')
print(f"\n=== events {tk}: {len(ev_tk)} событий ===")
print(ev_tk[['tradedate','alert_type']].head(10).to_string())
