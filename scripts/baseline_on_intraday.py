#!/usr/bin/env python3
"""
baseline_on_intraday.py — baseline на внутридневных TradeStats (ОПТИМИЗИРОВАННЫЙ).

Использует rolling-квантили (окно = LOOKBACK), а не весь history.
Это даёт O(N) вместо O(N²).

Варианты: M10 (floor 10min), H1 (floor 1h), H4 (floor 4h).
"""
import pandas as pd
import numpy as np
import sys
import time

TICKERS = ['BR', 'CE', 'CNYRUBF', 'CR', 'ED', 'EURRUBF', 'FF', 'GAZPF',
           'GD', 'GLDRUBF', 'IMOEXF', 'MX', 'OJ', 'PD', 'PT',
           'SBERF', 'SI', 'SV', 'USDRUBF', 'VI', 'W4']

LOOKBACK = 240        # 240 * 5 мин = 20 часов ≈ 4 дня M10-баров
HOLD_INTERVALS = 30   # 30 * 10 мин = 5 часов
COLS = ['val_net', 'vol_net', 'trades_net', 'pr_body', 'sec_pr_range']


def load_intraday(ticker):
    df = pd.read_parquet(f'data/tradestats/{ticker}_tradestats.parquet')
    df['dt'] = pd.to_datetime(df['tradedate'].astype(str) + ' ' + df['tradetime'].astype(str))
    df = df.sort_values('dt').reset_index(drop=True)
    df['val_net'] = df['val_b'] - df['val_s']
    df['vol_net'] = df['vol_b'] - df['vol_s']
    df['trades_net'] = df['trades_b'] - df['trades_s']
    df['pr_body'] = df['pr_close'] - df['pr_open']
    df['sec_pr_range'] = df['sec_pr_high'] - df['sec_pr_low']
    return df


def build_events(interval='M10'):
    all_rows = []
    for ticker in TICKERS:
        t0 = time.time()
        try:
            df = load_intraday(ticker)
        except Exception as e:
            print(f'{ticker}: ошибка {e}')
            continue
        if len(df) < LOOKBACK + HOLD_INTERVALS + 10:
            continue

        floor_map = {'M10': '10min', 'H1': 'h', 'H4': '4h'}
        if interval not in floor_map:
            print(f'Неизвестный interval: {interval}')
            return pd.DataFrame()

        df['bucket'] = df['dt'].dt.floor(floor_map[interval])
        agg = df.groupby('bucket').agg({
            **{c: 'sum' for c in COLS},
            'pr_close': 'last',
        }).reset_index().sort_values('bucket').reset_index(drop=True)

        # ВЕКТОРИЗАЦИЯ: rolling quantile
        for c in COLS:
            agg[f'{c}_q80'] = agg[c].rolling(LOOKBACK, min_periods=LOOKBACK // 2).quantile(0.8)
            agg[f'{c}_q20'] = agg[c].rolling(LOOKBACK, min_periods=LOOKBACK // 2).quantile(0.2)

        # Сигналы: top/bot
        for c in COLS:
            agg[f'{c}_top'] = (agg[c] > agg[f'{c}_q80']).astype(int)
            agg[f'{c}_bot'] = (agg[c] < agg[f'{c}_q20']).astype(int)

        agg['long_c'] = agg[[f'{c}_top' for c in COLS]].sum(axis=1)
        agg['short_c'] = agg[[f'{c}_bot' for c in COLS]].sum(axis=1)

        # Направление
        agg['dir'] = None
        agg.loc[agg['long_c'] >= 2, 'dir'] = 'LONG'
        agg.loc[agg['short_c'] >= 2, 'dir'] = 'SHORT'

        # PnL: entry=pr_close, exit=pr_close через HOLD
        agg['exit_p'] = agg['pr_close'].shift(-HOLD_INTERVALS)

        for i in range(LOOKBACK, len(agg) - HOLD_INTERVALS):
            r = agg.iloc[i]
            if pd.isna(r['dir']) or pd.isna(r['exit_p']):
                continue
            entry = float(r['pr_close'])
            exit_p = float(r['exit_p'])
            pnl = (exit_p - entry) if r['dir'] == 'LONG' else (entry - exit_p)
            all_rows.append({'ticker': ticker, 'dt': r['bucket'],
                             'interval': interval, 'dir': r['dir'], 'pnl': pnl})
        print(f'  {ticker}: {len(df)} записей → {len(agg)} bucket, {time.time()-t0:.1f}с')

    return pd.DataFrame(all_rows)


def metrics(r):
    if len(r) == 0:
        return {'n': 0, 'wr': 0, 'sharpe': 0, 'total': 0}
    sharpe = r['pnl'].mean() / r['pnl'].std() if r['pnl'].std() > 0 else 0
    return {'n': len(r), 'wr': 100 * (r['pnl'] > 0).mean(),
            'sharpe': sharpe, 'total': r['pnl'].sum()}


def walkforward(df, n_folds=5):
    d = df.sort_values('dt').reset_index(drop=True)
    if len(d) < n_folds * 5:
        print(f'Мало сделок ({len(d)})')
        return
    fold_size = len(d) // n_folds
    print(f'\n===== Walk-forward ({len(d)} сделок, {n_folds} фолдов) =====')
    print(f'{"fold":>4} {"test_n":>7} {"test_sharpe":>12} {"test_wr":>8} {"test_pnl":>10}')
    for k in range(n_folds):
        test = d.iloc[(k + 1) * fold_size: (k + 2) * fold_size] if k < n_folds - 1 else d.iloc[k * fold_size:]
        if len(test) == 0:
            continue
        ms = metrics(test)
        print(f'{k+1:>4} {ms["n"]:>7} {ms["sharpe"]:>12.3f} {ms["wr"]:>7.1f}% {ms["total"]:>10.0f}')


if __name__ == '__main__':
    intervals = sys.argv[1:] if len(sys.argv) > 1 else ['M10']
    for interval in intervals:
        print(f'\n######## Интервал: {interval} ########')
        t0 = time.time()
        df = build_events(interval)
        print(f'Всего событий: {len(df)}, время: {time.time()-t0:.1f}с')
        m = metrics(df)
        print(f'Общее: n={m["n"]}, WR={m["wr"]:.1f}%, Sharpe={m["sharpe"]:.3f}, Total={m["total"]:.0f}')
        walkforward(df)
