import pandas as pd
import glob, os, datetime as dt

TARGETS = [
    'data/hi2/*.parquet',
    'data/hi2_daily.parquet',
    'data/futoi_1h/futoi_1h.parquet',
    'data/funding/*.parquet',
    'data/sector_indices/*.parquet',
    'data/candles/*_D1.parquet',
]

for pat in TARGETS:
    files = sorted(glob.glob(pat))
    if not files:
        print(f"[НЕТ ФАЙЛОВ] {pat}")
        continue
    for f in files[:3]:
        try:
            df = pd.read_parquet(f)
            cols = list(df.columns)
            date_col = next((c for c in ['tradedate','date','begin','time','tradetime'] if c in cols), None)
            last = None
            if date_col is not None:
                last = pd.to_datetime(df[date_col], errors='coerce').max()
            mtime = dt.datetime.fromtimestamp(os.path.getmtime(f)).strftime('%Y-%m-%d %H:%M')
            print(f"{f} | mtime={mtime} | rows={len(df)} | last={last} | cols={cols[:10]}")
        except Exception as e:
            print(f"[ОШИБКА] {f}: {e}")
