"""
Агрегатор дневных HI2 данных. Группирует внутридневные записи в одну строку на день.
Запускается после сборщика HI2.

Использование:
    python FinLabPy/DataCollectors/hi2_daily_aggregator.py
"""
import os
import sys
from pathlib import Path
from datetime import date

project_root = Path(__file__).parent.parent.parent if '__file__' in globals() else Path('.').absolute()
sys.path.insert(0, str(project_root))

import polars as pl
from FinLabPy.Utils import setup_logger

logger = setup_logger('hi2_aggregator')

DATA_DIR = project_root / 'data' / 'hi2'
OUTPUT_FILE = project_root / 'data' / 'hi2_daily.parquet'

# Все 11 метрик HI2
METRICS = [
    'hhi_agressive', 'hhi_agressive_buy', 'hhi_agressive_sell',
    'hhi_buy', 'hhi_sell',
    'hhi_netflow_buy', 'hhi_netflow_sell',
    'hhi_passive', 'hhi_passive_buy', 'hhi_passive_sell',
    'hhi_volume',
]


def aggregate_all():
    """Агрегировать все файлы HI2 в дневной отчёт."""
    logger.info('Агрегация дневных HI2...')
    
    if not DATA_DIR.exists():
        logger.error('Папка с данными не найдена')
        return
    
    all_rows = []
    
    for f in sorted(DATA_DIR.glob('*_hi2.parquet')):
        ticker = f.stem.replace('_hi2', '')
        df = pl.read_parquet(f)
        
        if df.is_empty():
            continue
        
        # Группируем по дате
        # Все 11 метрик HI2
        agg_exprs = [
            pl.when(pl.col('metric') == m).then(pl.col('value')).last().alias(m)
            for m in METRICS
        ]
        if 'ticker' not in df.columns and 'secid' in df.columns:
            df = df.rename({'secid': 'ticker'})
        daily = df.group_by(['ticker', 'engine', 'tradedate']).agg(agg_exprs)
        
        all_rows.append(daily)
        logger.info(f'  {ticker}: {len(daily)} дней')
    
    if not all_rows:
        logger.warning('Нет данных для агрегации')
        return
    
    df_all = pl.concat(all_rows).sort(['ticker', 'tradedate'])
    df_all.write_parquet(OUTPUT_FILE)
    
    logger.info(f'Сохранено: {OUTPUT_FILE}')
    logger.info(f'  Всего строк: {len(df_all)}')
    logger.info(f'  Тикеров: {df_all["ticker"].n_unique()}')


if __name__ == '__main__':
    aggregate_all()
