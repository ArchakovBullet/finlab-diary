#!/usr/bin/env python3
"""
analyze_entry_variants.py — сравнение вариантов входа.

Для baseline-событий (n≈480) сравниваем:
- V0: реальный вход (M10 close 10:00)
- V1: вход по close сигнального дня
- V2: вход по откату на 0.5% от close сигнала (лимит)
- V3: вход по откату на 1.0%
- V4: вход по close + фильтр gap < 0.5%
- V5: вход по close + фильтр gap < 1.0%

Считаем WR, Sharpe, Total.
"""
import pandas as pd
import numpy as np

TICKERS = ['BR', 'CE', 'CNYRUBF', 'CR', 'ED', 'EURRUBF', 'FF', 'GAZPF',
           'GD', 'GLDRUBF', 'IMOEXF', 'MX', 'OJ', 'PD', 'PT',
           'SBERF', 'SI', 'SV', 'USDRUBF', 'VI', 'W4']
HOLD_DAYS = 5
LOOKBACK = 60


def build_baseline():
    all_rows = []
    for ticker in TICKERS:
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

        try:
            candles = pd.read_parquet(f'data/candles/{ticker}_D1.parquet')
            candles['begin'] = pd.to_datetime(candles['begin'])
            candles = candles.set_index('begin').sort_index()
        except Exception:
            continue

        for i in range(LOOKBACK, len(daily) - HOLD_DAYS):
            row = daily.iloc[i]
            d = row['tradedate']
            hist = daily.iloc[:i]
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
            if not alg_dir:
                continue

            try:
                signal_close = candles.loc[d, 'close']
                # V1: вход по close сигнала
                exit_date_sig = candles.index[candles.index.get_loc(d) + HOLD_DAYS]
                exit_sig = candles.loc[exit_date_sig, 'close']
                pnl_v1 = (exit_sig - signal_close) if alg_dir == 'LONG' else (signal_close - exit_sig)

                # V0: реальный вход (M10 10:00 следующего дня) — приближение по D1 open
                next_date = candles.index[candles.index.get_loc(d) + 1]
                next_open = candles.loc[next_date, 'open']
                # next_open — приближение M10 10:00 (M10 недоступен в D1, но это proxy)
                exit_date_v0 = candles.index[candles.index.get_loc(next_date) + HOLD_DAYS]
                exit_v0 = candles.loc[exit_date_v0, 'close']
                pnl_v0 = (exit_v0 - next_open) if alg_dir == 'LONG' else (next_open - exit_v0)

                # V2/V3: вход по откату (лимит) — если цена откатится
                # LONG: лимит на close_signal * (1 - X)
                # SHORT: лимит на close_signal * (1 + X)
                # Если next day low <= лимит — сработал, иначе — пропуск (по market at next_open)
                next_low = candles.loc[next_date, 'low']
                next_high = candles.loc[next_date, 'high']

                for x, label in [(0.005, 'V2_rollback_0.5'), (0.01, 'V3_rollback_1.0')]:
                    if alg_dir == 'LONG':
                        limit = signal_close * (1 - x)
                        if next_low <= limit:
                            entry_rb = limit
                            pnl_rb = exit_v0 - entry_rb
                        else:
                            continue
                    else:
                        limit = signal_close * (1 + x)
                        if next_high >= limit:
                            entry_rb = limit
                            pnl_rb = entry_rb - exit_v0
                        else:
                            continue
                    all_rows.append({'ticker': ticker, 'date': d, 'variant': label,
                                     'dir': alg_dir, 'pnl': pnl_rb})

                # V4/V5: фильтр gap (вход только если open недалеко от close)
                gap_pct = (next_open - signal_close) / signal_close * 100
                if alg_dir == 'LONG' and gap_pct < 0.5:
                    all_rows.append({'ticker': ticker, 'date': d, 'variant': 'V4_gap_lt_0.5',
                                     'dir': alg_dir, 'pnl': pnl_v0})
                if alg_dir == 'LONG' and gap_pct < 1.0:
                    all_rows.append({'ticker': ticker, 'date': d, 'variant': 'V5_gap_lt_1.0',
                                     'dir': alg_dir, 'pnl': pnl_v0})

                all_rows.append({'ticker': ticker, 'date': d, 'variant': 'V0_real',
                                 'dir': alg_dir, 'pnl': pnl_v0})
                all_rows.append({'ticker': ticker, 'date': d, 'variant': 'V1_close',
                                 'dir': alg_dir, 'pnl': pnl_v1})
            except Exception:
                continue

    return pd.DataFrame(all_rows)


def metrics(r):
    if len(r) == 0:
        return {'n': 0, 'wr': 0, 'sharpe': 0, 'total': 0}
    sharpe = r['pnl'].mean() / r['pnl'].std() if r['pnl'].std() > 0 else 0
    return {'n': len(r), 'wr': 100 * (r['pnl'] > 0).mean(),
            'sharpe': sharpe, 'total': r['pnl'].sum()}


if __name__ == '__main__':
    print('Сборка baseline-событий...')
    df = build_baseline()
    print(f'Всего событий: {len(df)}')
    for variant in ['V0_real', 'V1_close', 'V2_rollback_0.5', 'V3_rollback_1.0',
                    'V4_gap_lt_0.5', 'V5_gap_lt_1.0']:
        r = df[df['variant'] == variant]
        m = metrics(r)
        print(f'{variant:25s} | n={m["n"]:4d} | WR={m["wr"]:5.1f}% | Sharpe={m["sharpe"]:.3f} | Total={m["total"]:.0f}')
