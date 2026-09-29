"""
LQDT benchmark — единая точка сравнения с фондом ликвидности MOEX.
===================================================
Используется:
- dashboard (app_v2.py) — сравнение роботов с LQDT
- robots/* — сравнение новых роботов с LQDT

LQDT ~ 16-17% годовых (безрисковый ориентир).
"""
from pathlib import Path
from datetime import datetime
import pandas as pd

LQDT_PATH = Path('/root/finlab/data/candles/LQDT_D1.parquet')
DEPOSIT_DEFAULT = 100000


def load_lqdt():
    """Загрузить LQDT_D1.parquet (begin, close)."""
    if not LQDT_PATH.exists():
        return None
    df = pd.read_parquet(LQDT_PATH)
    if 'begin' not in df.columns:
        return None
    df['begin'] = pd.to_datetime(df['begin'])
    df = df.sort_values('begin').reset_index(drop=True)
    return df


def compare_to_lqdt(start, end, robot_return_pct, deposit=DEPOSIT_DEFAULT, pnl=None):
    """
    Сравнить доходность робота с LQDT за период [start, end].
    
    Args:
        start: datetime — начало периода (entry_time первой сделки)
        end: datetime — конец периода (exit_time последней сделки)
        robot_return_pct: float — доходность робота в %
        deposit: float — депозит (для расчёта, если pnl передан)
        pnl: float, optional — абсолютный PnL, пересчитает robot_return_pct
    
    Returns:
        dict:
          - lqdt_return: float или None
          - robot_return: float
          - diff: float (robot - lqdt)
          - beat: bool (robot > lqdt)
          - n_points: int (точек LQDT в периоде)
          - fallback: bool (использован fallback)
    """
    lqdt_df = load_lqdt()
    if lqdt_df is None or len(lqdt_df) == 0:
        return {'lqdt_return': None, 'robot_return': robot_return_pct,
                'diff': None, 'beat': None, 'n_points': 0, 'fallback': False}
    
    if pnl is not None:
        robot_return_pct = pnl / deposit * 100
    
    start = pd.to_datetime(start)
    end = pd.to_datetime(end)
    
    period = lqdt_df[(lqdt_df['begin'] >= start) & (lqdt_df['begin'] <= end)]
    fallback = False
    if len(period) < 2:
        period = lqdt_df[lqdt_df['begin'] <= end].tail(2)
        fallback = True
    
    if len(period) < 2:
        return {'lqdt_return': None, 'robot_return': robot_return_pct,
                'diff': None, 'beat': None, 'n_points': len(period), 'fallback': fallback}
    
    lqdt_return = (period['close'].iloc[-1] - period['close'].iloc[0]) / period['close'].iloc[0] * 100
    diff = robot_return_pct - lqdt_return
    
    return {
        'lqdt_return': float(lqdt_return),
        'robot_return': float(robot_return_pct),
        'diff': float(diff),
        'beat': bool(diff > 0),
        'n_points': int(len(period)),
        'fallback': fallback,
    }


def beat_lqdt_rate(closed_positions, deposit=DEPOSIT_DEFAULT):
    """
    Доля сделок, где робот обошёл LQDT за период удержания.
    
    Args:
        closed_positions: list[dict] — [{'entry_time', 'exit_time', 'pnl'}, ...]
        deposit: float
    
    Returns:
        dict: {'n': int, 'beat': int, 'rate': float, 'avg_diff': float}
    """
    lqdt_df = load_lqdt()
    if lqdt_df is None or not closed_positions:
        return {'n': 0, 'beat': 0, 'rate': 0.0, 'avg_diff': 0.0}
    
    beat = 0
    diffs = []
    for pos in closed_positions:
        r = compare_to_lqdt(pos['entry_time'], pos['exit_time'],
                            robot_return_pct=0, deposit=deposit, pnl=pos['pnl'])
        if r['diff'] is not None:
            diffs.append(r['diff'])
            if r['beat']:
                beat += 1
    
    n = len(diffs)
    return {
        'n': n,
        'beat': beat,
        'rate': (beat / n * 100) if n > 0 else 0.0,
        'avg_diff': (sum(diffs) / n) if n > 0 else 0.0,
    }


if __name__ == '__main__':
    # Smoke-test
    r = compare_to_lqdt('2026-09-01', '2026-09-29', robot_return_pct=5.0)
    print(r)
