"""
Агрегатор 4-часовых свечей (H4) для фьючерсов из M10.
Группирует 10-минутные свечи в 4-часовые блоки: 07:00-11:00, 11:00-15:00, 15:00-19:00.
"""
import sys, json
from pathlib import Path
from datetime import date, timedelta

project_root = Path(__file__).parent.parent.parent if '__file__' in globals() else Path('.').absolute()
sys.path.insert(0, str(project_root))

import polars as pl
from FinLabPy.Utils import setup_logger

logger = setup_logger('futures_h4')

DATA_DIR = project_root / 'data' / 'candles'

H4_BLOCKS = [
    ('07:00:00', '11:00:00', '07:00'),
    ('11:00:00', '15:00:00', '11:00'),
    ('15:00:00', '19:00:00', '15:00'),
]


def aggregate_all():
    logger.info('Агрегация фьючерсов в H4...')

    cfg_path = Path(__file__).parent / 'tickers_config.json'
    if not cfg_path.exists():
        logger.error('Конфиг не найден')
        return

    with open(cfg_path) as f:
        cfg = json.load(f)
    futures = cfg.get('futures', [])

    total_new = 0

    for ticker in futures:
        m10_file = DATA_DIR / f'{ticker}_M10.parquet'
        if not m10_file.exists():
            continue

        try:
            df = pl.read_parquet(m10_file)
        except:
            continue

        if df.is_empty() or 'begin' not in df.columns:
            continue

        # Приводим begin к datetime и извлекаем дату/время
        df = df.with_columns([
            pl.col('begin').cast(pl.Utf8).str.slice(0, 10).alias('tradedate'),
            pl.col('begin').cast(pl.Utf8).str.slice(11, 8).alias('tradetime'),
        ])

        df_recent = df

        h4_rows = []
        for block_start, block_end, label in H4_BLOCKS:
            block_df = df_recent.filter(
                (pl.col('tradetime') >= block_start) & (pl.col('tradetime') < block_end)
            )
            if block_df.is_empty():
                continue

            # Группируем по дате (ключевое исправление!)
            for trade_date in block_df['tradedate'].unique():
                day_block = block_df.filter(pl.col('tradedate') == trade_date)
                if day_block.is_empty():
                    continue
                h4_rows.append({
                    'ticker': ticker,
                    'tradedate': trade_date,
                    'block': label,
                    'open': day_block['open'].first(),
                    'high': day_block['high'].max(),
                    'low': day_block['low'].min(),
                    'close': day_block['close'].last(),
                    'volume': day_block['volume'].sum() if 'volume' in day_block.columns else 0,
                })

        if not h4_rows:
            continue

        df_h4 = pl.DataFrame(h4_rows).sort(['tradedate', 'block'])

        h4_file = DATA_DIR / f'{ticker}_H4.parquet'
        if h4_file.exists():
            try:
                existing = pl.read_parquet(h4_file)
                # Проверяем формат: старые файлы имеют колонку 'begin' вместо 'tradedate'
                if 'begin' in existing.columns and 'tradedate' not in existing.columns:
                    existing = existing.with_columns(
                        pl.col('begin').cast(pl.Utf8).str.slice(0, 10).alias('tradedate')
                    )
                if 'tradedate' in existing.columns:
                    new_dates = df_h4['tradedate'].unique()
                    existing = existing.filter(~pl.col('tradedate').is_in(new_dates))
                    df_h4 = pl.concat([existing, df_h4])
            except Exception:
                pass

        df_h4.write_parquet(h4_file)
        logger.info(f'  {ticker}: {len(h4_rows)} блоков')
        total_new += len(h4_rows)

    if total_new == 0:
        logger.warning('Нет данных для H4-агрегации')
    else:
        logger.info(f'Готово! Всего блоков: {total_new}')


if __name__ == '__main__':
    aggregate_all()
