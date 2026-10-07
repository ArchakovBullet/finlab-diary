#!/usr/bin/env python3
"""
Walk-forward для парного робота.
In-sample (70%) → оптимизация entry_z
Out-of-sample (30%) → проверка
С учётом комиссии (0.05%) и проскальзывания.
"""
import json
import pandas as pd
import numpy as np
from pathlib import Path

CANDLES = Path('/root/finlab/data/candles')
CONFIG_FILE = Path('/root/finlab/FinLabPy/My_Indicators/pairs_config.json')

COMMISSION = 0.0028  # 0.28% (0.14% x 2 — из README правило 10)
SLIPPAGE = 0.0002    # 0.02%
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
    # Корреляция (rolling 20)
    m['corr'] = m['close_a'].rolling(20).corr(m['close_b'])
    return m


def simulate(m, entry_z, exit_z, window=20):
    """Симулировать с учётом комиссий и фильтра корреляции."""
    m = m.copy()
    m['mean'] = m['spread'].rolling(window).mean()
    m['std'] = m['spread'].rolling(window).std()
    m['z'] = (m['spread'] - m['mean']) / m['std']

    pos = 0
    entry_price = 0
    pnl_total = 0
    wins = 0
    total = 0

    for i in range(window, len(m)):
        z = m['z'].iloc[i]
        spread = m['spread'].iloc[i]
        corr = m['corr'].iloc[i]

        if pos == 0:
            # Фильтр корреляции
            if pd.isna(corr) or corr < CORR_THRESHOLD:
                continue
            if z >= entry_z:
                pos = -1
                entry_price = spread
            elif z <= -entry_z:
                pos = 1
                entry_price = spread
        else:
            if abs(z) <= exit_z:
                pnl = (spread - entry_price) * pos
                # Комиссия (2 сделки: вход + выход)
                pnl -= 2 * (COMMISSION + SLIPPAGE)
                pnl_total += pnl
                total += 1
                if pnl > 0:
                    wins += 1
                pos = 0
    return pnl_total, wins, total


def main():
    with open(CONFIG_FILE) as f:
        cfg = json.load(f)

    pairs = cfg.get('pairs', {})
    enabled = [(k, v) for k, v in pairs.items() if v.get('enabled')]

    print(f'Всего enabled пар: {len(enabled)}')
    print(f'Комиссия: {COMMISSION*100:.2f}% + slippage {SLIPPAGE*100:.2f}%')
    print(f'Фильтр корреляции: > {CORR_THRESHOLD}')
    print()
    print(f'{"pair":<18} {"tf":<4} {"in_wr":>6} {"in_pnl":>8} {"out_wr":>7} {"out_pnl":>9} {"best_z":>7} {"verdict":>10}')
    print('-' * 80)

    results = []
    for pair_name, pair_data in enabled[:40]:
        base = pair_name.split('_')[0]
        if '-' not in base:
            continue
        ta, tb = base.split('-')
        tf = pair_name.split('_')[1] if '_' in pair_name else 'M10'

        m = load_pair(ta, tb, tf)
        if m is None or len(m) < 100:
            continue

        split = int(len(m) * 0.7)
        in_sample = m.iloc[:split]
        out_sample = m.iloc[split:]

        best_z = None
        best_pnl = -float('inf')
        for entry_z in [1.5, 2.0, 2.5, 3.0]:
            pnl, wins, total = simulate(in_sample, entry_z, 0.5)
            if pnl > best_pnl:
                best_pnl = pnl
                best_z = entry_z

        if best_z is None:
            continue

        in_pnl, in_wins, in_total = simulate(in_sample, best_z, 0.5)
        out_pnl, out_wins, out_total = simulate(out_sample, best_z, 0.5)

        in_wr = 100 * in_wins / in_total if in_total > 0 else 0
        out_wr = 100 * out_wins / out_total if out_total > 0 else 0

        verdict = '✅ OK' if out_pnl > 0 else '❌ FAIL'

        print(f'{pair_name:<18} {tf:<4} {in_wr:>6.1f} {in_pnl:>8.3f} {out_wr:>7.1f} {out_pnl:>9.3f} {best_z:>7.1f} {verdict:>10}')
        results.append((pair_name, best_z, in_wr, out_wr, out_pnl, verdict))

    print()
    ok_cnt = sum(1 for *_, v in results if 'OK' in v)
    fail_cnt = sum(1 for *_, v in results if 'FAIL' in v)
    print(f'OK: {ok_cnt}, FAIL: {fail_cnt}')

    # Распределение entry_z
    print()
    print('=== Распределение entry_z (оптимум) ===')
    from collections import Counter
    z_counts = Counter(z for _, z, *_ in results)
    for z, cnt in sorted(z_counts.items()):
        print(f'  entry_z={z}: {cnt} пар')


if __name__ == '__main__':
    main()
