#!/usr/bin/env python3
"""bybit_h1_collector.py — H1 BTCUSDT, 2 года (правильная пагинация)."""
import os, time, requests
import pandas as pd
from datetime import datetime

BASE = "https://api.bybit.com"
OUT = "/root/finlab/data/bybit"
SYMBOL = "BTCUSDT"
INTERVAL = "60"

def main():
    os.makedirs(OUT, exist_ok=True)
    now = int(datetime.now().timestamp() * 1000)
    start = now - 2*365*24*3600*1000
    all_rows = []
    cur = start
    while cur < now:
        params = {"category": "linear", "symbol": SYMBOL, "interval": INTERVAL, "limit": 1000, "start": cur}
        j = None
        for attempt in range(3):
            try:
                r = requests.get(f"{BASE}/v5/market/kline", params=params, timeout=10)
                j = r.json()
                if j.get("retCode") == 0:
                    break
                print(f"retry {attempt+1}: {j.get('retMsg')}")
                time.sleep(5)
            except Exception as e:
                print(f"retry {attempt+1}: {e}")
                time.sleep(5)
        if not j or j.get("retCode") != 0:
            print("ERROR: max retries"); break
        lst = j.get("result", {}).get("list", [])
        if not lst: break
        all_rows.extend(lst)
        print(f"chunk {len(all_rows)//1000}: +{len(lst)} rows, newest={pd.to_datetime(int(lst[0][0]), unit='ms')}", flush=True)
        if len(lst) < 1000: break
        newest = int(lst[0][0])
        if newest >= now: break
        cur = newest + 1
        time.sleep(1.0)
    if not all_rows:
        print("Нет данных"); return
    df = pd.DataFrame(all_rows, columns=["start","open","high","low","close","volume","turnover"])
    for c in ["open","high","low","close","volume","turnover"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["begin"] = pd.to_datetime(df["start"].astype("int64"), unit="ms", utc=True).dt.tz_convert(None)
    df = df.dropna(subset=["begin","close"]).drop_duplicates(subset=["begin"]).sort_values("begin").reset_index(drop=True)
    path = os.path.join(OUT, f"{SYMBOL}_H1.parquet")
    df[["begin","open","high","low","close","volume"]].to_parquet(path, index=False)
    print(f"{SYMBOL} H1: {len(df)} строк -> {path} (first: {df['begin'].iloc[0]}, last: {df['begin'].iloc[-1]})")

if __name__ == "__main__":
    main()
