#!/usr/bin/env python3
"""
update_combined_betas.py — пересчёт β для combined_v1 (Соколов 2.1.34).
Раз в день. Пишет в pairs_config_test.json -> pairs[name].combined_betas.
Только BANE-BN_M10 (combined_v1=true). Остальные — не трогает.

Read-only для торговли (v4 не трогает), но обновляет конфиг (v4 читает).
"""
import json, os
from pathlib import Path
import numpy as np
import pandas as pd
from statsmodels.tsa.vector_ar.vecm import coint_johansen

ROOT = Path('/root/finlab')
CFG = ROOT / 'FinLabPy' / 'My_Indicators' / 'pairs_config_test.json'
DATA = ROOT / 'data' / 'candles'

# Окно β (в барах). 30 дней M10 ≈ 30*24*6 = 4320 баров. Берём последние 4320.
WINDOW = 4320

def parse_pair(name):
    base, tf = name.rsplit('_', 1)
    a, b = base.split('-', 1)
    return a, b, tf

def load(ticker, tf):
    path = DATA / f'{ticker}_{tf}.parquet'
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_parquet(path)
    cols = {c.lower(): c for c in df.columns}
    if 'begin' not in cols or 'close' not in cols:
        raise ValueError(f'{path}: нет begin/close')
    df = df.rename(columns={cols['begin']: 'begin', cols['close']: 'close'})
    df['begin'] = pd.to_datetime(df['begin'], errors='coerce')
    return df.dropna(subset=['begin','close']).sort_values('begin').reset_index(drop=True)[['begin','close']]

def compute_betas(name):
    a, b, tf = parse_pair(name)
    dA, dB = load(a, tf), load(b, tf)
    m = pd.merge(dA, dB, on='begin', suffixes=('_a','_b')).dropna()
    if len(m) < 200:
        raise ValueError(f'{name}: мало данных ({len(m)})')
    m = m.tail(WINDOW)
    logA = np.log(m['close_a'].replace(0, np.nan)).values
    logB = np.log(m['close_b'].replace(0, np.nan)).values
    mask = ~(np.isnan(logA) | np.isnan(logB))
    logA, logB = logA[mask], logB[mask]
    res = coint_johansen(np.column_stack([logA, logB]), det_order=0, k_ar_diff=1)
    evec = res.evec
    if evec.shape[1] < 2:
        raise ValueError(f'{name}: rank < 2')
    b1 = float(evec[1,0] / evec[0,0])
    b2 = float(evec[1,1] / evec[0,1])
    # проверка ρ (независимость)
    v = logA - b1*logB; w = logA - b2*logB
    rho = float(np.corrcoef(v, w)[0,1])
    return b1, b2, rho

def main():
    cfg = json.load(open(CFG, encoding='utf-8'))
    updated = []
    for name, p in cfg.get('pairs', {}).items():
        if not p.get('combined_v1'):
            continue
        try:
            b1, b2, rho = compute_betas(name)
            p['combined_betas'] = [b1, b2]
            updated.append((name, b1, b2, rho))
            print(f'OK: {name} b1={b1:.4f} b2={b2:.4f} rho={rho:.4f}')
        except Exception as e:
            print(f'ERR: {name} — {e}')
    if updated:
        json.dump(cfg, open(CFG, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print(f'Сохранено: {CFG} ({len(updated)} пар)')
    else:
        print('Нет пар с combined_v1=true')

if __name__ == '__main__':
    main()
