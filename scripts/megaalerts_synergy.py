"""
MegaAlerts + независимые подтверждения:
  1. + HI2 (hhi-поток) — подтверждение силы
  2. + IMOEX (рыночный контекст) — растёт ли рынок
  3. + объём M10 — ликвидность
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
    frames.append(c[['ticker','tradedate','close','volume']])
candles = pd.concat(frames, ignore_index=True).sort_values(['ticker','tradedate']).reset_index(drop=True)
for h in (1, 3, 5):
    candles[f'fwd_{h}d'] = candles.groupby('ticker')['close'].shift(-h) / candles['close'] - 1.0

# --- HI2 ---
hi2 = pd.read_parquet('data/hi2_daily.parquet')
hi2['tradedate'] = pd.to_datetime(hi2['tradedate']).dt.normalize()
# z-score по тикеру
for col in ['hhi_buy','hhi_sell','hhi_netflow_buy','hhi_agressive_buy']:
    if col in hi2.columns:
        g = hi2.groupby('ticker')[col]
        hi2[f'{col}_z'] = (hi2[col] - g.transform('mean')) / g.transform('std')
if all(f'{c}_z' in hi2.columns for c in ['hhi_buy','hhi_netflow_buy','hhi_agressive_buy']):
    hi2['hi2_score'] = (hi2['hhi_buy_z'] + hi2['hhi_netflow_buy_z'] + hi2['hhi_agressive_buy_z']) / 3

# --- IMOEX ---
imoex = pd.read_parquet('data/sector_indices/IMOEX_D1.parquet')
imoex['tradedate'] = pd.to_datetime(imoex['begin']).dt.normalize()
imoex = imoex[['tradedate','close']].rename(columns={'close':'imoex_close'})
imoex['imoex_5d'] = imoex['close'].pct_change(5) if 'close' in imoex.columns else imoex['imoex_close'].pct_change(5)

# --- merge ---
merged = events.merge(candles, on=['ticker','tradedate'], how='inner')
merged = merged.merge(hi2[['ticker','tradedate','hi2_score']], on=['ticker','tradedate'], how='left')
merged = merged.merge(imoex[['tradedate','imoex_close']], on='tradedate', how='left')

# --- анализ синергии ---
print("=== синергия с HI2 ===")
for at in ['oi_low_min','vol_b_99_9_pctl','pr_high_max','net_vol_99_9_pctl-','pr_change_99_9_pctl-']:
    sub = merged[merged['alert_type'] == at].copy()
    sub = sub.dropna(subset=['hi2_score','fwd_5d'])
    if len(sub) < 10:
        print(f"  {at:32s} | мало данных (n={len(sub)})")
        continue
    strong = sub[sub['hi2_score'] > 1]
    weak = sub[sub['hi2_score'] <= 1]
    print(f"  {at:32s}")
    print(f"    strong hi2 (n={len(strong):3d}) fwd_5d={strong['fwd_5d'].mean():+.3%}")
    print(f"    weak hi2   (n={len(weak):3d}) fwd_5d={weak['fwd_5d'].mean():+.3%}")

# --- синергия с IMOEX ---
print("\n=== синергия с IMOEX (растущий рынок) ===")
for at in ['oi_low_min','vol_b_99_9_pctl','pr_high_max','net_vol_99_9_pctl-']:
    sub = merged[merged['alert_type'] == at].copy()
    sub = sub.dropna(subset=['fwd_5d'])
    if len(sub) < 10:
        continue
    imoex_5d = sub['imoex_close'] / sub['imoex_close'].shift(5) - 1.0
    sub['market_up'] = imoex_5d > 0
    up = sub[sub['market_up']]
    down = sub[~sub['market_up']]
    print(f"  {at:32s}")
    print(f"    рынок ↑ (n={len(up):3d})  fwd_5d={up['fwd_5d'].mean():+.3%}")
    print(f"    рынок ↓ (n={len(down):3d}) fwd_5d={down['fwd_5d'].mean():+.3%}")

# --- синергия с объёмом ---
print("\n=== синергия с объёмом (ликвидность) ===")
merged['vol_rank'] = merged.groupby('alert_type')['volume'].rank(pct=True) if 'volume' in merged.columns else 0.5
for at in ['oi_low_min','vol_b_99_9_pctl','pr_high_max']:
    sub = merged[merged['alert_type'] == at].dropna(subset=['fwd_5d','vol_rank'])
    if len(sub) < 10:
        continue
    high_vol = sub[sub['vol_rank'] > 0.7]
    low_vol = sub[sub['vol_rank'] < 0.3]
    print(f"  {at:32s}")
    print(f"    высокий vol (n={len(high_vol):3d}) fwd_5d={high_vol['fwd_5d'].mean():+.3%}")
    print(f"    низкий  vol (n={len(low_vol):3d}) fwd_5d={low_vol['fwd_5d'].mean():+.3%}")
