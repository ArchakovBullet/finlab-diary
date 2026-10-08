#!/usr/bin/env python3
"""
walk_forward_pairs_algopack.py — walk-forward пар с Algopack-фильтром.

Сравниваем:
- БЕЗ фильтра (базовый z-score)
- С фильтром (Algopack disb подтверждает направление)
"""
import json
import pandas as pd
import numpy as np
from pathlib import Path

CANDLES = Path('/root/finlab/data/candles')
TRADESTATS = Path('/root/finlab/data/tradestats')
CONFIG_FILE = Path('/root/finlab/FinLabPy/My_Indicators/pairs_config.json')

COMMISSION = 0.0028
CORR_THRESHOLD = 0.7


def load_pair(ticker_a, ticker_b, tf):
    fa = CANDLES / f'{ticker_a}_{tf}.parquet'
    fb = CANDLES / f'{ticker_b}_{tf}.parquet'
    if not fa.exists() or not fb.exists():
        return None
    df_a = pd.read_parquet(fa)
    df_b = pd.read_parquet(fb)
    _ca = 'begin' if 'begin' in df_a.columns else 'tradedate'
    _cb = 'begin' if 'begin' in df_b.columns else 'tradedate'
    a = df_a[[_ca, 'close']].rename(columns={_ca: 'dt'})
    b = df_b[[_cb, 'close']].rename(columns={_cb: 'dt'})
    m = pd.merge(a, b, on='dt', suffixes=('_a', '_b'))
    m['close_a'] = m['close_a'].apply(lambda x: float(x) if not isinstance(x, bytes) else 0.0)
    m['close_b'] = m['close_b'].apply(lambda x: float(x) if not isinstance(x, bytes) else 0.0)
    m['spread'] = np.log(m['close_a']) - np.log(m['close_b'])
    m['corr'] = m['close_a'].rolling(20).corr(m['close_b'])
    return m.sort_values('dt').reset_index(drop=True)


def get_algopack_disb(ticker, dt):
    """Algopack disb для ticker в момент dt (последний доступный)."""
    f = TRADESTATS / f'{ticker}_tradestats.parquet'
    if not f.exists():
        return 0.0
    try:
        df = pd.read_parquet(f)
        df['tradedate'] = pd.to_datetime(df['tradedate'])
        # Берём последний день <= dt
        df = df[df['tradedate'] <= dt]
        if len(df) == 0:
            return 0.0
        last_date = df['tradedate'].max()
        last = df[df['tradedate'] == last_date]
        return float(last['disb'].mean()) if 'disb' in last.columns else 0.0
    except Exception:
        return 0.0


def simulate(m, entry_z, exit_z, window=20, use_algopack=False, ticker_a='', ticker_b=''):
    m = m.copy()
    m['mean'] = m['spread'].rolling(window).mean()
    m['std'] = m['spread'].rolling(window).std()
    m['z'] = (m['spread'] - m['mean']) / m['std']

    pos = 0
    entry_price = 0
    entry_dt = None
    pnl_total = 0
    trades = []

    for i in range(window, len(m)):
        row = m.iloc[i]
        z = row['z']
        if pd.isna(z):
            continue

        # Algopack фильтр
        alg_ok_long = True
        alg_ok_short = True
        if use_algopack:
            disb_a = get_algopack_disb(ticker_a, row['dt'])
            disb_b = get_algopack_disb(ticker_b, row['dt'])
            # LONG_SPREAD = BUY a + SELL b
            # disb_a > 0 (покупки), disb_b < 0 (продажи)
            alg_ok_long = (disb_a > -0.3) and (disb_b < 0.3)
            # SHORT_SPREAD = SELL a + BUY b
            alg_ok_short = (disb_a < 0.3) and (disb_b > -0.3)

        if pos == 0:
            if z >= entry_z and (not use_algopack or alg_ok_short):
                pos = -1  # SHORT_SPREAD
                entry_price = row['spread']
                entry_dt = row['dt']
            elif z <= -entry_z and (not use_algopack or alg_ok_long):
                pos = 1  # LONG_SPREAD
                entry_price = row['spread']
                entry_dt = row['dt']
        elif pos != 0:
            if abs(z) <= exit_z:
                exit_price = row['spread']
                pnl_gross = (exit_price - entry_price) * pos
                pnl_net = pnl_gross - 2 * COMMISSION  # две ноги
                trades.append({'pnl': pnl_net, 'entry_dt': entry_dt, 'exit_dt': row['dt']})
                pnl_total += pnl_net
                pos = 0

    return trades, pnl_total


def metrics(trades):
    if len(trades) == 0:
        return {'n': 0, 'wr': 0, 'sharpe': 0, 'total': 0}
    r = pd.DataFrame(trades)['pnl']
    sharpe = r.mean() / r.std() if r.std() > 0 else 0
    return {'n': len(r), 'wr': 100 * (r > 0).mean(), 'sharpe': sharpe, 'total': r.sum()}


if __name__ == '__main__':
    with open(CONFIG_FILE) as f:
        cfg = json.load(f)
    pairs = cfg.get('pairs', cfg)

    active = [(n, p) for n, p in pairs.items() if isinstance(p, dict) and p.get('enabled')]
    print(f'Активных пар: {len(active)}\n')

    results = []
    for pair_name, pair_data in active:
        base_pair = pair_name.rsplit('_', 1)[0]
        tf = pair_name.rsplit('_', 1)[1]
        if '-' not in base_pair:
            continue
        ta, tb = base_pair.split('-')
        m = load_pair(ta, tb, tf)
        if m is None or len(m) < 100:
            continue
        entry_z = pair_data.get('best_params', {}).get('entry_z', 3.0)
        exit_z = pair_data.get('best_params', {}).get('exit_z', 0.5)

        # Без фильтра
        t1, _ = simulate(m, entry_z, exit_z, use_algopack=False)
        met1 = metrics(t1)

        # С фильтром
        t2, _ = simulate(m, entry_z, exit_z, use_algopack=True, ticker_a=ta, ticker_b=tb)
        met2 = metrics(t2)

        results.append({
            'pair': pair_name, 'tf': tf,
            'base_n': met1['n'], 'base_wr': met1['wr'], 'base_sharpe': met1['sharpe'],
            'alg_n': met2['n'], 'alg_wr': met2['wr'], 'alg_sharpe': met2['sharpe'],
        })

    df = pd.DataFrame(results)
    if len(df) == 0:
        print('Нет результатов')
    else:
        print(f'{"pair":<20} {"tf":<5} {"base_n":>7} {"base_wr":>8} {"base_sharpe":>12} {"alg_n":>7} {"alg_wr":>8} {"alg_sharpe":>12}')
        print('-' * 90)
        for _, r in df.iterrows():
            print(f'{r["pair"]:<20} {r["tf"]:<5} {r["base_n"]:>7} {r["base_wr"]:>7.1f}% {r["base_sharpe"]:>12.3f} {r["alg_n"]:>7} {r["alg_wr"]:>7.1f}% {r["alg_sharpe"]:>12.3f}')

        # Сводка
        print(f'\nСредний Sharpe (без фильтра): {df["base_sharpe"].mean():.3f}')
        print(f'Средний Sharpe (с фильтром): {df["alg_sharpe"].mean():.3f}')
        print(f'Пар, где фильтр улучшил Sharpe: {(df["alg_sharpe"] > df["base_sharpe"]).sum()}/{len(df)}')
