"""
TradeStats signals — единая точка расчёта сигналов для акций.
=================================================================
Используется:
- robots/tradestats_stocks_robot.py
- дашборд

Сигналы (5, H=5д):
- pr_change (Sharpe 2.79) — сумма pr_change за день
- pr_body (Sharpe 1.98) — pr_close − pr_open
- sec_pr_range (Sharpe 1.54) — sec_pr_high − sec_pr_low
- val_net (Sharpe 1.36) — val_b − val_s
- vol_net (Sharpe 1.22) — vol_b − vol_s

Порог входа: score >= 3 (из 5).
"""
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

ROOT = Path('/root/finlab')
TRADESTATS_DIR = ROOT / 'data' / 'tradestats'

# 5 сигналов (из тестов)
SIGNALS = ['pr_change', 'pr_body', 'sec_pr_range', 'val_net', 'vol_net']
SCORE_MIN = 3  # из 5


def _load_tradestats(ticker, lookback_days=60):
    """Загрузить TradeStats для тикера, дневная агрегация."""
    f = TRADESTATS_DIR / f'{ticker}_tradestats.parquet'
    if not f.exists():
        return None
    df = pd.read_parquet(f)
    df['tradedate'] = pd.to_datetime(df['tradedate'])
    cutoff = datetime.now() - timedelta(days=lookback_days)
    df = df[df['tradedate'] >= cutoff]
    if len(df) == 0:
        return None
    # Метрики
    df['pr_change'] = df['pr_change']
    df['pr_body'] = df['pr_close'] - df['pr_open']
    df['sec_pr_range'] = df['sec_pr_high'] - df['sec_pr_low']
    df['val_net'] = df['val_b'] - df['val_s']
    df['vol_net'] = df['vol_b'] - df['vol_s']
    # Дневная агрегация
    daily = df.groupby('tradedate').agg({
        'pr_change': 'sum',
        'pr_body': 'sum',
        'sec_pr_range': 'sum',
        'val_net': 'sum',
        'vol_net': 'sum',
    }).reset_index().sort_values('tradedate').reset_index(drop=True)
    return daily


def get_tradestats_signal(ticker, lookback_days=60):
    """
    Получить сигнал TradeStats для тикера.

    Returns:
        dict или None:
          - direction: 'LONG' / None (SHORT не используем)
          - score: int (0-5)
          - signals: dict (какие сигналы сработали)
          - metrics: dict (значения метрик)
    """
    daily = _load_tradestats(ticker, lookback_days)
    if daily is None or len(daily) < 30:
        return None

    last = daily.iloc[-1]
    signals = {}
    metrics = {}

    for col in SIGNALS:
        if col not in daily.columns:
            continue
        q80 = daily[col].quantile(0.8)
        val = last[col]
        metrics[col] = float(val)
        if val > q80:
            signals[col] = 'top'

    # Только LONG (score = число top-сигналов)
    score = len(signals)
    direction = 'LONG' if score >= SCORE_MIN else None

    return {
        'direction': direction,
        'score': score,
        'signals': signals,
        'metrics': metrics,
    }


if __name__ == '__main__':
    STOCKS = ['GAZP', 'GMKN', 'HYDR', 'IRAO', 'LKOH', 'PLZL', 'ROSN', 'SBER', 'TATN', 'VTBR']
    for t in STOCKS:
        sig = get_tradestats_signal(t)
        if sig:
            print(f"  {t:8s} | {sig['direction']} | score={sig['score']} | {sig['signals']}")
        else:
            print(f"  {t:8s} | нет данных")
