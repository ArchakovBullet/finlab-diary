#!/usr/bin/env python3
"""
pairs_screener.py — скринер новых пар для FinLabPy.

Что делает:
- Берёт все тикеры из tickers_config.json (futures + stocks).
- Для всех пар в пределах одного класса (futures x futures, stocks x stocks) считает:
    * correlation (log-returns, 60/120 баров)
    * cointegration (Engle-Granger: ADF на остатках OLS)
    * ADF на spread (stationarity)
    * ликвидность (median turnover или rows)
- Ранжирует по score = (1 - coint_pvalue) * corr * liquidity_factor
- Пишет отчёт в logs/pairs_screener_YYYY-MM-DD.csv
- ВЫКЛАДЫВАЕТ top-N предложений (не авто-добавляет в config!)
- ВАЖНО: config не трогает. Добавление в pairs_config*.json — вручную после walk-forward.

Запуск: python scripts/pairs_screener.py [--tf H4|M10] [--top 20] [--min-corr 0.5]
"""
import argparse, json, datetime
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path('/root/finlab')
CANDLES = ROOT / 'data' / 'candles'
TICKERS_CFG = ROOT / 'FinLabPy' / 'DataCollectors' / 'tickers_config.json'
CONFIG_V3 = ROOT / 'FinLabPy' / 'My_Indicators' / 'pairs_config_v3.json'
LOGS = ROOT / 'logs'


def load_close(ticker, tf):
    f = CANDLES / f'{ticker}_{tf}.parquet'
    if not f.exists():
        return None
    df = pd.read_parquet(f)
    tcol = 'begin' if 'begin' in df.columns else 'tradedate'
    if tcol not in df.columns or 'close' not in df.columns:
        return None
    s = df[[tcol, 'close']].rename(columns={tcol: 'dt'})
    s = s[s['close'] > 0].dropna().drop_duplicates('dt').set_index('dt')['close']
    if len(s) < 200:
        return None
    return s


def coint_pvalue(s1, s2):
    """Engle-Granger: OLS s1~s2, ADF на остатках. Возвращает p-value (bool: коинтегр.)."""
    from statsmodels.tsa.stattools import adfuller
    x = pd.concat([s1, s2], axis=1, join='inner').dropna()
    if len(x) < 100:
        return None, None
    x.columns = ['a','b']
    la = np.log(x['a'].values); lb = np.log(x['b'].values)
    # OLS без intercept: la = beta*lb + resid
    beta = np.sum(la*lb) / np.sum(lb*lb)
    resid = la - beta*lb
    if np.std(resid) == 0:
        return None, None
    try:
        adf = adfuller(resid, maxlag=1, regression='c', autolag='AIC')
        return float(adf[1]), beta
    except Exception:
        return None, None


def adf_pvalue(s):
    from statsmodels.tsa.stattools import adfuller
    s = s.dropna()
    if len(s) < 100: return None
    try:
        return float(adfuller(s, maxlag=1, autolag='AIC')[1])
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tf', default='H4', choices=['H4','M10'])
    ap.add_argument('--top', type=int, default=20)
    ap.add_argument('--min-corr', type=float, default=0.5)
    args = ap.parse_args()

    if not TICKERS_CFG.exists():
        print(f"Нет {TICKERS_CFG}"); return
    tickers_cfg = json.loads(TICKERS_CFG.read_text())
    # Структура может быть: {"futures": [...], "stocks": [...]} или {"futures": {"TICKER": {...}}}
    futures = tickers_cfg.get('futures', [])
    futures_list = list(futures) if isinstance(futures, list) else list(futures.keys())
    # ТОЛЬКО фьючерсы (stocks исключены: шорт по акциям запрещён принципиально)
    universe = [('futures', t) for t in futures_list]
    print(f"Universe: {len(futures_list)} futures ONLY (stocks исключены)")
    print(f"TF: {args.tf}, min_corr: {args.min_corr}, top: {args.top}")

    # Уже в config v3 — исключаем
    if CONFIG_V3.exists():
        cfg = json.loads(CONFIG_V3.read_text())
        existing = set()
        for k, v in cfg.get('pairs', {}).items():
            base = v.get('pair_name', k).replace('_M10', '').replace('_H4', '')
            parts = base.split('-')
            if len(parts) == 2:
                existing.add(tuple(sorted(parts)))
        print(f"Уже в config v3: {len(existing)} баз-пар")
    else:
        existing = set()

    # Загружаем close по каждому тикеру (кэш)
    print("Загрузка close...")
    close = {}
    for cls, t in universe:
        s = load_close(t, args.tf)
        if s is not None:
            close[t] = s
    print(f"Загружено: {len(close)} тикеров")

    # Считаем log-returns для corr
    rets = {t: np.log(s).diff().dropna() for t, s in close.items()}

    # Пары в пределах класса
    results = []
    items = list(close.keys())
    n = len(items)
    print(f"Сканируем {n*(n-1)//2} пар...")
    for i in range(n):
        for j in range(i+1, n):
            a, b = items[i], items[j]
            # Тот же класс?
            # Все — фьючерсы (stocks исключены)
            # Уже в config?
            if tuple(sorted([a, b])) in existing:
                continue
            # Корреляция log-returns
            r = pd.concat([rets[a], rets[b]], axis=1, join='inner').dropna()
            if len(r) < 100:
                continue
            corr = float(r.corr().iloc[0,1])
            if abs(corr) < args.min_corr:
                continue
            # Коинтеграция
            pval_coint, beta = coint_pvalue(close[a], close[b])
            if pval_coint is None:
                continue
            # ADF на spread (на логарифмах, β из OLS)
            la = np.log(close[a]); lb = np.log(close[b])
            sp = (la - beta*lb).dropna()
            pval_adf = adf_pvalue(sp)
            if pval_adf is None:
                continue
            # Ликвидность: сколько точек (медиана по обоим)
            liq = min(len(close[a]), len(close[b]))
            liq_factor = np.log10(liq)  # 2000 → 3.3
            # Score
            score = (1 - pval_coint) * abs(corr) * liq_factor
            results.append({
                'pair': f'{a}-{b}_{args.tf}',
                'tf': args.tf,
                'corr': round(corr, 4),
                'coint_pvalue': round(pval_coint, 4),
                'adf_pvalue': round(pval_adf, 4),
                'beta': round(float(beta), 4),
                'liq_rows': liq,
                'score': round(float(score), 4),
                'is_coint': pval_coint < 0.05,
                'spread_stationary': pval_adf < 0.05,
            })

    results.sort(key=lambda x: x['score'], reverse=True)
    df = pd.DataFrame(results)
    out = LOGS / f'pairs_screener_{datetime.date.today()}.csv'
    df.to_csv(out, index=False)
    print(f"\n✅ CSV: {out} (rows={len(df)})")
    print(f"\n=== TOP {args.top} новых пар (по score) ===")
    for r in results[:args.top]:
        flag = '✅' if (r['is_coint'] and r['spread_stationary']) else '  '
        print(f"  {flag} {r['pair']:25s} corr={r['corr']:.3f} coint_p={r['coint_pvalue']:.4f} adf_p={r['adf_pvalue']:.4f} beta={r['beta']:7.3f} score={r['score']:.3f} liq={r['liq_rows']}")
    print()
    print("ВАЖНО: скринер НЕ добавляет пары в config. Только предлагает.")
    print("Следующий шаг: walk-forward по выбранной паре → затем вручную в pairs_config_v2/v3.json.")


if __name__ == '__main__':
    main()
