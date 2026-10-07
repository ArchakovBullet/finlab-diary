#!/usr/bin/env python3
import pandas as pd
import numpy as np
import glob

TICKERS = ['BR', 'CE', 'CNYRUBF', 'CR', 'ED', 'EURRUBF', 'FF', 'GAZPF',
           'GD', 'GLDRUBF', 'IMOEXF', 'MX', 'OJ', 'PD', 'PT',
           'SBERF', 'SI', 'SV', 'USDRUBF', 'VI', 'W4']

# Типы с направлением
LONG_TYPES = ['vol_b_99_9_pctl', 'vol_b_max', 'net_vol_99_9_pctl+', 'net_vol_max']
SHORT_TYPES = ['vol_s_99_9_pctl', 'vol_s_max', 'net_vol_99_9_pctl-', 'net_vol_min']

HORIZONS = [1, 3, 5, 10]
COMMISSION = 0.0028


def load_candles(ticker):
    try:
        df = pd.read_parquet('data/candles/' + ticker + '_D1.parquet')
        df['begin'] = pd.to_datetime(df['begin']).dt.normalize()
        return df.sort_values('begin').reset_index(drop=True)
    except Exception:
        return None


def build_events():
    all_rows = []
    for ticker in TICKERS:
        candles = load_candles(ticker)
        if candles is None or len(candles) < 20:
            continue
        try:
            f = 'data/mega_alerts/' + ticker + '_alerts.parquet'
            alerts = pd.read_parquet(f)
        except Exception:
            continue
        if 'alert_type' not in alerts.columns:
            continue
        alerts['tradedate'] = pd.to_datetime(alerts['tradedate']).dt.normalize()
        # Только типы с direction
        for atype in LONG_TYPES + SHORT_TYPES:
            sub = alerts[alerts['alert_type'] == atype]
            if len(sub) == 0:
                continue
            direction = 'LONG' if atype in LONG_TYPES else 'SHORT'
            for _, row in sub.iterrows():
                d = row['tradedate']
                # Найти индекс d в candles
                idx = candles[candles['begin'] == d].index
                if len(idx) == 0:
                    continue
                i0 = idx[0]
                entry = float(candles.iloc[i0]['close'])
                for h in HORIZONS:
                    if i0 + h >= len(candles):
                        continue
                    exit_p = float(candles.iloc[i0 + h]['close'])
                    if direction == 'LONG':
                        pnl_gross = (exit_p - entry) / entry * 100
                    else:
                        pnl_gross = (entry - exit_p) / entry * 100
                    pnl_net = pnl_gross - COMMISSION * 100
                    all_rows.append({'ticker': ticker, 'date': d, 'alert_type': atype,
                                     'direction': direction, 'horizon': h, 'pnl': pnl_net})
    return pd.DataFrame(all_rows)


def metrics(r):
    if len(r) == 0:
        return {'n': 0, 'wr': 0, 'sharpe': 0, 'total': 0}
    sharpe = r.mean() / r.std() if r.std() > 0 else 0
    return {'n': len(r), 'wr': 100 * (r > 0).mean(),
            'sharpe': sharpe, 'total': r.sum()}


if __name__ == '__main__':
    df = build_events()
    print('Всего событий:', len(df))
    if len(df) == 0:
        print('Нет данных')
        exit()
    for atype in LONG_TYPES + SHORT_TYPES:
        for h in HORIZONS:
            r = df[(df['alert_type'] == atype) & (df['horizon'] == h)]['pnl']
            if len(r) == 0:
                continue
            m = metrics(r)
            print(atype + ' | h=' + str(h) + ' | n=' + str(m['n']) +
                  ' | WR=' + str(round(m['wr'], 1)) + '%' +
                  ' | Sharpe=' + str(round(m['sharpe'], 3)) +
                  ' | Total=' + str(round(m['total'], 2)))
