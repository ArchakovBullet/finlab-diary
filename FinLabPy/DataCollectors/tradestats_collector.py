"""
Сборщик TradeStats для вертикального профиля объёма (Volume Profile)
Сохраняет агрегированные объёмы по ценовым уровням
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import json
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Создаём сессию с retry
session = requests.Session()
retry = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=[500, 502, 503, 504],
    allowed_methods=["GET"]
)
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)
session.mount('https://', adapter)

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from MOEXPy.MOEXPy import MOEXPy
from FinLabPy.Utils import setup_logger

logger = setup_logger('tradestats_collector')

# ========== КОНФИГ ==========
# Вечные фьючерсы (те, что уже есть в проекте)
FUTURES = ['CNYRUBF', 'EURRUBF', 'GAZPF', 'GLDRUBF', 'IMOEXF', 'SBERF', 'USDRUBF', 'BR', 'CE', 'CR', 'ED', 'FF', 'GD', 'MX', 'OJ', 'PD', 'PT', 'RI', 'SI', 'SV', 'VI', 'W4']

# Акции (для которых есть Super Candles)
STOCKS = ['AFLT', 'SBER', 'GAZP', 'GMKN', 'LKOH', 'HYDR', 'IRAO', 'PLZL', 'ROSN', 'TATN', 'VTBR', 'AFKS', 'T', 'YDEX', 'RUAL', 'MAGN', 'OZON', 'SMLT', 'MTLR', 'UGLD', 'NVTK', 'ALRS', 'SNGSP', 'VKCO', 'MGNT', 'X5', 'TRNFP', 'CHMF', 'SVCB', 'SGZH', 'NLMK', 'SPBE', 'SBERP', 'DOMRF', 'MOEX', 'SNGS', 'MVID', 'POSI', 'MTSS', 'PHOR', 'SIBN', 'UPRO', 'ASTR', 'ENPG', 'HHRU', 'RNFT', 'RTKM', 'WUSH', 'TATNP']

DATA_DIR = Path('/root/finlab/data/tradestats')
DATA_DIR.mkdir(parents=True, exist_ok=True)

def _resolve_full_code(short_code):
    cache_file = Path(__file__).parent / "contract_cache.json"
    cache = {}
    if cache_file.exists():
        with open(cache_file) as f:
            cache = json.load(f)
    today = datetime.now().strftime("%Y-%m-%d")
    if short_code in cache and cache[short_code].get("date") == today:
        return cache[short_code]["code"]
    try:
        url = "https://iss.moex.com/iss/engines/futures/markets/forts/securities.json"
        r = session.get(url, timeout=30)
        data = r.json()["securities"]
        cols = data["columns"]
        rows = data["data"]
        secid_idx = cols.index("SECID")
        sectype_idx = cols.index("SECTYPE")
        date_idx = cols.index("LASTTRADEDATE")
        active = []
        for row in rows:
            if row[sectype_idx].upper() == short_code.upper() and row[date_idx] > today:
                active.append((row[date_idx], row[secid_idx]))
        if active:
            active.sort()
            full_code = active[0][1]
            cache[short_code] = {"code": full_code, "date": today}
            with open(cache_file, "w") as f:
                json.dump(cache, f)
            return full_code
    except:
        pass
    return short_code

def collect_tradestats(ticker, board):
    """Собрать TradeStats для одного тикера"""
    logger.info(f"  {ticker} ({board})...")
    
    moex = MOEXPy()
    
    # Определяем даты: последние 30 дней
    dt_till = datetime.now()
    dt_from = dt_till - timedelta(days=30)
    
    try:
        api_ticker = _resolve_full_code(ticker) if ticker not in ['CNYRUBF', 'USDRUBF', 'EURRUBF', 'GLDRUBF', 'GAZPF', 'SBERF', 'IMOEXF'] else ticker
        result = moex.get_tradestats(api_ticker, dt_from, dt_till, board)
        
        if result is None or 'data' not in result:
            logger.warning("нет данных")
            return 0
        
        # Преобразуем в DataFrame
        if isinstance(result['data'], dict) and 'data' in result['data']:
            df = pd.DataFrame(result['data']['data'], columns=result['data']['columns'])
        else:
            df = pd.DataFrame(result['data'])
        
        if df.empty:
            logger.warning("пустой ответ")
            return 0
        
        # Сохраняем
        file_path = DATA_DIR / f"{ticker}_tradestats.parquet"
        
        if file_path.exists():
            existing = pd.read_parquet(file_path)
            combined = pd.concat([existing, df], ignore_index=True)
            combined = combined.drop_duplicates(subset=['tradedate', 'tradetime'])
            combined.to_parquet(file_path, index=False)
        else:
            df.to_parquet(file_path, index=False)
        
        logger.info(f"+{len(df)} записей")
        return len(df)
    
    except Exception as e:
        logger.error(f"ошибка: {e}")
        return 0

def main():
    logger.info("=" * 60)
    logger.info(f"СБОРЩИК TRADESTATS | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    total = 0
    
    # Фьючерсы (board='RFUD')
    logger.info("\n=== ФЬЮЧЕРСЫ ===")
    for ticker in FUTURES:
        count = collect_tradestats(ticker, 'RFUD')
        total += count
    
    # Акции (board='TQBR')
    logger.info("\n=== АКЦИИ ===")
    for ticker in STOCKS:
        count = collect_tradestats(ticker, 'TQBR')
        total += count
    
    logger.info("\n" + "=" * 60)
    logger.info(f"ГОТОВО! Всего новых записей: {total}")
    logger.info(f"Данные в: {DATA_DIR}")
    logger.info("=" * 60)

if __name__ == '__main__':
    main()
