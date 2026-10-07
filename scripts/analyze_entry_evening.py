#!/usr/bin/env python3
"""
analyze_entry_evening.py — вход вечером (21:30) vs утром (10:00).

Для baseline-событий (n≈468):
- V_evening: вход по M10 close 21:30 того же дня
- V_morning: вход по M10 close 10:00 следующего дня (proxy через open D1)
- V_close: вход по close D1

Выход — через 5 дней, по close D1.
"""
import pandas as pd

TICKERS = ['BR', 'CE', 'CNYRUBF', 'CR', 'ED', 'EURRUBF', 'FF', 'GAZPF',
           'GD', 'GLDRUBF', 'IMOEXF', 'MX', 'OJ', 'PD', 'PT',
           'SBERF', 'SI', 'SV', 'USDRUBF', 'VI', 'W4']
HOLD_DAYS = 5
LOOKBACK = 60


def load_m10(ticker):
    try:
        df = pd.read_parquet(f'data/candles/{ticker}_M10.parquet')
        df['begin'] = pd.to_datetime(df['begin'])
        return df.sort_values('begin').reset_index(drop=True)
    except Exception:
        return None


def build():
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

        m10 = load_m10(ticker)
        if m10 is None:
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
                # V_close: close D1 сигнального дня
                close_signal = candles.loc[d, 'close']
                exit_date = candles.index[candles.index.get_loc(d) + HOLD_DAYS]
                exit_p = candles.loc[exit_date, 'close']

                # V_evening: M10 close в 21:30 того же дня
                m10_day = m10[(m10['begin'].dt.date == d.date()) if hasattr(d, 'date') else True]

                # Найти M10 в 21:30
                m10_evening = m10[(m10['begin'].dt.normalize() == d) & (m10['begin'].dt.hour == 21) & (m10['begin'].dt.minute == 30)]
                if len(m10_evening) == 0:
                    continue
                entry_evening = float(m10_evening.iloc[0]['close'])

                # V_morning: M10 close 10:00 следующего дня
                next_d = candles.index[candles.index.get_loc(d) + 1]
                m10_morning = m10[(m10['begin'].dt.normalize() == next_d) & (m10['begin'].dt.hour == 10) & (m10['begin'].dt.minute == 0)]
                if len(m10_morning) == 0:
                    continue
                entry_morning = float(m10_morning.iloc[0]['close'])

                # PnL для LONG/SHORT
                if alg_dir == 'LONG':
                    pnl_close = exit_p - close_signal
                    pnl_evening = exit_p - entry_evening
                    pnl_morning = exit_p - entry_morning
                else:
                    pnl_close = close_signal - exit_p
                    pnl_evening = entry_evening - exit_p
                    pnl_morning = entry_morning - exit_p

                all_rows.append({'ticker': ticker, 'date': d, 'variant': 'V_close', 'pnl': pnl_close})
                all_rows.append({'ticker': ticker, 'date': d, 'variant': 'V_evening', 'pnl': pnl_evening})
                all_rows.append({'ticker': ticker, 'date': d, 'variant': 'V_morning', 'pnl': pnl_morning})
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
    print('Сборка событий...')
    df = build()
    print(f'Всего событий: {len(df)}')
    for variant in ['V_close', 'V_evening', 'V_morning']:
        r = df[df['variant'] == variant]
        m = metrics(r)
        print(f'{variant:12s} | n={m["n"]:4d} | WR={m["wr"]:5.1f}% | Sharpe={m["sharpe"]:.3f} | Total={m["total"]:.0f}')
