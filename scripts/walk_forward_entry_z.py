#!/usr/bin/env python3
"""walk_forward_entry_z.py — перебор entry_z на 9 enabled-парах (5 фолдов)."""
import json
import pandas as pd
import numpy as np
from pathlib import Path

CANDLES = Path('/root/finlab/data/candles')
CONFIG_FILE = Path('/root/finlab/FinLabPy/My_Indicators/pairs_config.json')

COMMISSION = 0.0028
TIME_EXIT_BARS = 120
WINDOW = 20
N_FOLDS = 5
ENTRY_Z_GRID = [1.5, 2.0, 2.5, 3.0]
EXIT_Z = 0.5


def load_pair(a, b, tf):
    fa = CANDLES / f'{a}_{tf}.parquet'
    fb = CANDLES / f'{b}_{tf}.parquet'
    if not fa.exists() or not fb.exists():
        return None
    da = pd.read_parquet(fa); db = pd.read_parquet(fb)
    _ca = 'begin' if 'begin' in da.columns else 'tradedate'
    _cb = 'begin' if 'begin' in db.columns else 'tradedate'
    a_df = da[[_ca, 'close']].rename(columns={_ca: 'dt'})
    b_df = db[[_cb, 'close']].rename(columns={_cb: 'dt'})
    m = pd.merge(a_df, b_df, on='dt', suffixes=('_a', '_b'))
    m['close_a'] = m['close_a'].apply(lambda x: float(x) if not isinstance(x, bytes) else 0.0)
    m['close_b'] = m['close_b'].apply(lambda x: float(x) if not isinstance(x, bytes) else 0.0)
    m['spread'] = np.log(m['close_a']) - np.log(m['close_b'])
    return m.sort_values('dt').reset_index(drop=True)


def simulate(m, entry_z, exit_z, window=WINDOW):
    m = m.copy()
    m['mean'] = m['spread'].rolling(window).mean()
    m['std'] = m['spread'].rolling(window).std()
    m['z'] = (m['spread'] - m['mean']) / m['std']
    pos = 0; entry_price = 0; entry_i = 0; trades = []
    for i in range(window, len(m)):
        z = m['z'].iloc[i]
        if pd.isna(z): continue
        if pos == 0:
            if z >= entry_z: pos = -1; entry_price = m['spread'].iloc[i]; entry_i = i
            elif z <= -entry_z: pos = 1; entry_price = m['spread'].iloc[i]; entry_i = i
        else:
            if (i - entry_i) >= TIME_EXIT_BARS or abs(z) <= exit_z:
                pnl = (m['spread'].iloc[i] - entry_price) * pos - 2 * COMMISSION
                trades.append(pnl); pos = 0
    return trades


def stats(trades):
    if not trades:
        return {'n': 0, 'pnl': 0, 'wr': 0, 'sharpe': 0, 'avg': 0}
    t = np.array(trades)
    return {
        'n': len(t),
        'pnl': float(t.sum()),
        'wr': float((t > 0).mean()),
        'sharpe': float(t.mean() / t.std() * np.sqrt(252)) if t.std() > 0 else 0,
        'avg': float(t.mean()),
    }


def main():
    cfg = json.loads(CONFIG_FILE.read_text())
    pairs = [(k, v) for k, v in cfg['pairs'].items() if v.get('enabled')]
    print(f'Enabled-пар: {len(pairs)}')
    print(f'Entry_z grid: {ENTRY_Z_GRID}')
    print(f'Фолдов: {N_FOLDS}')
    print()

    results = []
    for pair_name, pcfg in pairs:
        base = pcfg.get('pair_name', pair_name).replace('_M10', '').replace('_H4', '')
        tf = 'M10' if '_M10' in pair_name else 'H4'
        parts = base.split('-')
        if len(parts) != 2:
            print(f'⚠️ {pair_name}: не могу распарсить')
            continue
        a, b = parts
        m = load_pair(a, b, tf)
        if m is None or len(m) < 200:
            print(f'⚠️ {pair_name}: нет данных')
            continue
        for entry_z in ENTRY_Z_GRID:
            fold_size = len(m) // N_FOLDS
            for fold in range(N_FOLDS):
                start = fold * fold_size
                end = start + fold_size if fold < N_FOLDS - 1 else len(m)
                sub = m.iloc[start:end].reset_index(drop=True)
                trades = simulate(sub, entry_z, EXIT_Z)
                s = stats(trades)
                results.append({
                    'pair': pair_name, 'tf': tf, 'entry_z': entry_z,
                    'fold': fold, **s,
                })

    df = pd.DataFrame(results)
    if df.empty:
        print('Нет данных.')
        return

    # Сводка по entry_z
    print('=' * 80)
    print('СВОДКА ПО ENTRY_Z (все пары, все фолды)')
    print('=' * 80)
    summary = df.groupby('entry_z').agg(
        n_trades=('n', 'sum'),
        pnl=('pnl', 'sum'),
        wr=('wr', 'mean'),
        sharpe=('sharpe', 'mean'),
    ).round(4)
    print(summary)
    print()

    # Топ-5 пар по PnL для каждого entry_z
    for entry_z in ENTRY_Z_GRID:
        sub = df[df['entry_z'] == entry_z].groupby('pair').agg(
            n=('n', 'sum'), pnl=('pnl', 'sum'), wr=('wr', 'mean'), sharpe=('sharpe', 'mean')
        ).round(4).sort_values('pnl', ascending=False)
        print(f'--- entry_z={entry_z} (топ-5 по PnL) ---')
        print(sub.head(5))
        print()

    # Сохранить
    out = Path('/root/finlab/logs/walk_forward_entry_z.csv')
    df.to_csv(out, index=False)
    print(f'✅ Сохранено: {out}')


if __name__ == '__main__':
    main()
