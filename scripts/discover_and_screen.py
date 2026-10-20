#!/usr/bin/env python3
"""
discover_and_screen.py — discovery новых активов на MOEX ISS + упрощённый screening.

Логика:
1. MOEX ISS API → полный список фьючерсов (FORTS).
2. Сравнить с tickers_config.json → новые тикеры.
3. Для новых тикеров — corr + coint_p против СТАРЫХ (из JSON).
4. Отчёт → logs/discovery_YYYY-MM-DD.csv + текстовый вывод.

Запуск:
  python scripts/discover_and_screen.py            # полный (ISS + screening)
  python scripts/discover_and_screen.py --dry-run  # только список новых (без screening)
  python scripts/discover_and_screen.py --min-corr 0.5 --coint-p 0.05

Cron (еженедельно, вс 18:00):
  0 18 * * 0 cd /root/finlab && venv/bin/python scripts/discover_and_screen.py >> logs/discovery_cron.log 2>&1
"""
import argparse, json, datetime
from pathlib import Path
import numpy as np
import pandas as pd
import requests

ROOT = Path('/root/finlab')
CANDLES = ROOT / 'data' / 'candles'
TICKERS_CFG = ROOT / 'FinLabPy' / 'DataCollectors' / 'tickers_config.json'
LOGS = ROOT / 'logs'
ISS_URL = 'https://iss.moex.com/iss/engines/futures/markets/forts/securities.json'


def fetch_moex_futures():
    """Получить полный список фьючерсов с MOEX ISS."""
    try:
        r = requests.get(ISS_URL, params={'iss.meta': 'off'}, timeout=30)
        r.raise_for_status()
        data = r.json()
        sec = data.get('securities', {})
        cols = sec.get('columns', [])
        rows = sec.get('data', [])
        df = pd.DataFrame(rows, columns=cols)
        # Нас интересует ASSETCODE (базовый код, без экспирации) — иначе 489 серий
        col = None
        for c in ('ASSETCODE', 'SECID'):
            if c in df.columns:
                col = c
                break
        if col is None:
            print("WARN: ни ASSETCODE, ни SECID не найдены")
            return None
        tickers = df[col].dropna().astype(str).unique().tolist()
        # фильтр: только базовые коды (2-6 символов, буквы/цифры, без месяца)
        import re
        base = [t for t in tickers if re.fullmatch(r'[A-Z0-9]{2,6}', t)]
        print(f"MOEX ISS: получено {len(tickers)} (ASSETCODE), базовых: {len(base)}")
        return base
    except Exception as e:
        print(f"ERR ISS: {e}")
        return None


def load_existing_tickers():
    """Загрузить существующие тикеры из tickers_config.json."""
    if not TICKERS_CFG.exists():
        print(f"WARN: {TICKERS_CFG} не найден")
        return set()
    cfg = json.loads(TICKERS_CFG.read_text())
    fut = cfg.get('futures', [])
    fut_list = list(fut) if isinstance(fut, list) else list(fut.keys())
    return set(fut_list)


def load_close(ticker, tf='H4'):
    """Загрузить close по тикеру (H4)."""
    f = CANDLES / f'{ticker}_{tf}.parquet'
    if not f.exists():
        return None
    df = pd.read_parquet(f)
    tcol = 'begin' if 'begin' in df.columns else 'tradedate'
    dt = pd.to_datetime(df[tcol], errors='coerce')
    if dt.isna().all():
        return None
    df = df.assign(date=dt.dt.normalize())
    df['close'] = df['close'].apply(lambda x: float(x) if not isinstance(x, bytes) else 0.0)
    df = df[df['close'] > 0]
    return df.groupby('date')['close'].last().reset_index()


def coint_pvalue(s1, s2):
    from statsmodels.tsa.stattools import adfuller
    x = pd.merge(s1, s2, on='date', suffixes=('_a','_b')).dropna()
    if len(x) < 100:
        return None
    la = np.log(x['close_a'].values); lb = np.log(x['close_b'].values)
    beta = np.sum(la*lb) / np.sum(lb*lb)
    resid = la - beta*lb
    if np.std(resid) == 0:
        return None
    try:
        p = float(adfuller(resid, maxlag=1, regression='c', autolag='AIC')[1])
        return p
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true', help='Только список новых, без screening')
    ap.add_argument('--min-corr', type=float, default=0.5)
    ap.add_argument('--coint-p', type=float, default=0.05)
    ap.add_argument('--tf', default='H4')
    args = ap.parse_args()

    LOGS.mkdir(exist_ok=True)
    new_tickers = []
    moex = fetch_moex_futures()
    if moex is None:
        print("ISS недоступен — выход")
        return
    existing = load_existing_tickers()
    print(f"Существующих тикеров в JSON: {len(existing)}")
    new_tickers = [t for t in moex if t not in existing]
    print(f"Новых тикеров (нет в JSON): {len(new_tickers)}")
    if not new_tickers:
        print("Нет новых тикеров — всё актуально.")
        return
    print("Список новых:", new_tickers[:30])

    if args.dry_run:
        print("\n[dry-run] Только список новых. Screening пропущен.")
        return

    # Загружаем close по новым и старым (только те, у кого есть H4)
    print("\nЗагрузка close (H4) по новым и старым...")
    new_close = {t: load_close(t, args.tf) for t in new_tickers}
    new_close = {k: v for k, v in new_close.items() if v is not None}
    old_close = {t: load_close(t, args.tf) for t in existing}
    old_close = {k: v for k, v in old_close.items() if v is not None}
    print(f"  новых с H4: {len(new_close)}")
    print(f"  старых с H4: {len(old_close)}")

    if not new_close or not old_close:
        print("Нет данных для screening (новые или старые без H4) — выход.")
        return

    # Screening: новые × старые
    results = []
    print("\nScreening новых × старых...")
    for nt, nclose in new_close.items():
        for ot, oclose in old_close.items():
            # corr по лог-returns
            ret_n = np.log(nclose['close']).diff().dropna()
            ret_o = np.log(oclose['close']).diff().dropna()
            r = pd.concat([ret_n, ret_o], axis=1, join='inner').dropna()
            if len(r) < 100:
                continue
            corr = float(r.corr().iloc[0,1])
            if abs(corr) < args.min_corr:
                continue
            p = coint_pvalue(nclose, oclose)
            if p is None:
                continue
            results.append({
                'new_ticker': nt,
                'old_ticker': ot,
                'corr': round(corr, 4),
                'coint_p': round(p, 4),
                'is_coint': p < args.coint_p,
                'rows': len(r),
            })

    if not results:
        print("Screening: 0 пар прошли фильтры.")
        # Пишем пустой CSV с заголовками, чтобы get_discovery_summary видел файл
        out = LOGS / f'discovery_{datetime.date.today()}.csv'
        pd.DataFrame(columns=['new_ticker','old_ticker','corr','coint_p','is_coint','rows']).to_csv(out, index=False)
        print(f"OK CSV (пустой): {out}")
        return

    df = pd.DataFrame(results).sort_values(['is_coint','corr'], ascending=[False, False])
    out = LOGS / f'discovery_{datetime.date.today()}.csv'
    df.to_csv(out, index=False)
    print(f"\nOK CSV: {out} (rows={len(df)})")
    print(f"\n=== TOP-20 (новые × старые, по coint/corr) ===")
    for _, r in df.head(20).iterrows():
        flag = '✅' if r['is_coint'] else '  '
        print(f"  {flag} {r['new_ticker']:10s} × {r['old_ticker']:10s} corr={r['corr']:.3f} coint_p={r['coint_p']:.4f} rows={r['rows']}")
    print("\nВАЖНО: это СИГНАЛ, не автоматическое добавление. Дальше — walk-forward по выбранной паре.")


if __name__ == '__main__':
    main()
