"""Сборщик индексов и секторов MOEX"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Создаём сессию с retry
session = requests.Session()
retry = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=[500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)
session.mount('https://', adapter)
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from Utils.Logger import setup_logger

logger = setup_logger('sector_indices')

DATA_DIR = Path('/root/finlab/data/sector_indices')
DATA_DIR.mkdir(exist_ok=True)

# Индексы для сбора (тикер MOEX -> имя файла)
INDICES = {
    'IMOEX': 'IMOEX_D1.parquet',
    'RVI': 'RVI_D1.parquet',
    'RGBI': 'RGBI_D1.parquet',
    # Отраслевые (расширенный список — 11 индексов)
    'MOEXOG': 'MOEXOG_D1.parquet',   # Нефть и газ
    'MOEXFN': 'MOEXFN_D1.parquet',   # Финансы
    'MOEXMM': 'MOEXMM_D1.parquet',   # Металлы и добыча
    'MOEXEU': 'MOEXEU_D1.parquet',   # Электроэнергетика
    # MOEXTL удалён 09.10.2026 — делистинг на MOEX, телеком теперь в MOEXIT
    'MOEXCH': 'MOEXCH_D1.parquet',   # Химия
    'MOEXCN': 'MOEXCN_D1.parquet',   # Потребительский
    'MOEXIT': 'MOEXIT_D1.parquet',   # IT & TL
    'MOEXRE': 'MOEXRE_D1.parquet',   # Недвижимость
    'MOEXTN': 'MOEXTN_D1.parquet',   # Транспорт
    'MOEXINN': 'MOEXINN_D1.parquet', # Инновации
}

def collect_index(ticker, filename):
    """Собрать свечи индекса через ISS MOEX API"""
    url = f'https://iss.moex.com/iss/engines/stock/markets/index/securities/{ticker}/candles.json'
    params = {
        'from': (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'),
        'till': datetime.now().strftime('%Y-%m-%d'),
        'interval': 24  # D1
    }
    
    import time
    r = None
    for attempt in range(1, 4):
        try:
            r = session.get(url, params=params, timeout=30)
            if r.status_code == 200:
                break
            else:
                logger.warning(f'{ticker}: HTTP {r.status_code} (попытка {attempt}/3)')
        except Exception as e:
            logger.warning(f'{ticker}: ошибка (попытка {attempt}/3): {e}')
        if attempt < 3:
            time.sleep(attempt * 5)

    try:
        if r is None or r.status_code != 200:
            logger.error(f'{ticker}: не удалось получить данные после 3 попыток')
            return 0
        
        data = r.json()
        if 'candles' not in data:
            logger.warning(f'{ticker}: нет данных')
            return 0
        
        candles = data['candles']
        cols = candles['columns']
        rows = candles['data']
        
        if not rows:
            return 0
        
        df = pd.DataFrame(rows, columns=cols)
        cols_lower = [c.lower() for c in cols]
        df = pd.DataFrame(rows, columns=cols_lower)
        df['begin'] = pd.to_datetime(df['begin'])
        
        filepath = DATA_DIR / filename
        
        if filepath.exists():
            existing = pd.read_parquet(filepath)
            existing['begin'] = pd.to_datetime(existing['begin'])
            existing_starts = set(existing['begin'])
            new_df = df[~df['begin'].isin(existing_starts)]
            if len(new_df) > 0:
                combined = pd.concat([existing, new_df], ignore_index=True)
                combined = combined.sort_values('begin')
                combined.to_parquet(filepath, index=False)
                logger.info(f'{ticker}: +{len(new_df)} новых свечей, всего {len(combined)}')
                return len(new_df)
            else:
                logger.info(f'{ticker}: нет новых')
                return 0
        else:
            df.to_parquet(filepath, index=False)
            logger.info(f'{ticker}: создан новый файл, {len(df)} свечей')
            return len(df)
    except Exception as e:
        logger.error(f'{ticker}: {e}')
        return 0

def main():
    logger.info('Сбор секторов и индексов...')
    total = 0
    for ticker, filename in INDICES.items():
        n = collect_index(ticker, filename)
        total += n
    logger.info(f'Готово! Новых свечей: {total}')

if __name__ == '__main__':
    main()
