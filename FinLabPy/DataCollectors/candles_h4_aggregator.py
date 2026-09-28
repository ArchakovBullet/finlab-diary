"""
Агрегатор H4-свечей для акций из M10 (fallback: H1).

Для каждого {ticker}_M10.parquet в data/candles/:
  - resample('4h') по begin
  - open=first, high=max, low=min, close=last, value=sum, volume=sum
  - пишем в data/candles/{ticker}_H4.parquet

Пропускаем тикеры, у которых нет M10 и H1.
Существующие H4 — перезаписываем (с бэкапом не нужно: H4 — производные данные).
"""
import pandas as pd
import glob
import os
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path('/root/finlab')
CANDLES_DIR = ROOT / 'data' / 'candles'


def aggregate_one(ticker: str, src_tf: str) -> bool:
    """Агрегирует {ticker}_{src_tf}.parquet в {ticker}_H4.parquet."""
    src = CANDLES_DIR / f'{ticker}_{src_tf}.parquet'
    dst = CANDLES_DIR / f'{ticker}_H4.parquet'

    if not src.exists():
        return False

    df = pd.read_parquet(src)
    if len(df) == 0:
        return False

    # нормализуем begin
    if 'begin' not in df.columns:
        print(f'  ⚠️ {ticker}: нет колонки begin')
        return False
    df['begin'] = pd.to_datetime(df['begin'], errors='coerce')
    df = df.dropna(subset=['begin']).sort_values('begin').reset_index(drop=True)
    if len(df) == 0:
        return False
    df = df.set_index('begin')

    # колонки для агрегации — только те, что есть
    agg = {}
    for c in ['open', 'high', 'low', 'close', 'value', 'volume']:
        if c in df.columns:
            if c in ('open',):
                agg[c] = 'first'
            elif c in ('high',):
                agg[c] = 'max'
            elif c in ('low',):
                agg[c] = 'min'
            elif c in ('close',):
                agg[c] = 'last'
            elif c in ('value', 'volume'):
                agg[c] = 'sum'

    if 'close' not in agg:
        print(f'  ⚠️ {ticker}: нет колонки close')
        return False

    # ресемплинг
    h4 = df.resample('4h').agg(agg).dropna(subset=['close']).reset_index()

    if len(h4) == 0:
        return False

    # добавляем end = begin + 4h - 1s (совместимо с D1/H1)
    h4['end'] = (h4['begin'] + pd.Timedelta(hours=4) - pd.Timedelta(seconds=1)).astype(str)

    # порядок колонок как в D1/H1
    cols = [c for c in ['open', 'close', 'high', 'low', 'value', 'volume', 'begin', 'end'] if c in h4.columns]
    h4 = h4[cols]

    h4.to_parquet(dst, index=False)
    return True


def main():
    files_m10 = sorted(glob.glob(str(CANDLES_DIR / '*_M10.parquet')))
    files_h1 = sorted(glob.glob(str(CANDLES_DIR / '*_H1.parquet')))
    tickers_m10 = {os.path.basename(f).replace('_M10.parquet', '') for f in files_m10}
    tickers_h1 = {os.path.basename(f).replace('_H1.parquet', '') for f in files_h1}
    all_tickers = sorted(tickers_m10 | tickers_h1)

    print(f'M10: {len(tickers_m10)} тикеров, H1: {len(tickers_h1)} тикеров, всего: {len(all_tickers)}')

    ok = 0
    fail = 0
    for tk in all_tickers:
        # приоритет: M10, fallback: H1
        src = 'M10' if tk in tickers_m10 else 'H1'
        try:
            if aggregate_one(tk, src):
                ok += 1
            else:
                fail += 1
        except Exception as e:
            print(f'  ❌ {tk}: {type(e).__name__}: {e}')
            fail += 1

    print(f'\n✅ Готово: {ok} тикеров, ❌ ошибок: {fail}')
    print(f'   Файлы H4 в {CANDLES_DIR}')


if __name__ == '__main__':
    main()
