#!/usr/bin/env python3
"""
bybit_collector.py — сборщик свечей Bybit (read-only) в data/bybit/.
Символы: BTCUSDT, ETHUSDT, SOLUSDT. TF: H4, M10 (по умолчанию).
Формат: begin, open, high, low, close, volume (как MOEX).
"""
import os, time, requests
import pandas as pd
from datetime import datetime, timezone

BASE = 'https://api.bybit.com'
OUT = '/root/finlab/data/bybit'
SYMBOLS = ['BTCUSDT','ETHUSDT','SOLUSDT']
# Bybit interval: 240 (H4), 10 (M10); limit<=1000
TF_MAP = {'H4':'240', 'M10':'10'}

def fetch_kline(symbol, interval, pages=10, limit=1000):
    out = []
    end = None
    for _ in range(pages):
        params = {'category':'linear','symbol':symbol,'interval':interval,'limit':limit}
        if end:
            params['end'] = end
        r = requests.get(f'{BASE}/v5/market/kline', params=params, timeout=20)
        r.raise_for_status()
        j = r.json()
        if j.get('retCode') != 0:
            raise RuntimeError(j.get('retMsg'))
        lst = j.get('result', {}).get('list', [])
        if not lst:
            break
        out.extend(lst)
        # list: [start, open, high, low, close, volume, turnover]
        oldest = int(lst[-1][0])
        end = oldest - 1
        time.sleep(0.15)
    if not out:
        return pd.DataFrame()
    df = pd.DataFrame(out, columns=['start','open','high','low','close','volume','turnover'])
    for c in ['open','high','low','close','volume','turnover']:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    df['begin'] = pd.to_datetime(df['start'].astype('int64'), unit='ms', utc=True).dt.tz_convert(None)
    df = df.dropna(subset=['begin','close']).drop_duplicates(subset=['begin']).sort_values('begin').reset_index(drop=True)
    return df[['begin','open','high','low','close','volume']]

def main():
    os.makedirs(OUT, exist_ok=True)
    for sym in SYMBOLS:
        for tf, interval in TF_MAP.items():
            try:
                df = fetch_kline(sym, interval, pages=10, limit=1000)
                if df.empty:
                    print(f"{sym} {tf}: пусто"); continue
                path = os.path.join(OUT, f"{sym}_{tf}.parquet")
                df.to_parquet(path, index=False)
                print(f"{sym} {tf}: {len(df)} строк -> {path} (last: {df['begin'].iloc[-1]})")
            except Exception as e:
                print(f"{sym} {tf}: ERROR {e}")

if __name__ == '__main__':
    main()
