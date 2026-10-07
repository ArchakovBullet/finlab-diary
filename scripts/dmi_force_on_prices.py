#!/usr/bin/env python3
"""
dmi_force_on_prices.py — DMI-cross + Force-cross НА ЦЕНАХ (не Algopack).

DMI: high/low/close из data/candles/{ticker}_D1.parquet.
Force: volume × (close − prev_close), из тех же свечей.

Baseline: TradeStats (val_net, vol_net, trades_net, pr_body, sec_pr_range).

Сравниваем:
- baseline (TradeStats)
- A: DMI-cross + Force-cross (на ценах)
- C: DMI-cross + Force-state (на ценах)
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
    """DMI на ценах (high/low/close)."""
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
    """Force Index: volume × (close − prev_close)."""
    fi = df['volume'] * df['close'].diff()
    return fi.ewm(span=period, adjust=False).mean()


def build_events():
    all_rows = []
    for ticker in TICKERS:
        # Цены
        try:
            candles = pd.read_parquet(f'data/candles/{ticker}_D1.parquet')
            candles['begin'] = pd.to_datetime(candles['begin'])
            candles = candles.sort_values('begin').reset_index(drop=True)
        except Exception:
            continue
        if len(candles) < LOOKBACK + HOLD_DAYS + 30:
            continue

        # DMI/Force на ценах
        pdi, mdi, adx = calc_dmi_on_prices(candles, DMI_PERIOD)
        candles['pdi'] = pdi
        candles['mdi'] = mdi
        candles['adx'] = adx
        candles['force'] = calc_force_on_prices(candles, FORCE_PERIOD)
        candles['pdi_prev'] = candles['pdi'].shift(1)
        candles['mdi_prev'] = candles['mdi'].shift(1)

        # Baseline — TradeStats
        try:
            ts = pd.read_parquet(f'data/tradestats/{ticker}_tradestats.parquet')
            ts['tradedate'] = pd.to_datetime(ts['tradedate'])
            ts['val_net'] = ts['val_b'] - ts['val_s']
            ts['vol_net'] = ts['vol_b'] - ts['vol_s']
            ts['trades_net'] = ts['trades_b'] - ts['trades_s']
            ts['pr_body'] = ts['pr_close'] - ts['pr_open']
            ts['sec_pr_range'] = ts['sec_pr_high'] - ts['sec_pr_low']
            daily = ts.groupby('tradedate').agg({
                'val_net': 'sum', 'vol_net': 'sum', 'trades_net': 'sum',
                'pr_body': 'sum', 'sec_pr_range': 'sum',
            }).reset_index().sort_values('tradedate').reset_index(drop=True)
        except Exception:
            continue

        # Объединяем по tradedate
        m = candles.merge(daily, left_on='begin', right_on='tradedate', how='inner')
        m = m.sort_values('begin').reset_index(drop=True)
        if len(m) < LOOKBACK + HOLD_DAYS + 30:
            continue

        for i in range(LOOKBACK, len(m) - HOLD_DAYS):
            row = m.iloc[i]
            hist = m.iloc[:i]
            d = row['begin']

            # Baseline сигнал
            sigs = {}
            for col in ['val_net', 'vol_net', 'trades_net', 'pr_body', 'sec_pr_range']:
                q80 = hist[col].quantile(0.8)
                q20 = hist[col].quantile(0.2)
                v = row[col]
                if v > q80: sigs[col] = 'top'
                elif v < q20: sigs[col] = 'bot'
            long_c = sum(1 for v in sigs.values() if v == 'top')
            short_c = sum(1 for v in sigs.values() if v == 'bot')
            alg_dir = 'LONG' if long_c >= 2 else ('SHORT' if short_c >= 2 else None)

            entry = row['close']
            exit_price = m.iloc[i + HOLD_DAYS]['close']

            # Baseline
            if alg_dir:
                pnl = (exit_price - entry) if alg_dir == 'LONG' else (entry - exit_price)
                all_rows.append({'ticker': ticker, 'date': d, 'variant': 'base',
                                 'dir': alg_dir, 'pnl': pnl})

            # DMI-cross, Force-cross (на ценах)
            pdi_cross_up = pd.notna(row['pdi_prev']) and pd.notna(row['mdi_prev']) \
                and row['pdi_prev'] <= row['mdi_prev'] and row['pdi'] > row['mdi']
            mdi_cross_up = pd.notna(row['pdi_prev']) and pd.notna(row['mdi_prev']) \
                and row['mdi_prev'] <= row['pdi_prev'] and row['mdi'] > row['pdi']
            force_cross_up = pd.notna(row['force']) and row['force'] > 0 and \
                (row['force'] - hist['force'].iloc[-1]) > 0  # приблизительно
            # A: DMI-cross + Force-state (на ценах)
            if pdi_cross_up and pd.notna(row['force']) and row['force'] > 0:
                pnl = exit_price - entry
                all_rows.append({'ticker': ticker, 'date': d, 'variant': 'A_prices',
                                 'dir': 'LONG', 'pnl': pnl})
            elif mdi_cross_up and pd.notna(row['force']) and row['force'] < 0:
                pnl = entry - exit_price
                all_rows.append({'ticker': ticker, 'date': d, 'variant': 'A_prices',
                                 'dir': 'SHORT', 'pnl': pnl})

    return pd.DataFrame(all_rows)


def metrics(r):
    if len(r) == 0:
        return {'n': 0, 'wr': 0, 'sharpe': 0, 'total': 0}
    sharpe = r['pnl'].mean() / r['pnl'].std() if r['pnl'].std() > 0 else 0
    return {'n': len(r), 'wr': 100 * (r['pnl'] > 0).mean(),
            'sharpe': sharpe, 'total': r['pnl'].sum()}


if __name__ == '__main__':
    print('Сборка событий (DMI/Force на ценах)...')
    df = build_events()
    print(f'Всего событий: {len(df)}')
    for variant in ['base', 'A_prices']:
        r = df[df['variant'] == variant]
        m = metrics(r)
        print(f'\n{variant}: n={m["n"]}, WR={m["wr"]:.1f}%, Sharpe={m["sharpe"]:.3f}, Total={m["total"]:.0f}')
