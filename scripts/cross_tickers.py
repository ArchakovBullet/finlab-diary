"""
Пересечение тикеров между источниками:
  - MegaAlerts
  - FutOI
  - TradeStats (собираем тикеры из secid, т.к. asset_code есть не везде)
  - candles
"""
import pandas as pd, glob, os

# MegaAlerts
files = sorted(glob.glob('data/mega_alerts/*.parquet'))
frames = []
for f in files:
    df = pd.read_parquet(f)
    df['ticker'] = os.path.basename(f).replace('_alerts.parquet','')
    frames.append(df)
events = pd.concat(frames, ignore_index=True)
key_cols = ['ticker','tradedate','tradetime','alert_type','threshold','value']
events = events.drop_duplicates(subset=key_cols)
ma_tickers = set(events['ticker'].unique())
print(f"MegaAlerts tickers: {len(ma_tickers)}")

# FutOI
futoi = pd.read_parquet('data/futoi_1h/futoi_1h.parquet')
fo_tickers = set(futoi['ticker'].unique())
print(f"FutOI tickers: {len(fo_tickers)}")

# TradeStats — собираем из secid (asset_code не везде)
ts_tickers = set()
for f in glob.glob('data/tradestats/*.parquet'):
    df = pd.read_parquet(f)
    # берём secid, потому что asset_code может отсутствовать
    col = 'secid' if 'secid' in df.columns else 'ticker'
    if col in df.columns:
        ts_tickers.update(df[col].astype(str).unique())
# базовый тикер — без буквы месяца (BRU6 -> BR)
ts_base = set()
for t in ts_tickers:
    if len(t) >= 2:
        ts_base.add(t[:2])  # BR, CR, GD, ...
ts_tickers = ts_tickers | ts_base
print(f"TradeStats tickers (из secid + базовые): {len(ts_tickers)}")

# Candles
candles_tickers = set()
for f in glob.glob('data/candles/*_D1.parquet'):
    candles_tickers.add(os.path.basename(f).replace('_D1.parquet',''))
print(f"Candles tickers: {len(candles_tickers)}")

# Пересечения
print("\n=== Пересечения ===")
print(f"MegaAlerts ∩ FutOI: {len(ma_tickers & fo_tickers)}")
print(f"  {sorted(ma_tickers & fo_tickers)[:30]}")

print(f"\nMegaAlerts ∩ TradeStats: {len(ma_tickers & ts_tickers)}")
print(f"  {sorted(ma_tickers & ts_tickers)[:30]}")

print(f"\nFutOI ∩ TradeStats: {len(fo_tickers & ts_tickers)}")
print(f"  {sorted(fo_tickers & ts_tickers)[:30]}")

print(f"\nMegaAlerts ∩ FutOI ∩ TradeStats: {len(ma_tickers & fo_tickers & ts_tickers)}")
print(f"  {sorted(ma_tickers & fo_tickers & ts_tickers)}")

# Сколько событий MegaAlerts на каждом пересечении
print("\n=== MegaAlerts событий на пересечениях ===")
e_fo = events[events['ticker'].isin(ma_tickers & fo_tickers)]
print(f"на MegaAlerts ∩ FutOI: {len(e_fo)} событий")
print(f"  топ типов:")
print(e_fo['alert_type'].value_counts().head(10).to_string())

e_ts = events[events['ticker'].isin(ma_tickers & ts_tickers)]
print(f"\nна MegaAlerts ∩ TradeStats: {len(e_ts)} событий")
print(f"  топ типов:")
print(e_ts['alert_type'].value_counts().head(10).to_string())
