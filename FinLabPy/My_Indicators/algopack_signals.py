"""
Algopack signals — единая точка расчёта сигналов TradeStats + FutOI.
====================================================================
Используется:
- robots/futures_algopack_robot.py (фьючерсы)
- robots/tradestats_stocks_robot.py (акции)
- дашборд

Сигналы (5д горизонт):
- TradeStats: sec_pr_range, vol_net, pr_body, val_net, trades_net
- FutOI: yur_buy_ratio, yur_long_ratio, fiz_buy_ratio
"""
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

ROOT = Path('/root/finlab')
TRADESTATS_DIR = ROOT / 'data' / 'tradestats'
FUTOI_PATH = ROOT / 'data' / 'futoi_1h' / 'futoi_1h.parquet'
CANDLES_DIR = ROOT / 'data' / 'candles'


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
    df['val_net'] = df['val_b'] - df['val_s']
    df['vol_net'] = df['vol_b'] - df['vol_s']
    df['trades_net'] = df['trades_b'] - df['trades_s']
    df['pr_body'] = df['pr_close'] - df['pr_open']
    df['pr_range'] = df['pr_high'] - df['pr_low']
    df['sec_pr_range'] = df['sec_pr_high'] - df['sec_pr_low']
    # Дневная агрегация
    daily = df.groupby('tradedate').agg({
        'val_net': 'sum', 'vol_net': 'sum', 'trades_net': 'sum',
        'pr_body': 'sum', 'pr_range': 'sum', 'sec_pr_range': 'sum',
        'val': 'sum', 'vol': 'sum', 'trades': 'sum',
    }).reset_index().sort_values('tradedate').reset_index(drop=True)
    return daily


def _load_futoi(ticker, lookback_days=60):
    """Загрузить FutOI для тикера, дневная агрегация."""
    if not FUTOI_PATH.exists():
        return None
    df = pd.read_parquet(FUTOI_PATH)
    df = df[df['ticker'] == ticker]
    if len(df) == 0:
        return None
    df['hour'] = pd.to_datetime(df['hour'])
    df['tradedate'] = df['hour'].dt.normalize()
    cutoff = datetime.now() - timedelta(days=lookback_days)
    df = df[df['tradedate'] >= cutoff]
    if len(df) == 0:
        return None
    # Производные
    df['yur_net'] = df['yur_long'] - df['yur_short']
    df['fiz_net'] = df['fiz_long'] - df['fiz_short']
    # *_long_ratio (доля лонгов в общем объёме)
    df['fiz_long_ratio'] = df['fiz_long'] / df['fiz_total'].replace(0, np.nan)
    df['yur_long_ratio'] = df['yur_long'] / df['yur_total'].replace(0, np.nan)
    # Дневная агрегация
    daily = df.groupby('tradedate').agg({
        'yur_buy_ratio': 'mean', 'fiz_buy_ratio': 'mean',
        'yur_long_ratio': 'mean', 'fiz_long_ratio': 'mean',
        'yur_net': 'mean', 'fiz_net': 'mean',
    }).reset_index().sort_values('tradedate').reset_index(drop=True)
    return daily


def get_tradestats_signal(ticker, lookback_days=60):
    """
    Получить сигнал TradeStats для тикера.
    
    Returns:
        dict или None:
          - direction: 'LONG' / 'SHORT' / None
          - score: int (сколько сигналов сработало)
          - signals: dict (какие сигналы сработали)
          - metrics: dict (значения метрик)
          - lqdt_beat_rate: float
    """
    daily = _load_tradestats(ticker, lookback_days)
    if daily is None or len(daily) < 30:
        return None
    
    # Последний день
    last = daily.iloc[-1]
    
    # Квантили за всю историю
    signals = {}
    metrics = {}
    
    for col, direction in [
        ('vol_net', 'LONG'), ('val_net', 'LONG'), ('trades_net', 'LONG'),
        ('pr_body', 'LONG'), ('sec_pr_range', 'LONG'),
    ]:
        if col not in daily.columns:
            continue
        q80 = daily[col].quantile(0.8)
        q20 = daily[col].quantile(0.2)
        val = last[col]
        metrics[col] = float(val)
        if val > q80:
            signals[col] = 'top'
        elif val < q20:
            signals[col] = 'bot'
    
    # Определяем направление
    long_count = sum(1 for v in signals.values() if v == 'top')
    short_count = sum(1 for v in signals.values() if v == 'bot')
    
    direction = None
    score = 0
    if long_count >= 2:
        direction = 'LONG'
        score = long_count
    elif short_count >= 2:
        direction = 'SHORT'
        score = short_count
    
    # Слабые метрики — для логирования (не для входа)
    weak_metrics = {}
    for col in ['val', 'vol', 'trades', 'pr_std', 'pr_std_ratio', 'pr_range', 'sec_pr_body']:
        if col in daily.columns:
            weak_metrics[col] = float(last[col])
    
    return {
        'direction': direction,
        'score': score,
        'signals': signals,
        'metrics': metrics,
        'weak_metrics': weak_metrics,
    }


def get_futoi_signal(ticker, lookback_days=60):
    """Получить сигнал FutOI для тикера."""
    daily = _load_futoi(ticker, lookback_days)
    if daily is None or len(daily) < 30:
        return None
    
    last = daily.iloc[-1]
    signals = {}
    metrics = {}
    
    for col, direction in [
        ('yur_buy_ratio', 'LONG'), ('fiz_buy_ratio', 'SHORT'),
        ('yur_long_ratio', 'LONG'),
    ]:
        if col not in daily.columns:
            continue
        q80 = daily[col].quantile(0.8)
        q20 = daily[col].quantile(0.2)
        val = last[col]
        metrics[col] = float(val)
        if direction == 'LONG':
            if val > q80:
                signals[col] = 'top'
        else:  # SHORT (fiz — контр-сигнал)
            if val < q20:
                signals[col] = 'bot'
    
    long_count = sum(1 for v in signals.values() if v in ('top',))
    short_count = 0
    if 'fiz_buy_ratio' in signals and signals['fiz_buy_ratio'] == 'bot':
        long_count += 1
    
    direction = None
    score = 0
    if long_count >= 2:
        direction = 'LONG'
        score = long_count
    
    return {
        'direction': direction,
        'score': score,
        'signals': signals,
        'metrics': metrics,
    }


def get_combined_signal(ticker):
    """
    Комбинированный сигнал: TradeStats + FutOI.
    
    Returns:
        dict:
          - direction: 'LONG' / 'SHORT' / None
          - score: int (сумма баллов)
          - tradestats: dict
          - futoi: dict
    """
    ts = get_tradestats_signal(ticker)
    fo = get_futoi_signal(ticker)
    
    direction = None
    score = 0
    
    if ts and ts['direction']:
        direction = ts['direction']
        score = ts['score']
    if fo and fo['direction'] == direction:
        score += fo['score']
    elif fo and fo['direction'] and not direction:
        direction = fo['direction']
        score = fo['score']
    
    return {
        'direction': direction,
        'score': score,
        'tradestats': ts,
        'futoi': fo,
    }


if __name__ == '__main__':
    # Smoke-test
    for t in ['LKOH', 'GAZP', 'ROSN', 'SBER', 'BR', 'RI']:
        sig = get_combined_signal(t)
        print(f"{t}: {sig['direction']} (score={sig['score']})")
        if sig['tradestats']:
            print(f"  TS: {sig['tradestats']['signals']}")
        if sig['futoi']:
            print(f"  FO: {sig['futoi']['signals']}")
