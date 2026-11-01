#!/usr/bin/env python3
"""
analyze_funding.py — анализ funding (BTC/ETH/SOL) из Bybit.
Read-only. Пишет CSV в logs/.
"""
import os
import numpy as np
import pandas as pd
from datetime import datetime

ROOT = "/root/finlab"
DATA = os.path.join(ROOT, "data", "bybit")
OUT_DIR = os.path.join(ROOT, "logs")
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

def analyze(sym):
    p = os.path.join(DATA, f"funding_{sym}.parquet")
    if not os.path.exists(p):
        return None
    df = pd.read_parquet(p)
    df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
    df = df.dropna().sort_values("ts").reset_index(drop=True)
    if len(df) == 0:
        return None
    fr = df["fundingRate"].values
    median_diff_h = float(df["ts"].diff().dt.total_seconds().median() / 3600) if len(df) > 1 else None
    return {
        "symbol": sym,
        "n": len(fr),
        "first": str(df["ts"].iloc[0]),
        "last": str(df["ts"].iloc[-1]),
        "mean_pct": float(fr.mean() * 100),
        "median_pct": float(np.median(fr) * 100),
        "std_pct": float(fr.std() * 100),
        "positive_pct": float((fr > 0).mean() * 100),
        "cum_pct": float((np.prod(1 + fr) - 1) * 100),
        "min_pct": float(fr.min() * 100),
        "max_pct": float(fr.max() * 100),
        "median_diff_h": median_diff_h,
    }

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rows = []
    for sym in SYMBOLS:
        r = analyze(sym)
        if r is None:
            print(f"{sym}: нет данных"); continue
        rows.append(r)
        print(f"{sym}: n={r['n']} mean={r['mean_pct']:.4f}% median={r['median_pct']:.4f}% "
              f"positive={r['positive_pct']:.1f}% cum={r['cum_pct']:.2f}% "
              f"min={r['min_pct']:.4f}% max={r['max_pct']:.4f}% period={r['median_diff_h']}h")
    if not rows:
        return
    out = pd.DataFrame(rows)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    path = os.path.join(OUT_DIR, f"funding_analysis_{ts}.csv")
    out.to_csv(path, index=False)
    print(f"\nСохранено: {path}")
    print("\n=== Сравнение с fee (Bybit 0.13%) ===")
    for r in rows:
        daily_funding = r["mean_pct"] * 3  # 3 funding в день
        print(f"  {r['symbol']}: daily_funding ~{daily_funding:.4f}%/день, "
              f"fee 0.13% (вход+выход) -> окупаемость ~{0.13 / daily_funding if daily_funding > 0 else 999:.1f} дней")

if __name__ == "__main__":
    main()
