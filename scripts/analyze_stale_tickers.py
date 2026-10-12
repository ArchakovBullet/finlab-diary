#!/usr/bin/env python3
"""analyze_stale_tickers.py — анализ «мёртвых» тикеров.

Для каждого тикера:
- последняя дата в M10/H1/H4/D1.
- есть ли в config (enabled/all).
- есть ли в других папках (supercandles, tradestats, futoi).
"""
import json
from pathlib import Path
from datetime import datetime
import pandas as pd

ROOT = Path('/root/finlab')
CANDLES = ROOT / 'data' / 'candles'
CONFIG = ROOT / 'FinLabPy' / 'My_Indicators' / 'pairs_config.json'

STALE = ['CRU6', 'PI', 'UT', 'IN', 'KZ', 'BY', 'TY', 'SY', 'CS', 'HK', 'I2', 'JD', 'NO', 'RF', 'LQDT']


def get_last_date(ticker, tf):
    f = CANDLES / f'{ticker}_{tf}.parquet'
    if not f.exists():
        return None
    try:
        df = pd.read_parquet(f)
        if len(df) == 0:
            return None
        col = 'begin' if 'begin' in df.columns else 'tradedate'
        return str(df[col].iloc[-1])[:19]
    except Exception as e:
        return f'ERROR: {e}'


def main():
    c = json.load(open(CONFIG))
    pairs = c.get('pairs', {})
    for t in STALE:
        print(f'\n=== {t} ===')
        for tf in ['M10', 'H1', 'H4', 'D1']:
            last = get_last_date(t, tf)
            print(f'  {tf}: {last}')
        # В config
        in_pairs = []
        for k, v in pairs.items():
            base = k.replace('_M10', '').replace('_H1', '').replace('_H4', '').replace('_D1', '')
            if '-' in base:
                a, b = base.split('-', 1)
                if a == t or b == t:
                    in_pairs.append((k, v.get('enabled')))
        if in_pairs:
            print(f'  В config: {in_pairs}')
        else:
            print(f'  В config: нет')


if __name__ == '__main__':
    main()
