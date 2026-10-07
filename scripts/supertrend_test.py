#!/usr/bin/env python3
import pandas as pd
import numpy as np
import talib

TICKERS = ['BR', 'CE', 'CNYRUBF', 'CR', 'ED', 'EURRUBF', 'FF', 'GAZPF',
           'GD', 'GLDRUBF', 'IMOEXF', 'MX', 'OJ', 'PD', 'PT',
           'SBERF', 'SI', 'SV', 'USDRUBF', 'VI', 'W4']
PERIOD = 14
MULT = 3.0
COMMISSION = 0.0028
N_FOLDS = 5


def supertrend(high, low, close, period=14, mult=3.0):
    atr = talib.ATR(high, low, close, period)
    hl = (high + low) / 2
    upper = hl + mult * atr
    lower = hl - mult * atr
    n = len(close)
    st = np.zeros(n)
    sd = np.zeros(n)
    # Найти первый индекс с не-NaN ATR
    start = 0
    for i in range(n):
        if not np.isnan(atr[i]):
            start = i
            break
    if start == 0:
        return st, sd
    # Инициализация на start: sd = 1, st = lower
    sd[start] = 1
    st[start] = lower[start]
    for i in range(start + 1, n):
        if np.isnan(atr[i]):
            sd[i] = sd[i-1]
            st[i] = st[i-1]
            continue
        # Обновляем upper/lower
        if not np.isnan(upper[i-1]) and (upper[i] < upper[i-1] or close[i-1] > upper[i-1]):
            upper[i] = upper[i]
        else:
            upper[i] = upper[i-1] if not np.isnan(upper[i-1]) else upper[i]
        if not np.isnan(lower[i-1]) and (lower[i] > lower[i-1] or close[i-1] < lower[i-1]):
            lower[i] = lower[i]
        else:
            lower[i] = lower[i-1] if not np.isnan(lower[i-1]) else lower[i]
        # Определяем направление
        if not np.isnan(upper[i-1]) and close[i] > upper[i-1]:
            sd[i] = 1
            st[i] = lower[i]
        elif not np.isnan(lower[i-1]) and close[i] < lower[i-1]:
            sd[i] = -1
            st[i] = upper[i]
        else:
            sd[i] = sd[i-1]
            st[i] = lower[i] if sd[i] == 1 else upper[i]
    return st, sd


def build_trades(ticker):
    try:
        df = pd.read_parquet('data/candles/' + ticker + '_D1.parquet')
        df['begin'] = pd.to_datetime(df['begin'])
        df = df.sort_values('begin').reset_index(drop=True)
    except Exception:
        return []
    if len(df) < PERIOD + 20:
        return []
    st, sd = supertrend(df['high'].values.astype('float64'),
                        df['low'].values.astype('float64'),
                        df['close'].values.astype('float64'),
                        PERIOD, MULT)
    trades = []
    pos = 0
    entry = 0
    entry_dt = None
    for i in range(1, len(df)):
        if sd[i] != sd[i-1] and sd[i] != 0:
            if pos != 0:
                exit_p = df.iloc[i]['close']
                if pos == 1:
                    pnl_gross = (exit_p - entry) / entry * 100
                else:
                    pnl_gross = (entry - exit_p) / entry * 100
                pnl_net = pnl_gross - COMMISSION * 100
                trades.append({'ticker': ticker, 'entry_dt': entry_dt,
                               'exit_dt': df.iloc[i]['begin'],
                               'dir': 'LONG' if pos == 1 else 'SHORT',
                               'pnl': pnl_net})
            pos = int(sd[i])
            entry = df.iloc[i]['close']
            entry_dt = df.iloc[i]['begin']
    return trades


def metrics(r):
    if len(r) == 0:
        return {'n': 0, 'wr': 0, 'sharpe': 0, 'total': 0}
    sharpe = r['pnl'].mean() / r['pnl'].std() if r['pnl'].std() > 0 else 0
    return {'n': len(r), 'wr': 100 * (r['pnl'] > 0).mean(),
            'sharpe': sharpe, 'total': r['pnl'].sum()}


def walkforward(df, n_folds=N_FOLDS):
    if len(df) == 0:
        print('Нет сделок для walk-forward')
        return
    d = df.sort_values('exit_dt').reset_index(drop=True)
    if len(d) < n_folds * 3:
        print('Мало сделок: ' + str(len(d)))
        return
    fold_size = len(d) // n_folds
    print('\n===== Walk-forward (' + str(len(d)) + ' сделок) =====')
    for k in range(n_folds):
        if k < n_folds - 1:
            test = d.iloc[(k + 1) * fold_size: (k + 2) * fold_size]
        else:
            test = d.iloc[k * fold_size:]
        if len(test) == 0:
            continue
        ms = metrics(test)
        print('fold ' + str(k+1) + ': n=' + str(ms['n']) +
              ', WR=' + str(round(ms['wr'], 1)) + '%' +
              ', Sharpe=' + str(round(ms['sharpe'], 3)) +
              ', Total=' + str(round(ms['total'], 2)))


if __name__ == '__main__':
    all_trades = []
    for ticker in TICKERS:
        t = build_trades(ticker)
        all_trades.extend(t)
        if t:
            m = metrics(pd.DataFrame(t))
            print(ticker + ': n=' + str(m['n']) +
                  ', WR=' + str(round(m['wr'], 1)) + '%' +
                  ', Sharpe=' + str(round(m['sharpe'], 3)) +
                  ', Total=' + str(round(m['total'], 2)))
    df = pd.DataFrame(all_trades)
    print('\nВсего сделок: ' + str(len(df)))
    if len(df) > 0:
        m = metrics(df)
        print('Общее: n=' + str(m['n']) +
              ', WR=' + str(round(m['wr'], 1)) + '%' +
              ', Sharpe=' + str(round(m['sharpe'], 3)) +
              ', Total=' + str(round(m['total'], 2)))
    walkforward(df)
