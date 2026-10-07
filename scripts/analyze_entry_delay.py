#!/usr/bin/env python3
"""
analyze_entry_delay.py — анализ задержки входа v1/v2.

Для каждой позиции в БД робота:
- entry_time: когда робот открыл позицию
- Сигнал был на закрытии предыдущего торгового дня (~18:30 МСК)
- Смотрим close D1 дня ПЕРЕД entry_time и entry_price
- Считаем разницу в %

Также:
- forward return от entry_price (на 5 дней)
- forward return от close D1 дня сигнала (на 5 дней)
- сравнение
"""
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import sys

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


def forward_return(df, from_date, days=5):
    """Forward return от close ближайшей свечи >= from_date, через N свечей."""
    m = df[df['begin'] >= from_date]
    if len(m) < 2:
        return None
    i0 = m.index[0]
    i1 = min(i0 + days, len(df) - 1)
    p0 = float(df.loc[i0, 'close'])
    p1 = float(df.loc[i1, 'close'])
    return (p1 - p0) / p0 * 100.0


def analyze(robot_name, db_path):
    if not db_path.exists():
        print(f'{robot_name}: БД не найдена')
        return
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, ticker, direction, entry_price, entry_time, status, exit_reason, pnl "
        "FROM algopack_positions ORDER BY id"
    ).fetchall()
    conn.close()

    print(f'\n========== {robot_name} ({len(rows)} позиций) ==========')
    print(f'{"id":>3} {"ticker":<9} {"dir":<5} {"entry_time":<19} '
          f'{"prev_close":>10} {"entry":>10} {"diff%":>7} '
          f'{"fwd_from_signal":>15} {"fwd_from_entry":>14}')

    total_delay = 0.0
    n = 0
    for r in rows:
        ticker = r['ticker']
        df = load_d1(ticker)
        if df is None:
            print(f'{r["id"]:>3} {ticker:<9} {r["direction"]:<5} {r["entry_time"]:<19} '
                  f'{"NO_D1":>10}')
            continue

        entry_dt = pd.to_datetime(r['entry_time'])
        # Последняя D1 свеча ПЕРЕД entry_time — это день сигнала (если entry в 10:00, то вчера)
        prev = df[df['begin'] < entry_dt.replace(hour=23, minute=59)]
        if len(prev) == 0:
            print(f'{r["id"]:>3} {ticker:<9} {r["direction"]:<5} {r["entry_time"]:<19} '
                  f'{"NO_PREV":>10}')
            continue
        signal_row = prev.iloc[-1]
        signal_date = signal_row['begin']
        signal_close = float(signal_row['close'])
        entry_price = float(r['entry_price']) if r['entry_price'] else 0.0
        diff_pct = (entry_price - signal_close) / signal_close * 100.0 if signal_close else 0.0

        fwd_signal = forward_return(df, signal_date, days=5)
        fwd_entry = forward_return(df, entry_dt, days=5)

        fs = f'{fwd_signal:+.2f}%' if fwd_signal is not None else '—'
        fe = f'{fwd_entry:+.2f}%' if fwd_entry is not None else '—'

        print(f'{r["id"]:>3} {ticker:<9} {r["direction"]:<5} {r["entry_time"]:<19} '
              f'{signal_close:>10.4f} {entry_price:>10.4f} {diff_pct:>+6.2f}% '
              f'{fs:>15} {fe:>14}')
        total_delay += diff_pct
        n += 1

    if n:
        print(f'\nСредняя задержка (entry vs signal close): {total_delay/n:+.2f}%')


if __name__ == '__main__':
    for name, path in ROBOT_DB.items():
        analyze(name, path)
