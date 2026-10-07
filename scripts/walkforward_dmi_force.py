#!/usr/bin/env python3
"""
walkforward_dmi_force.py — walk-forward для DMI-cross + Force.

Варианты:
  A: DMI-cross + Force-cross (событие)
  B: DMI-cross вход + Force-cross выход
  C: DMI-cross + Force-state

Разбиение: 5 фолдов по времени (chronological split).
In-sample 70% / out-sample 30% на каждом фолде.
"""
import sys
sys.path.insert(0, '/root/finlab/FinLabPy')
import pandas as pd
import numpy as np
from pathlib import Path

TICKERS = ['BR', 'CE', 'CNYRUBF', 'CR', 'ED', 'EURRUBF', 'FF', 'GAZPF',
           'GD', 'GLDRUBF', 'IMOEXF', 'MX', 'OJ', 'PD', 'PT',
           'SBERF', 'SV', 'USDRUBF', 'VI', 'W4']
HOLD_DAYS = 5
LOOKBACK = 60
DMI_PERIOD = 14
FORCE_PERIOD = 13
N_FOLDS = 5


def algopack_dmi(daily, period=14):
    high = daily['val_b']; low = daily['val_s']; close = daily['val_net']
    plus_dm = high.diff(); minus_dm = -low.diff()
    plus_dm[plus_dm < 0] = 0; minus_dm[minus_dm < 0] = 0
    plus_dm[plus_dm < minus_dm] = 0; minus_dm[minus_dm < plus_dm] = 0
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx = dx.rolling(period).mean()
    return plus_di, minus_di, adx


def algopack_force(daily, period=13):
    fi = daily['vol'] * daily['val_net'].diff()
    return fi.ewm(span=period, adjust=False).mean()


def build_signals():
    """Собрать все события для всех тикеров (baseline + A/B/C)."""
    all_rows = []
    for ticker in TICKERS:
        try:
            df = pd.read_parquet(f'data/tradestats/{ticker}_tradestats.parquet')
        except Exception:
            continue
        df['tradedate'] = pd.to_datetime(df['tradedate'])
        df['val_net'] = df['val_b'] - df['val_s']
        df['vol_net'] = df['vol_b'] - df['vol_s']
        df['trades_net'] = df['trades_b'] - df['trades_s']
        df['pr_body'] = df['pr_close'] - df['pr_open']
        df['pr_range'] = df['pr_high'] - df['pr_low']
        df['sec_pr_range'] = df['sec_pr_high'] - df['sec_pr_low']
        daily = df.groupby('tradedate').agg({
            'val_net': 'sum', 'vol_net': 'sum', 'trades_net': 'sum',
            'pr_body': 'sum', 'pr_range': 'sum', 'sec_pr_range': 'sum',
            'val_b': 'sum', 'val_s': 'sum', 'vol': 'sum',
        }).reset_index().sort_values('tradedate').reset_index(drop=True)

        pdi, mdi, adx = algopack_dmi(daily, DMI_PERIOD)
        daily['pdi'] = pdi; daily['mdi'] = mdi; daily['adx'] = adx
        daily['force'] = algopack_force(daily, FORCE_PERIOD)
        daily['pdi_prev'] = daily['pdi'].shift(1)
        daily['mdi_prev'] = daily['mdi'].shift(1)
        daily['force_prev'] = daily['force'].shift(1)

        try:
            candles = pd.read_parquet(f'data/candles/{ticker}_D1.parquet')
            candles['begin'] = pd.to_datetime(candles['begin'])
            candles = candles.set_index('begin').sort_index()
        except Exception:
            continue

        for i in range(LOOKBACK, len(daily) - HOLD_DAYS):
            row = daily.iloc[i]; d = row['tradedate']; hist = daily.iloc[:i]
            sigs = {}
            for col in ['val_net', 'vol_net', 'trades_net', 'pr_body', 'sec_pr_range']:
                q80 = hist[col].quantile(0.8); q20 = hist[col].quantile(0.2)
                v = row[col]
                if v > q80: sigs[col] = 'top'
                elif v < q20: sigs[col] = 'bot'
            long_c = sum(1 for v in sigs.values() if v == 'top')
            short_c = sum(1 for v in sigs.values() if v == 'bot')
            alg_dir = 'LONG' if long_c >= 2 else ('SHORT' if short_c >= 2 else None)

            try:
                entry_price = candles.loc[d, 'close']
                exit_date = candles.index[candles.index.get_loc(d) + HOLD_DAYS]
                exit_price = candles.loc[exit_date, 'close']
            except Exception:
                continue

            pdi_cross_up = pd.notna(row['pdi_prev']) and pd.notna(row['mdi_prev']) and row['pdi_prev'] <= row['mdi_prev'] and row['pdi'] > row['mdi']
            mdi_cross_up = pd.notna(row['pdi_prev']) and pd.notna(row['mdi_prev']) and row['mdi_prev'] <= row['pdi_prev'] and row['mdi'] > row['pdi']
            force_cross_up = pd.notna(row['force_prev']) and row['force_prev'] <= 0 and row['force'] > 0
            force_cross_down = pd.notna(row['force_prev']) and row['force_prev'] >= 0 and row['force'] < 0

            # Baseline
            if alg_dir:
                pnl = (exit_price - entry_price) if alg_dir == 'LONG' else (entry_price - exit_price)
                all_rows.append({'ticker': ticker, 'date': d, 'variant': 'base',
                                 'dir': alg_dir, 'pnl': pnl})

            # A: DMI-cross + Force-cross
            if pdi_cross_up and force_cross_up:
                pnl = exit_price - entry_price
                all_rows.append({'ticker': ticker, 'date': d, 'variant': 'A',
                                 'dir': 'LONG', 'pnl': pnl})
            elif mdi_cross_up and force_cross_down:
                pnl = entry_price - exit_price
                all_rows.append({'ticker': ticker, 'date': d, 'variant': 'A',
                                 'dir': 'SHORT', 'pnl': pnl})

            # C: DMI-cross + Force-state
            if pdi_cross_up and pd.notna(row['force']) and row['force'] > 0:
                pnl = exit_price - entry_price
                all_rows.append({'ticker': ticker, 'date': d, 'variant': 'C',
                                 'dir': 'LONG', 'pnl': pnl})
            elif mdi_cross_up and pd.notna(row['force']) and row['force'] < 0:
                pnl = entry_price - exit_price
                all_rows.append({'ticker': ticker, 'date': d, 'variant': 'C',
                                 'dir': 'SHORT', 'pnl': pnl})

    return pd.DataFrame(all_rows)


def metrics(r):
    if len(r) == 0:
        return {'n': 0, 'wr': 0, 'sharpe': 0, 'total': 0}
    sharpe = r['pnl'].mean() / r['pnl'].std() if r['pnl'].std() > 0 else 0
    return {
        'n': len(r),
        'wr': 100 * (r['pnl'] > 0).mean(),
        'sharpe': sharpe,
        'total': r['pnl'].sum(),
    }


def walkforward(df, variant):
    d = df[df['variant'] == variant].sort_values('date').reset_index(drop=True)
    if len(d) < N_FOLDS * 5:
        print(f'{variant}: мало сделок ({len(d)}) для {N_FOLDS} фолдов')
        return
    fold_size = len(d) // N_FOLDS
    print(f'\n===== Walk-forward: {variant} ({len(d)} сделок, {N_FOLDS} фолдов по ~{fold_size}) =====')
    print(f'{"fold":>4} {"train_n":>8} {"train_sharpe":>13} {"test_n":>7} {"test_sharpe":>12} {"test_wr":>8} {"test_pnl":>10}')
    for k in range(N_FOLDS):
        train = d.iloc[: (k + 1) * fold_size] if k < N_FOLDS - 1 else d.iloc[: k * fold_size]
        test = d.iloc[(k + 1) * fold_size: (k + 2) * fold_size] if k < N_FOLDS - 1 else d.iloc[k * fold_size:]
        if len(test) == 0:
            continue
        mt = metrics(train); ms = metrics(test)
        print(f'{k+1:>4} {mt["n"]:>8} {mt["sharpe"]:>13.3f} {ms["n"]:>7} {ms["sharpe"]:>12.3f} {ms["wr"]:>7.1f}% {ms["total"]:>10.0f}')


if __name__ == '__main__':
    print('Сборка событий...')
    df = build_signals()
    print(f'Всего событий: {len(df)}')
    for variant in ['base', 'A', 'C']:
        r = df[df['variant'] == variant]
        m = metrics(r)
        print(f'\n{variant}: n={m["n"]}, WR={m["wr"]:.1f}%, Sharpe={m["sharpe"]:.3f}, Total={m["total"]:.0f}')
    for variant in ['A', 'C']:
        walkforward(df, variant)
