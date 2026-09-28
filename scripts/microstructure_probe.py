"""
Проверка: содержат ли SuperCandles/TradeStats информацию о будущем движении.

Гипотезы:
  1. disb (дисбаланс) -> forward return
  2. vol (объём) -> |forward return| (волатильность)
  3. trades_b - trades_s -> forward return
  4. Агрегированный за день disb -> forward return на 1/5 дней
"""
import pandas as pd, numpy as np, glob, os

def load(path_pattern, ticker):
    files = glob.glob(path_pattern)
    for f in files:
        if os.path.basename(f).startswith(ticker + '_'):
            df = pd.read_parquet(f)
            df['tradedate'] = pd.to_datetime(df['tradedate']).dt.normalize()
            df['tradetime'] = pd.to_datetime(df['tradedate'].astype(str) + ' ' + df['tradetime'])
            df = df.sort_values('tradetime').reset_index(drop=True)
            return df
    return None

def probe_intraday(df, name, horizons_min=(5, 15, 30, 60)):
    print(f"\n===== {name}: {len(df)} строк, {df['tradedate'].nunique()} дней =====")
    print(f"период: {df['tradedate'].min().date()} .. {df['tradedate'].max().date()}")

    for h in horizons_min:
        # forward return на h баров вперёд (5-мин бары)
        df[f'fwd_{h}'] = df['pr_close'].shift(-h) / df['pr_close'] - 1.0

    # 1) корреляция disb -> fwd_ret
    print("\n--- корреляция disb -> fwd_ret ---")
    for h in horizons_min:
        sub = df[['disb', f'fwd_{h}']].dropna()
        if len(sub) < 100:
            continue
        corr = sub['disb'].corr(sub[f'fwd_{h}'])
        print(f"  h={h:3d} мин | corr={corr:+.4f} | n={len(sub)}")

    # 2) корреляция vol -> |fwd_ret|
    print("\n--- корреляция vol -> |fwd_ret| (волатильность) ---")
    for h in horizons_min:
        sub = df[['vol', f'fwd_{h}']].dropna()
        if len(sub) < 100:
            continue
        sub = sub.assign(abs_fwd=sub[f'fwd_{h}'].abs())
        corr = sub['vol'].corr(sub['abs_fwd'])
        print(f"  h={h:3d} мин | corr={corr:+.4f} | n={len(sub)}")

    # 3) trades_b - trades_s -> fwd_ret
    print("\n--- корреляция (trades_b - trades_s) -> fwd_ret ---")
    df['tb_ts'] = df['trades_b'] - df['trades_s']
    for h in horizons_min:
        sub = df[['tb_ts', f'fwd_{h}']].dropna()
        if len(sub) < 100:
            continue
        corr = sub['tb_ts'].corr(sub[f'fwd_{h}'])
        print(f"  h={h:3d} мин | corr={corr:+.4f} | n={len(sub)}")

    # 4) агрегация по дням: сумма disb -> forward return на 1/5 дней
    print("\n--- дневная агрегация: сумма disb за день -> forward close ---")
    daily = df.groupby('tradedate').agg(
        disb_sum=('disb', 'sum'),
        vol_sum=('vol', 'sum'),
        close=('pr_close', 'last'),
    ).reset_index()
    daily = daily.sort_values('tradedate')
    for h in (1, 5):
        daily[f'fwd_{h}d'] = daily['close'].shift(-h) / daily['close'] - 1.0

    for h in (1, 5):
        sub = daily[['disb_sum', f'fwd_{h}d']].dropna()
        if len(sub) < 10:
            print(f"  h={h}d | мало данных (n={len(sub)})")
            continue
        corr = sub['disb_sum'].corr(sub[f'fwd_{h}d'])
        print(f"  h={h}d | corr(disb_sum, fwd_ret)={corr:+.4f} | n={len(sub)}")

# --- тест на SBER (акция, SuperCandles) ---
sc = load('data/supercandles/*.parquet', 'SBER')
if sc is not None:
    probe_intraday(sc, 'SuperCandles SBER')
else:
    print("SBER в supercandles не найден")

# --- тест на BR (фьючерс, TradeStats) ---
ts = load('data/tradestats/*.parquet', 'BR')
if ts is not None:
    probe_intraday(ts, 'TradeStats BR')
else:
    print("BR в tradestats не найден")
