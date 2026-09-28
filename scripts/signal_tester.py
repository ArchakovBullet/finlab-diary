"""
FinLabPy — единый шаблон тестирования сигналов.

Возможности:
- merge сигнала со свечами (с фиксом date_col: tradedate / date / begin)
- forward return на горизонт H
- score по HI2 (z-score по тикеру: netflow_buy, buy, agressive_buy)
- метрики: n, mean, std, WR, base_WR, gross_edge, net_edge,
            sharpe_per_trade, t_stat, PF, avg_win, avg_loss,
            zero_share, max_dd
- purged walk-forward: 2 фолда x 10 дней теста, gap = горизонт (10)
- комиссия: 0.14% x 2 = 0.28%

Правила проекта:
- НЕ патчить sed. Только text.replace / nano.
- Sharpe — per-trade, без аннуализации (на 41 дне это фикция).
- Бенчмарк = mean fwd_ret по ВСЕМ сделкам (не только по сигналу).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

COMMISSION = 0.0014  # 0.14% на сторону; вход+выход = 0.28%
HI2_HORIZON = 10     # дней


# ---------------------------------------------------------------------------
# Merge / нормализация даты
# ---------------------------------------------------------------------------

def normalize_date_col(c: pd.DataFrame,
                       date_col: str | None = None) -> pd.DataFrame:
    """Приводит колонку даты к единому виду 'tradedate' (datetime64, normalized).

    Фикс из брифа: tradedate / date / begin — что первое найдётся.
    """
    c = c.copy()
    if date_col is None:
        date_col = (
            'tradedate' if 'tradedate' in c.columns
            else 'date' if 'date' in c.columns
            else 'begin' if 'begin' in c.columns
            else c.columns[0]
        )
    c['tradedate'] = pd.to_datetime(c[date_col], errors='coerce').dt.normalize()
    return c


def merge_signal_with_candles(signal_df: pd.DataFrame,
                              candles_df: pd.DataFrame,
                              ticker_col: str = 'ticker',
                              signal_date_col: str = 'tradedate',
                              price_col: str = 'close') -> pd.DataFrame:
    """Inner merge сигнала и свечей по (ticker, tradedate)."""
    s = normalize_date_col(signal_df, date_col=signal_date_col)
    c = normalize_date_col(candles_df)

    keep = [ticker_col, 'tradedate', price_col]
    c = c[keep].drop_duplicates(subset=[ticker_col, 'tradedate'])

    merged = s.merge(c, on=[ticker_col, 'tradedate'], how='inner',
                     suffixes=('_sig', '_px'))
    return merged


# ---------------------------------------------------------------------------
# Forward return + HI2 score
# ---------------------------------------------------------------------------

def add_forward_returns(df: pd.DataFrame, horizon: int,
                        price_col: str = 'close',
                        group_col: str = 'ticker') -> pd.DataFrame:
    """fwd_ret = close.shift(-H) / close - 1, по каждому тикеру."""
    d = df.sort_values([group_col, 'tradedate']).copy()
    g = d.groupby(group_col, group_keys=False)
    d['fwd_ret'] = g[price_col].shift(-horizon) / d[price_col] - 1.0
    return d


def _zscore_by_ticker(df: pd.DataFrame, col: str,
                      group_col: str = 'ticker') -> pd.Series:
    """Z-score колонки col внутри каждого тикера (по времени)."""
    g = df.groupby(group_col)[col]
    mu = g.transform('mean')
    sd = g.transform('std')
    return (df[col] - mu) / sd.replace(0, np.nan)


def add_hi2_score(df: pd.DataFrame,
                  cols: tuple[str, str, str] = (
                      'hhi_netflow_buy', 'hhi_buy', 'hhi_agressive_buy'),
                  group_col: str = 'ticker') -> pd.DataFrame:
    """score = среднее z-score трёх метрик (netflow_buy, buy, agressive_buy)."""
    d = df.copy()
    zs = [_zscore_by_ticker(d, c, group_col=group_col) for c in cols]
    d['hi2_score'] = (zs[0] + zs[1] + zs[2]) / 3.0
    return d


# ---------------------------------------------------------------------------
# Метрики
# ---------------------------------------------------------------------------

def max_drawdown_trades(returns) -> float:
    """Max drawdown по equity-кривой сделок (в порядке времени)."""
    r = np.asarray(returns, dtype=float)
    if r.size == 0:
        return np.nan
    eq = np.cumsum(r)
    peak = np.maximum.accumulate(eq)
    dd = eq - peak
    return float(dd.min())


def _metrics(r: np.ndarray, base_mean: float, base_wr: float) -> dict:
    """Считает все метрики по массиву fwd_ret попавших сделок."""
    n = int(r.size)
    if n == 0:
        return dict(n=0, mean=np.nan, std=np.nan, wr=np.nan,
                    base_mean=base_mean, base_wr=base_wr,
                    gross_edge=np.nan, net_edge=np.nan,
                    sharpe_per_trade=np.nan, t_stat=np.nan,
                    pf=np.nan, avg_win=np.nan, avg_loss=np.nan,
                    zero_share=np.nan, max_dd=np.nan)

    mean_r = float(np.mean(r))
    std_r = float(np.std(r, ddof=1)) if n > 1 else np.nan
    wr = float(np.mean(r > 0))

    win = r[r > 0]
    loss = r[r < 0]
    pf = float(win.sum() / abs(loss.sum())) if loss.size > 0 else np.nan
    avg_w = float(win.mean()) if win.size > 0 else np.nan
    avg_l = float(loss.mean()) if loss.size > 0 else np.nan

    sharpe = mean_r / std_r if (std_r and std_r > 0) else np.nan
    tstat = mean_r / (std_r / np.sqrt(n)) if (std_r and std_r > 0) else np.nan
    zero_share = float(np.mean(np.isclose(r, 0.0)))
    mdd = max_drawdown_trades(r)

    gross_edge = mean_r - base_mean
    net_edge = gross_edge - 2 * COMMISSION

    return dict(n=n, mean=mean_r, std=std_r, wr=wr,
                base_mean=base_mean, base_wr=base_wr,
                gross_edge=gross_edge, net_edge=net_edge,
                sharpe_per_trade=sharpe, t_stat=tstat,
                pf=pf, avg_win=avg_w, avg_loss=avg_l,
                zero_share=zero_share, max_dd=mdd)


def test_signal(df: pd.DataFrame, score_col: str, threshold: float,
                horizon: int, verbose: bool = True) -> dict:
    """Основная функция теста сигнала на полном датасете.

    df должен содержать: score_col, 'fwd_ret', желательно 'tradedate'.
    """
    d = df.dropna(subset=[score_col, 'fwd_ret']).copy()
    base_mean = float(d['fwd_ret'].mean()) if len(d) else np.nan
    base_wr = float((d['fwd_ret'] > 0).mean()) if len(d) else np.nan

    hits = d[d[score_col] > threshold]
    r = hits['fwd_ret'].to_numpy(dtype=float)
    m = _metrics(r, base_mean, base_wr)

    if verbose:
        print(f"--- signal: {score_col} > {threshold}, horizon={horizon} ---")
        print(f"  n              : {m['n']}")
        print(f"  mean           : {m['mean']:.4%}" if pd.notna(m['mean']) else "  mean           : nan")
        print(f"  std            : {m['std']:.4%}" if pd.notna(m['std']) else "  std            : nan")
        print(f"  WR             : {m['wr']:.3%}" if pd.notna(m['wr']) else "  WR             : nan")
        print(f"  base_mean      : {m['base_mean']:.4%}" if pd.notna(m['base_mean']) else "  base_mean      : nan")
        print(f"  base_WR        : {m['base_wr']:.3%}" if pd.notna(m['base_wr']) else "  base_WR        : nan")
        print(f"  gross_edge     : {m['gross_edge']:.4%}" if pd.notna(m['gross_edge']) else "  gross_edge     : nan")
        print(f"  net_edge       : {m['net_edge']:.4%}" if pd.notna(m['net_edge']) else "  net_edge       : nan")
        print(f"  sharpe_per_tr  : {m['sharpe_per_trade']:.4f}" if pd.notna(m['sharpe_per_trade']) else "  sharpe_per_tr  : nan")
        print(f"  t_stat         : {m['t_stat']:.4f}" if pd.notna(m['t_stat']) else "  t_stat         : nan")
        print(f"  PF             : {m['pf']:.4f}" if pd.notna(m['pf']) else "  PF             : nan")
        print(f"  avg_win        : {m['avg_win']:.4%}" if pd.notna(m['avg_win']) else "  avg_win        : nan")
        print(f"  avg_loss       : {m['avg_loss']:.4%}" if pd.notna(m['avg_loss']) else "  avg_loss       : nan")
        print(f"  zero_share     : {m['zero_share']:.3%}" if pd.notna(m['zero_share']) else "  zero_share     : nan")
        print(f"  max_dd         : {m['max_dd']:.4%}" if pd.notna(m['max_dd']) else "  max_dd         : nan")
    return m


# ---------------------------------------------------------------------------
# Purged walk-forward (2 фолда x 10 дней теста, gap = horizon)
# ---------------------------------------------------------------------------

def purged_walk_forward(df: pd.DataFrame, score_col: str, threshold: float,
                        horizon: int, n_folds: int = 2,
                        fold_size: int = 10, verbose: bool = True) -> list[dict]:
    """Purged walk-forward по последовательным дням tradedate.

    По брифу:
      fold 1: train [0:10], gap 10, test [20:30]
      fold 2: train [10:20], gap 10, test [30:40]

    Используем уникальные tradedate, отсортированные.
    """
    d = df.dropna(subset=[score_col, 'fwd_ret']).copy()
    if 'tradedate' not in d.columns:
        raise ValueError("purged_walk_forward: нужна колонка 'tradedate'")

    days = np.array(sorted(d['tradedate'].unique()))
    if len(days) < (n_folds + 1) * fold_size + horizon:
        print(f"[WARN] дней={len(days)}, для {n_folds} фолдов по {fold_size} теста "
              f"с gap={horizon} может не хватить — считаем сколько есть")

    results = []
    for k in range(n_folds):
        train_lo = k * fold_size
        train_hi = train_lo + fold_size
        gap_hi = train_hi + horizon
        test_lo = gap_hi
        test_hi = test_lo + fold_size

        if test_hi > len(days):
            print(f"[fold {k+1}] пропуск: test_hi={test_hi} > дней={len(days)}")
            continue

        train_days = days[train_lo:train_hi]
        test_days = days[test_lo:test_hi]

        dtr = d[d['tradedate'].isin(train_days)]
        dte = d[d['tradedate'].isin(test_days)]

        base_mean = float(dte['fwd_ret'].mean()) if len(dte) else np.nan
        base_wr = float((dte['fwd_ret'] > 0).mean()) if len(dte) else np.nan

        hits = dte[dte[score_col] > threshold]
        r = hits['fwd_ret'].to_numpy(dtype=float)
        m = _metrics(r, base_mean, base_wr)
        m['fold'] = k + 1
        m['train_days'] = (str(pd.Timestamp(train_days[0]).date()),
                           str(pd.Timestamp(train_days[-1]).date()))
        m['test_days'] = (str(pd.Timestamp(test_days[0]).date()),
                          str(pd.Timestamp(test_days[-1]).date()))
        results.append(m)

        if verbose:
            print(f"--- fold {k+1}: train {m['train_days']} | test {m['test_days']} ---")
            print(f"  n={m['n']}  net_edge={m['net_edge']:.4%}  sharpe_per_tr={m['sharpe_per_trade']:.4f}"
                  if pd.notna(m['net_edge']) else "  (пусто)")
    return results


# ---------------------------------------------------------------------------
# Демо-прогон 4.2
# ---------------------------------------------------------------------------

def _load_hi2_and_candles(hi2_path: str = 'data/hi2_daily.parquet',
                          candles_glob: str = 'data/candles/*_D1.parquet') -> pd.DataFrame:
    import glob
    hi2 = pd.read_parquet(hi2_path)
    frames = []
    for f in glob.glob(candles_glob):
        c = pd.read_parquet(f)
        c['ticker'] = f.split('/')[-1].split('_')[0]
        frames.append(c[['ticker', 'begin', 'close']])
    candles = pd.concat(frames, ignore_index=True)
    merged = merge_signal_with_candles(hi2, candles)
    merged = add_forward_returns(merged, HI2_HORIZON, price_col='close', group_col='ticker')
    merged = add_hi2_score(merged)
    return merged


if __name__ == '__main__':
    print("=== HI2: merge signal + candles, fwd_ret H=10, score z-by-ticker ===")
    df = _load_hi2_and_candles()
    print(f"merged rows: {len(df)}, tickers: {df['ticker'].nunique()}, "
          f"days: {df['tradedate'].nunique()}, "
          f"date range: {df['tradedate'].min().date()} .. {df['tradedate'].max().date()}")

    print()
    test_signal(df, 'hi2_score', threshold=2.0, horizon=HI2_HORIZON)
    print()
    test_signal(df, 'hi2_score', threshold=3.0, horizon=HI2_HORIZON)

    print()
    print("=== Purged walk-forward (2 folds x 10d, gap 10) ===")
    purged_walk_forward(df, 'hi2_score', threshold=2.0, horizon=HI2_HORIZON,
                        n_folds=2, fold_size=10)
