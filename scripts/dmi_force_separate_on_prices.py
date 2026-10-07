#!/usr/bin/env python3
"""
dmi_force_separate_on_prices.py — тест DMI-cross и Force-cross ОТДЕЛЬНО.

Варианты:
  DMI_long: +DI cross up -DI → LONG
  DMI_short: -DI cross up +DI → SHORT
  Force_long: Force cross up 0 → LONG
  Force_short: Force cross down 0 → SHORT
  DMI_LS: DMI cross (LONG и SHORT как отдельные сигналы)
  Force_LS: Force cross (LONG и SHORT как отдельные сигналы)

Всё — на ЦЕНАХ (data/candles/{ticker}_D1.parquet).
"""
import pandas as pd
import numpy as np

TICKERS = ['BR', 'CE', 'CNYRUBF', 'CR', 'ED', 'EURRUBF', 'FF', 'GAZPF',
           'GD', 'GLDRUBF', 'IMOEXF', 'MX', 'OJ', 'PD', 'PT',
           'SBERF', 'SI', 'SV', 'USDRUBF', 'VI', 'W4']
HOLD_DAYS = 5
LOOKBACK = 60
DMI_PERIOD = 14
FORCE_PERIOD = 13


def calc_dmi_on_prices(df, period=14):
    high = df['high']; low = df['low']; close = df['close']
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    plus_dm[plus_dm < minus_dm] = 0
    minus_dm[minus_dm < plus_dm] = 0
    tr = pd.concat([high - low,
                    (high - close.shift()).abs(),
                    (low - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx = dx.rolling(period).mean()
    return plus_di, minus_di, adx


def calc_force_on_prices(df, period=13):
    fi = df['volume'] * df['close'].diff()
    return fi.ewm(span=period, adjust=False).mean()


def build_events():
    all_rows = []
    for ticker in TICKERS:
        try:
            df = pd.read_parquet(f'data/candles/{ticker}_D1.parquet')
            df['begin'] = pd.to_datetime(df['begin'])
            df = df.sort_values('begin').reset_index(drop=True)
        except Exception:
            continue
        if len(df) < LOOKBACK + HOLD_DAYS + 30:
            continue

        pdi, mdi, adx = calc_dmi_on_prices(df, DMI_PERIOD)
        df['pdi'] = pdi
        df['mdi'] = mdi
        df['adx'] = adx
        df['force'] = calc_force_on_prices(df, FORCE_PERIOD)
        df['pdi_prev'] = df['pdi'].shift(1)
        df['mdi_prev'] = df['mdi'].shift(1)
        df['force_prev'] = df['force'].shift(1)

        for i in range(LOOKBACK, len(df) - HOLD_DAYS):
            row = df.iloc[i]
            d = row['begin']
            entry = row['close']
            exit_price = df.iloc[i + HOLD_DAYS]['close']

            pdi_cross_up = pd.notna(row['pdi_prev']) and pd.notna(row['mdi_prev']) \
                and row['pdi_prev'] <= row['mdi_prev'] and row['pdi'] > row['mdi']
            mdi_cross_up = pd.notna(row['pdi_prev']) and pd.notna(row['mdi_prev']) \
                and row['mdi_prev'] <= row['pdi_prev'] and row['mdi'] > row['pdi']

            force_cross_up = pd.notna(row['force_prev']) and row['force_prev'] <= 0 and row['force'] > 0
            force_cross_down = pd.notna(row['force_prev']) and row['force_prev'] >= 0 and row['force'] < 0

            # DMI-cross → LONG
            if pdi_cross_up:
                pnl = exit_price - entry
                all_rows.append({'ticker': ticker, 'date': d, 'variant': 'DMI_LONG',
                                 'pnl': pnl})
            # DMI-cross → SHORT
            if mdi_cross_up:
                pnl = entry - exit_price
                all_rows.append({'ticker': ticker, 'date': d, 'variant': 'DMI_SHORT',
                                 'pnl': pnl})

            # Force-cross → LONG
            if force_cross_up:
                pnl = exit_price - entry
                all_rows.append({'ticker': ticker, 'date': d, 'variant': 'Force_LONG',
                                 'pnl': pnl})
            # Force-cross → SHORT
            if force_cross_down:
                pnl = entry - exit_price
                all_rows.append({'ticker': ticker, 'date': d, 'variant': 'Force_SHORT',
                                 'pnl': pnl})

    return pd.DataFrame(all_rows)


def metrics(r):
    if len(r) == 0:
        return {'n': 0, 'wr': 0, 'sharpe': 0, 'total': 0}
    sharpe = r['pnl'].mean() / r['pnl'].std() if r['pnl'].std() > 0 else 0
    return {'n': len(r), 'wr': 100 * (r['pnl'] > 0).mean(),
            'sharpe': sharpe, 'total': r['pnl'].sum()}


def walkforward(df, variant, n_folds=5):
    d = df[df['variant'] == variant].sort_values('date').reset_index(drop=True)
    if len(d) < n_folds * 5:
        print(f'{variant}: мало сделок ({len(d)})')
        return
    fold_size = len(d) // n_folds
    print(f'\n===== {variant} ({len(d)} сделок, {n_folds} фолдов) =====')
    print(f'{"fold":>4} {"test_n":>7} {"test_sharpe":>12} {"test_wr":>8} {"test_pnl":>10}')
    for k in range(n_folds):
        test = d.iloc[(k + 1) * fold_size: (k + 2) * fold_size] if k < n_folds - 1 else d.iloc[k * fold_size:]
        if len(test) == 0:
            continue
        ms = metrics(test)
        print(f'{k+1:>4} {ms["n"]:>7} {ms["sharpe"]:>12.3f} {ms["wr"]:>7.1f}% {ms["total"]:>10.0f}')


if __name__ == '__main__':
    print('Сборка событий (DMI-cross и Force-cross отдельно, на ценах)...')
    df = build_events()
    print(f'Всего событий: {len(df)}')
    for variant in ['DMI_LONG', 'DMI_SHORT', 'Force_LONG', 'Force_SHORT']:
        r = df[df['variant'] == variant]
        m = metrics(r)
        print(f'\n{variant}: n={m["n"]}, WR={m["wr"]:.1f}%, Sharpe={m["sharpe"]:.3f}, Total={m["total"]:.0f}')
    # Walk-forward для каждого варианта
    for variant in ['DMI_LONG', 'DMI_SHORT', 'Force_LONG', 'Force_SHORT']:
        walkforward(df, variant)
