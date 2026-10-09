#!/usr/bin/env python3
"""train_ml_models.py — обучает Logistic Regression для ML-фильтра пар.

Читает per-pair параметры из config.
Сохраняет pickle в models/lr_{pair_name}.pkl.

Фичи: z, std, corr, spread_trend, beta (как в calculate_zscore робота).
Target: PnL следующей сделки > 0.
"""
import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score

ROOT = Path('/root/finlab')
CANDLES = ROOT / 'data' / 'candles'
MODELS_DIR = ROOT / 'models'
CONFIG_PATH = ROOT / 'FinLabPy' / 'My_Indicators' / 'pairs_config.json'

COMMISSION = 0.0028
TIME_EXIT_BARS = 120

# 3 пары с AUC > 0.6 (per-pair параметры)
ML_PAIRS = [
    ('GD', 'PT', 'H4'),
    ('BELU', 'NB', 'M10'),
    ('SFIN', 'SH', 'M10'),
]


def load_pair(a, b, tf):
    fa = CANDLES / f'{a}_{tf}.parquet'
    fb = CANDLES / f'{b}_{tf}.parquet'
    if not fa.exists() or not fb.exists():
        return None
    da = pd.read_parquet(fa); db = pd.read_parquet(fb)
    col_a = 'begin' if 'begin' in da.columns else 'tradedate'
    col_b = 'begin' if 'begin' in db.columns else 'tradedate'
    a_df = da[[col_a, 'close']].rename(columns={col_a: 'dt'})
    b_df = db[[col_b, 'close']].rename(columns={col_b: 'dt'})
    m = pd.merge(a_df, b_df, on='dt', suffixes=('_a', '_b')).sort_values('dt').reset_index(drop=True)
    m['close_a'] = m['close_a'].apply(lambda x: float(x) if not isinstance(x, bytes) else 0.0)
    m['close_b'] = m['close_b'].apply(lambda x: float(x) if not isinstance(x, bytes) else 0.0)
    m['log_a'] = np.log(m['close_a'].replace(0, np.nan))
    m['log_b'] = np.log(m['close_b'].replace(0, np.nan))
    return m


def build_features(m, window=30, resid_window=60):
    from statsmodels.regression.linear_model import OLS
    from statsmodels.tools import add_constant
    m = m.copy()
    resid = []; betas = []
    for i in range(len(m)):
        if i < resid_window:
            resid.append(np.nan); betas.append(np.nan); continue
        y = m['log_a'].iloc[i-resid_window:i].values
        x = add_constant(m['log_b'].iloc[i-resid_window:i].values)
        try:
            model = OLS(y, x).fit()
            beta = model.params[1]; alpha = model.params[0]
            r = m['log_a'].iloc[i] - beta * m['log_b'].iloc[i] - alpha
            resid.append(r); betas.append(beta)
        except Exception:
            resid.append(np.nan); betas.append(np.nan)
    m['resid'] = resid
    m['beta'] = betas
    m['mean'] = m['resid'].rolling(window).mean()
    m['std'] = m['resid'].rolling(window).std()
    m['z'] = (m['resid'] - m['mean']) / m['std']
    m['corr'] = m['close_a'].rolling(50).corr(m['close_b'])
    m['spread_trend'] = m['z'] - m['z'].shift(1)

    m['future_pnl'] = 0.0
    for i in range(window + resid_window, len(m) - TIME_EXIT_BARS):
        z = m['z'].iloc[i]
        if pd.isna(z): continue
        if z >= 2.5:
            pos = -1
        elif z <= -2.5:
            pos = 1
        else:
            continue
        entry = m['resid'].iloc[i]
        exit_i = min(i + TIME_EXIT_BARS, len(m) - 1)
        for j in range(i+1, exit_i+1):
            if abs(m['z'].iloc[j]) <= 0.5:
                exit_i = j
                break
        exit_price = m['resid'].iloc[exit_i]
        pnl = (exit_price - entry) * pos - 2 * COMMISSION
        m.loc[i, 'future_pnl'] = pnl

    m['target'] = (m['future_pnl'] > 0).astype(int)
    return m


def train_one(a, b, tf, config_pairs):
    """Обучить LR для одной пары. Возвращает dict или None."""
    pair_name = f'{a}-{b}_{tf}'
    m = load_pair(a, b, tf)
    if m is None or len(m) < 300:
        print(f'{pair_name}: мало данных ({len(m) if m is not None else 0})')
        return None

    bp = config_pairs.get(pair_name, {}).get('best_params', {})
    w = bp.get('window', 30)
    rw = bp.get('resid_window', 60)

    m = build_features(m, window=w, resid_window=rw)

    features = ['z', 'std', 'corr', 'spread_trend', 'beta']
    df = m.dropna(subset=features + ['target']).copy()
    df = df[df['z'].abs() >= 2.0]

    if len(df) < 30:
        print(f'{pair_name}: мало сигналов ({len(df)})')
        return None

    # Walk-forward 5 фолдов (для валидации)
    fold_size = len(df) // 6
    auc_scores = []
    for k in range(5):
        test_start = (k+1) * fold_size
        test_end = test_start + fold_size
        train = df.iloc[:test_start]
        test = df.iloc[test_start:test_end]
        if len(test) < 5 or len(train) < 20:
            continue
        y_tr = train['target'].values
        y_te = test['target'].values
        if len(set(y_tr)) < 2 or len(set(y_te)) < 2:
            continue
        scaler = StandardScaler()
        X_tr = scaler.fit_transform(train[features].values)
        X_te = scaler.transform(test[features].values)
        model = LogisticRegression(max_iter=1000)
        model.fit(X_tr, y_tr)
        try:
            auc = roc_auc_score(y_te, model.predict_proba(X_te)[:, 1])
            auc_scores.append(auc)
        except Exception:
            pass
    avg_auc = np.mean(auc_scores) if auc_scores else 0

    # Финальная модель — на всех данных
    scaler = StandardScaler()
    X_all = scaler.fit_transform(df[features].values)
    y_all = df['target'].values
    model = LogisticRegression(max_iter=1000)
    model.fit(X_all, y_all)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = MODELS_DIR / f'lr_{pair_name}.pkl'
    with open(out_path, 'wb') as f:
        pickle.dump({
            'model': model,
            'scaler': scaler,
            'features': features,
            'window': w,
            'resid_window': rw,
            'pair_name': pair_name,
            'n_signals': len(df),
            'avg_auc': float(avg_auc),
            'trained_at': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
        }, f)

    print(f'{pair_name}: n={len(df)}, avg_auc={avg_auc:.3f}, w={w}, rw={rw} -> {out_path.name}')
    return {'pair': pair_name, 'auc': avg_auc, 'n': len(df), 'path': str(out_path)}


if __name__ == '__main__':
    cfg = json.load(open(CONFIG_PATH))
    config_pairs = cfg.get('pairs', cfg)

    results = []
    for a, b, tf in ML_PAIRS:
        r = train_one(a, b, tf, config_pairs)
        if r:
            results.append(r)

    print()
    print('=== ИТОГО ===')
    for r in results:
        verdict = '✅' if r['auc'] > 0.6 else '❌'
        print(f"  {r['pair']}: AUC={r['auc']:.3f} {verdict}  n={r['n']}  {r['path']}")
