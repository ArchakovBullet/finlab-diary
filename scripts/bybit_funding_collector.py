#!/usr/bin/env python3
"""bybit_funding_collector.py — сбор funding rate (BTC/ETH/SOL, linear perp)."""
import os, time, requests
import pandas as pd
from datetime import datetime

BASE = "https://api.bybit.com"
OUT = "/root/finlab/data/bybit"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

def fetch_funding(symbol, limit=200):
    r = requests.get(f"{BASE}/v5/market/funding/history",
                     params={"category": "linear", "symbol": symbol, "limit": limit}, timeout=20)
    r.raise_for_status()
    j = r.json()
    if j.get("retCode") != 0:
        raise RuntimeError(j.get("retMsg"))
    lst = j.get("result", {}).get("list", [])
    if not lst:
        return pd.DataFrame()
    df = pd.DataFrame(lst)
    df["fundingRate"] = pd.to_numeric(df["fundingRate"], errors="coerce")
    df["ts"] = pd.to_datetime(df["fundingRateTimestamp"].astype("int64"), unit="ms", utc=True).dt.tz_convert(None)
    df = df[["ts", "fundingRate"]].dropna().sort_values("ts").reset_index(drop=True)
    return df

def main():
    os.makedirs(OUT, exist_ok=True)
    for sym in SYMBOLS:
        try:
            df = fetch_funding(sym, limit=200)
            if df.empty:
                print(f"{sym}: пусто"); continue
            path = os.path.join(OUT, f"funding_{sym}.parquet")
            df.to_parquet(path, index=False)
            print(f"{sym}: {len(df)} строк -> {path} (last: {df['ts'].iloc[-1]})")
        except Exception as e:
            print(f"{sym}: ERROR {e}")

if __name__ == "__main__":
    main()
