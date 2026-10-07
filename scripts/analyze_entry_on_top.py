#!/usr/bin/env python3
"""
analyze_entry_on_top.py — входы v1/v2 на вершинах?

Для каждой позиции:
- entry_price vs close предыдущего дня: gap_pct
- entry_price vs high последних 5 дней: pct_5d_high
- entry_price vs high следующих 5 дней: pct_next5
- Сколько входов были выше close_prev, и на сколько
"""
import sqlite3
from pathlib import Path
import pandas as pd


ROBOT_DB = {
    'v1': Path('/root/finlab/robots/futures_algopack_robot.db'),
    'v2': Path('/root/finlab/robots/futures_algopack_robot_v2.db'),
}
CANDLES = Path('/root/finlab/data/candles')


def load_d1(ticker):
    f = CANDLES / f'{ticker}_D1.parquet'
    if not f.exists():
        return None
    df = pd.read_parquet(f)
    df['begin'] = pd.to_datetime(df['begin'])
    return df.sort_values('begin').reset_index(drop=True)


def analyze(robot_name, db_path):
    if not db_path.exists():
        return
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, ticker, direction, entry_price, entry_time "
        "FROM algopack_positions ORDER BY id"
    ).fetchall()
    conn.close()

    print(f'\n========== {robot_name} ==========')
    print(f'{"id":>3} {"ticker":<9} {"dir":<5} {"entry":>10} '
          f'{"prev_close":>10} {"gap%":>7} '
          f'{"5d_high":>10} {"pct_5d_high":>12} '
          f'{"next5_high":>11} {"pct_next5":>10}')

    gaps_list = []
    pct_5d_high_list = []
    pct_next5_list = []
    for r in rows:
        ticker = r['ticker']
        df = load_d1(ticker)
        if df is None:
            continue
        entry_dt = pd.to_datetime(r['entry_time'])
        prev = df[df['begin'] < entry_dt.replace(hour=23, minute=59)]
        if len(prev) == 0:
            continue
        prev_close = float(prev.iloc[-1]['close'])

        idx = df[df['begin'] < entry_dt].index
        if len(idx) == 0:
            continue
        last_idx = idx[-1]
        start_5d = max(0, last_idx - 4)
        high_5d = float(df.iloc[start_5d:last_idx + 1]['high'].max())

        after_idx = df[df['begin'] >= entry_dt].index
        if len(after_idx) == 0:
            continue
        start_after = after_idx[0]
        end_after = min(len(df), start_after + 5)
        if end_after - start_after < 2:
            high_next5 = None
        else:
            high_next5 = float(df.iloc[start_after:end_after]['high'].max())

        entry = float(r['entry_price']) if r['entry_price'] else 0.0
        gap_pct_val = (entry - prev_close) / prev_close * 100 if prev_close else 0.0
        pct_5d_high_val = (entry - high_5d) / high_5d * 100 if high_5d else 0.0
        if high_next5 is not None:
            pct_next5_val = (entry - high_next5) / high_next5 * 100
        else:
            pct_next5_val = None

        next5_str = f'{high_next5:>11.4f}' if high_next5 is not None else f'{"n/a":>11}'
        pct_next5_str = f'{pct_next5_val:>+9.2f}%' if pct_next5_val is not None else f'{"n/a":>10}'
        print(f'{r["id"]:>3} {ticker:<9} {r["direction"]:<5} {entry:>10.4f} '
              f'{prev_close:>10.4f} {gap_pct_val:>+6.2f}% '
              f'{high_5d:>10.4f} {pct_5d_high_val:>+11.2f}% '
              f'{next5_str} {pct_next5_str}')

        gaps_list.append(gap_pct_val)
        pct_5d_high_list.append(pct_5d_high_val)
        if pct_next5_val is not None:
            pct_next5_list.append(pct_next5_val)

    if gaps_list:
        n = len(gaps_list)
        print(f'\n--- Сводка по {robot_name} ({n} позиций) ---')
        print(f'  Средний gap (entry vs prev_close): {sum(gaps_list)/n:+.2f}%')
        print(f'  Средний pct от 5d_high: {sum(pct_5d_high_list)/n:+.2f}%')
        if pct_next5_list:
            print(f'  Средний pct от next5_high: {sum(pct_next5_list)/len(pct_next5_list):+.2f}% (n={len(pct_next5_list)})')
        above = sum(1 for g in gaps_list if g > 0)
        print(f'  Входов выше prev_close: {above}/{n} ({100*above/n:.0f}%)')
        near_high = sum(1 for p in pct_5d_high_list if p > -1.0)
        print(f'  Входов в пределах 1% от 5d_high: {near_high}/{n} ({100*near_high/n:.0f}%)')
        if pct_next5_list:
            near_next5 = sum(1 for p in pct_next5_list if p > -1.0)
            nn5 = len(pct_next5_list)
            print(f'  Входов в пределах 1% от next5_high: {near_next5}/{nn5} ({100*near_next5/nn5:.0f}%)')


if __name__ == '__main__':
    for name, path in ROBOT_DB.items():
        analyze(name, path)
