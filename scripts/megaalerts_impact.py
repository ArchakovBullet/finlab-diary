"""
MegaAlerts: влияют ли события на рынок?

Проверяем:
  1. forward return после события (5 / 15 / 30 / 60 минут) на M10 свечах
  2. сравнение с baseline (средний fwd_ret по всем барам)
  3. по типам алертов — какие дают эффект
  4. движение ДО события (если больше, чем после -> алерт опаздывает)
"""
import pandas as pd, numpy as np, glob, os

# --- 1. события ---
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
events['dt'] = pd.to_datetime(
    events['tradedate'].astype(str) + ' ' + events['tradetime'].astype(str)
)
# оставляем только 2026-07-01+, где плотная история
events = events[events['tradedate'] >= '2026-07-01'].copy()
print(f"события (07-01+): {len(events)}")
print(f"по типам (топ-10):")
print(events['alert_type'].value_counts().head(10).to_string())

# --- 2. M10 свечи ---
print("\n=== загружаем M10 свечи ===")
candles = []
for f in glob.glob('data/candles/*_M10.parquet'):
    c = pd.read_parquet(f)
    c['ticker'] = os.path.basename(f).replace('_M10.parquet', '')
    c['tradedate'] = pd.to_datetime(c['begin']).dt.normalize()
    c['dt'] = pd.to_datetime(c['begin'])
    c = c[['ticker','dt','tradedate','close']].copy()
    candles.append(c)
candles = pd.concat(candles, ignore_index=True)
candles = candles.sort_values(['ticker','dt']).reset_index(drop=True)
print(f"candles: {len(candles)} строк, {candles['ticker'].nunique()} тикеров")

# --- 3. baseline: fwd_ret по всем барам ---
def add_fwd(df, horizons_min, bar_min=10):
    """fwd_ret на N минут = N / bar_min баров вперёд."""
    d = df.sort_values(['ticker','dt']).copy()
    for h in horizons_min:
        k = h // bar_min
        d[f'fwd_{h}'] = d.groupby('ticker')['close'].shift(-k) / d['close'] - 1.0
    return d

candles = add_fwd(candles, horizons_min=[5, 15, 30, 60])
print("\n=== baseline (по всем барам M10) ===")
for h in [5, 15, 30, 60]:
    sub = candles[f'fwd_{h}'].dropna()
    print(f"  h={h:3d} мин | mean={sub.mean():+.5%} | std={sub.std():.5%} | n={len(sub)}")

# --- 4. merge: событие + ближайший бар ---
print("\n=== merge событий с M10 ===")
merged_list = []
for ticker, grp in events.groupby('ticker'):
    c = candles[candles['ticker'] == ticker]
    if len(c) == 0:
        continue
    m = pd.merge_asof(
        grp.sort_values('dt'),
        c[['dt','close'] + [f'fwd_{h}' for h in [5,15,30,60]]].sort_values('dt'),
        on='dt',
        direction='forward',
        tolerance=pd.Timedelta('15min'),
    )
    merged_list.append(m)

merged = pd.concat(merged_list, ignore_index=True)
print(f"смержилось: {len(merged)} из {len(events)}")

# --- 5. forward return после события по типам ---
print("\n=== fwd_ret после события (по типам) ===")
top_types = merged['alert_type'].value_counts().head(12).index.tolist()
for at in top_types:
    sub = merged[merged['alert_type'] == at]
    row = f"  {at:32s} | n={len(sub):4d}"
    for h in [5, 15, 30, 60]:
        m = sub[f'fwd_{h}'].mean()
        row += f" | h={h:2d}: {m:+.4%}" if pd.notna(m) else f" | h={h:2d}:    nan"
    print(row)

# --- 6. движение ДО события (fwd_ret назад) ---
print("\n=== проверка: 'алерт опаздывает?' — fwd_ret ДО события ===")
for ticker, grp in events.groupby('ticker'):
    c = candles[candles['ticker'] == ticker]
    if len(c) == 0:
        continue
    c = c.sort_values('dt').copy()
    for h in [5, 15, 30, 60]:
        c[f'back_{h}'] = c['close'] / c['close'].shift(h // 10) - 1.0
    m = pd.merge_asof(
        grp.sort_values('dt'),
        c[['dt'] + [f'back_{h}' for h in [5,15,30,60]]].sort_values('dt'),
        on='dt', direction='forward', tolerance=pd.Timedelta('15min'),
    )
    merged_list.append(m)

# соберём back_* колонки
back_frames = []
for ticker, grp in events.groupby('ticker'):
    c = candles[candles['ticker'] == ticker]
    if len(c) == 0:
        continue
    c = c.sort_values('dt').copy()
    for h in [5, 15, 30, 60]:
        c[f'back_{h}'] = c['close'] / c['close'].shift(h // 10) - 1.0
    m = pd.merge_asof(
        grp.sort_values('dt'),
        c[['dt'] + [f'back_{h}' for h in [5,15,30,60]]].sort_values('dt'),
        on='dt', direction='forward', tolerance=pd.Timedelta('15min'),
    )
    back_frames.append(m)

back_merged = pd.concat(back_frames, ignore_index=True)
for at in top_types:
    sub = back_merged[back_merged['alert_type'] == at]
    row = f"  {at:32s} | n={len(sub):4d}"
    for h in [5, 15, 30, 60]:
        m = sub[f'back_{h}'].mean()
        row += f" | h={h:2d}: {m:+.4%}" if pd.notna(m) else f" | h={h:2d}:    nan"
    print(row)
