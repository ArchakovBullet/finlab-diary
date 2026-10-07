#!/usr/bin/env python3
"""
baseline_on_intraday_v2.py — M10/H1 с комиссией и разными HOLD.

Добавлено:
- Комиссия 0.28% (0.14% × 2) на сделку.
- HOLD: 1, 3, 6, 12, 30, 60 баров.
- Опционально: фильтр по волатильности.
"""
import pandas as pd
import numpy as np
import sys
import time

TICKERS = ['BR', 'CE', 'CNYRUBF', 'CR', 'ED', 'EURRUBF', 'FF', 'GAZPF',
           'GD', 'GLDRUBF', 'IMOEXF', 'MX', 'OJ', 'PD', 'PT',
           'SBERF', 'SI', 'SV', 'USDRUBF', 'VI', 'W4']

LOOKBACK = 240
COMMISSION = 0.0028  # 0.28%
COLS = ['val_net', 'vol_net', 'trades_net', 'pr_body', 'sec_pr_range']
HOLDS = [1, 3, 6, 12, 30, 60]


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
        try:
            df = load_intraday(ticker)
        except Exception:
            continue
        if len(df) < LOOKBACK + max(HOLDS) + 10:
            continue

        floor_map = {'M10': '10min', 'H1': 'h', 'H4': '4h'}
        df['bucket'] = df['dt'].dt.floor(floor_map[interval])
        agg = df.groupby('bucket').agg({
            **{c: 'sum' for c in COLS},
            'pr_close': 'last',
        }).reset_index().sort_values('bucket').reset_index(drop=True)

        for c in COLS:
            agg[f'{c}_q80'] = agg[c].rolling(LOOKBACK, min_periods=LOOKBACK // 2).quantile(0.8)
            agg[f'{c}_q20'] = agg[c].rolling(LOOKBACK, min_periods=LOOKBACK // 2).quantile(0.2)
            agg[f'{c}_top'] = (agg[c] > agg[f'{c}_q80']).astype(int)
            agg[f'{c}_bot'] = (agg[c] < agg[f'{c}_q20']).astype(int)

        agg['long_c'] = agg[[f'{c}_top' for c in COLS]].sum(axis=1)
        agg['short_c'] = agg[[f'{c}_bot' for c in COLS]].sum(axis=1)

        agg['dir'] = None
        agg.loc[agg['long_c'] >= 2, 'dir'] = 'LONG'
        agg.loc[agg['short_c'] >= 2, 'dir'] = 'SHORT'

        for hold in HOLDS:
            agg[f'exit_p_{hold}'] = agg['pr_close'].shift(-hold)

        for i in range(LOOKBACK, len(agg) - max(HOLDS)):
            r = agg.iloc[i]
            if pd.isna(r['dir']):
                continue
            entry = float(r['pr_close'])
            for hold in HOLDS:
                exit_p = r.get(f'exit_p_{hold}')
                if pd.isna(exit_p):
                    continue
                exit_p = float(exit_p)
                if r['dir'] == 'LONG':
                    pnl_gross = (exit_p - entry) / entry * 100  # %
                else:
                    pnl_gross = (entry - exit_p) / entry * 100
                pnl_net = pnl_gross - COMMISSION * 100  # в %
                all_rows.append({'ticker': ticker, 'dt': r['bucket'],
                                 'interval': interval, 'hold': hold,
                                 'dir': r['dir'], 'pnl_gross': pnl_gross, 'pnl_net': pnl_net})
    return pd.DataFrame(all_rows)


def metrics(r):
    if len(r) == 0:
        return {'n': 0, 'wr': 0, 'sharpe': 0, 'total': 0}
    sharpe = r.mean() / r.std() if r.std() > 0 else 0
    return {'n': len(r), 'wr': 100 * (r > 0).mean(),
            'sharpe': sharpe, 'total': r.sum()}


if __name__ == '__main__':
    intervals = sys.argv[1:] if len(sys.argv) > 1 else ['M10']
    for interval in intervals:
        print(f'\n######## Интервал: {interval} ########')
        t0 = time.time()
        df = build_events(interval)
        print(f'Событий: {len(df)}, время: {time.time()-t0:.1f}с')
        for hold in HOLDS:
            r = df[df['hold'] == hold]['pnl_net']
            m = metrics(r)
            print(f'  HOLD={hold:3d} | n={m["n"]:6d} | WR={m["wr"]:5.1f}% | Sharpe={m["sharpe"]:.3f} | Total={m["total"]:.0f}%')
