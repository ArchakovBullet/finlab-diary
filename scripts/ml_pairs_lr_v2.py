#!/usr/bin/env python3
"""ml_pairs_lr.py — Logistic Regression для пар.

Фичи: z-score, corr, std, spread_trend, beta.
Target: PnL следующей сделки > 0.
Walk-forward 5 фолдов.
"""
import pandas as pd
import numpy as np
import json
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, roc_auc_score

CANDLES = Path('/root/finlab/data/candles')
COMMISSION = 0.0028
TIME_EXIT_BARS = 120

PAIRS = [
    # M10 (3)
    ('SFIN', 'SH', 'M10'),
    ('BANE', 'BN', 'M10'),
    ('BELU', 'NB', 'M10'),
    # H4 (8)
    ('BR', 'GAZPF', 'H4'),
    ('GAZPF', 'SBERF', 'H4'),
    ('GD', 'PT', 'H4'),
    ('GD', 'SV', 'H4'),
    ('GLDRUBF', 'GD', 'H4'),
    ('LK', 'IMOEXF', 'H4'),
    ('PD', 'SV', 'H4'),
    ('PT', 'SV', 'H4'),
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
    # Rolling OLS
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

    # Target: PnL следующей сделки
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
        # Выход через TIME_EXIT или z_exit
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


if __name__ == '__main__':
    for a, b, tf in PAIRS:
        m = load_pair(a, b, tf)
        if m is None or len(m) < 300:
            continue
        # Читаем параметры из config
        _cfg = json.load(open('/root/finlab/FinLabPy/My_Indicators/pairs_config.json'))
        _pairs = _cfg.get('pairs', _cfg)
        _p = _pairs.get(f'{a}-{b}_{tf}', {}).get('best_params', {})
        _w = _p.get('window', 30)
        _rw = _p.get('resid_window', 60)
        m = build_features(m, window=_w, resid_window=_rw)

        # Фичи
        features = ['z', 'std', 'corr', 'spread_trend', 'beta']
        df = m.dropna(subset=features + ['target']).copy()
        # Только сигналы (|z| > 2.5) — там где target имеет смысл
        df = df[(df['z'].abs() >= 2.0)]

        if len(df) < 30:
            print(f'{a}-{b}_{tf}: мало данных ({len(df)})')
            continue

        X = df[features].values
        y = df['target'].values

        # Walk-forward 5 фолдов
        fold_size = len(df) // 6
        auc_scores = []
        for k in range(5):
            test_start = (k+1) * fold_size
            test_end = test_start + fold_size
            train = df.iloc[:test_start]
            test = df.iloc[test_start:test_end]
            if len(test) < 5 or len(train) < 20:
                continue
            X_tr = train[features].values; y_tr = train['target'].values
            X_te = test[features].values; y_te = test['target'].values
            if len(set(y_tr)) < 2:
                continue
            scaler = StandardScaler()
            X_tr_s = scaler.fit_transform(X_tr)
            X_te_s = scaler.transform(X_te)
            model = LogisticRegression(max_iter=1000)
            model.fit(X_tr_s, y_tr)
            y_pred = model.predict_proba(X_te_s)[:, 1]
            try:
                auc = roc_auc_score(y_te, y_pred)
                auc_scores.append(auc)
            except Exception:
                pass

        avg_auc = np.mean(auc_scores) if auc_scores else 0
        verdict = '✅' if avg_auc > 0.55 else '❌'
        print(f'{a}-{b}_{tf}: n={len(df)}, avg_auc={avg_auc:.3f} {verdict}')
