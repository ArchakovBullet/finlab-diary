"""
Сборщик свечей через MOEXPy для фьючерсов, акций и индексов
Сохраняет в Parquet по таймфреймам M10, H1, D1
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'FinLabPy'))

from MOEXPy.MOEXPy import MOEXPy
from FinLabPy.Utils import setup_logger

logger = setup_logger('candles_collector')

# ========== КОНФИГ ==========
# Инструменты с указанием board
def _load_tickers():
    '''Загрузить тикеры из tickers_config.json'''
    import json
    cfg_path = Path(__file__).parent / 'tickers_config.json'
    if cfg_path.exists():
        with open(cfg_path) as f:
            cfg = json.load(f)
        futures = {}
        for t in cfg.get('futures', []):
            futures[t] = 'RFUD'
        stocks = {}
        for t in cfg.get('stocks', []):
            stocks[t] = 'TQBR'
        return futures, stocks
    # Fallback
    return {'CNYRUBF': 'RFUD', 'SBERF': 'RFUD'}, {'SBER': 'TQBR'}

FUTURES, STOCKS = _load_tickers()

CORRELATIONS = {
    'RTS': 'RFUD',   # Индекс РТС (фьючерс)
    'BRENT': 'RFUD'  # Нефть Brent (фьючерс)
}

ALL_TICKERS = {**FUTURES, **STOCKS, **CORRELATIONS}

# Таймфреймы: MOEX interval
TIMEFRAMES = {
    'M10': 10,
    'H1': 60,
    'D1': 24
}

DATA_DIR = Path('/root/finlab/data/candles')
DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_full_code(short_code):
    import json, requests
    from datetime import datetime
    from pathlib import Path
    
    # Маппинг коротких кодов фьючерсов к SECTYPE
    short_to_sectype = {
        'MM': 'MXI', 'RM': 'RTSM', 'HO': 'HOME', 'OG': 'OGI', 'MA': 'MMI',
        'FN': 'FNI', 'CS': 'CNI', 'RB': 'RGBI', 'RF': 'RUONIA', 'MY': 'MOEXCNY',
        'IP': 'IPO', 'EH': 'ETH', 'BT': 'BTC', 'S3': 'SOL', 'XR': 'XRP',
        'TX': 'TRX', 'BC': 'BNB', 'BM': 'BRM', 'WT': 'WTI', 'NG': 'NG',
        'NR': 'NGM', 'GL': 'GL', 'GN': 'GOLDM', 'LD': 'PLDM', 'LT': 'PLTM',
        'S1': 'SILVM', 'S2': 'SL', 'NC': 'NICKEL', 'ZC': 'ZINC', 'AN': 'ALUM',
        'SA': 'SUGR', 'Su': 'SUGAR', 'CC': 'COCOA', 'KC': 'COFFEE', '92': 'AI92',
        '95': 'AI95', 'DL': 'DTL', 'Eu': 'Eu', 'ER': 'EURM', 'UM': 'USDM',
        'TY': 'TRY', 'HK': 'HKD', 'AE': 'AED', 'I2': 'INR', 'KZ': 'KZT',
        'AR': 'AMD', 'BY': 'BYN', 'GU': 'GBPU', 'CA': 'UCAD',
        'CF': 'UCHF', 'JP': 'UJPY', 'TR': 'UTRY', 'UC': 'UCNY', 'UT': 'UKZT',
        'IN': 'UINR', 'EC': 'ECAD', 'EG': 'EGBP', 'EJ': 'EJPY',
        'RR': 'RUON', 'MF': '1MFR',
    }
    
    try:
        cache_file = Path(__file__).parent / "contract_cache.json"
        cache = {}
        if cache_file.exists():
            with open(cache_file) as f:
                cache = json.load(f)
        today = datetime.now().strftime("%Y-%m-%d")
        if short_code in cache and cache[short_code].get("date") == today:
            return cache[short_code]["code"]
        url = "https://iss.moex.com/iss/engines/futures/markets/forts/securities.json"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return short_code
        data = r.json()["securities"]
        cols = data["columns"]
        rows = data["data"]
        secid_idx = cols.index("SECID")
        sectype_idx = cols.index("SECTYPE")
        date_idx = cols.index("LASTTRADEDATE")
        active = []
        for row in rows:
            # Проверяем по короткому коду или по маппингу SECTYPE
            sectype_lookup = short_to_sectype.get(short_code, short_code)
            if row[sectype_idx].upper() == sectype_lookup.upper():
                if row[date_idx] > today:
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


def main():
    logger.info("=" * 60)
    logger.info(f"СБОРЩИК СВЕЧЕЙ | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
        
    moex = MOEXPy()
    total = 0
    
    for ticker, board in ALL_TICKERS.items():
        logger.info(f"\n{ticker} ({board}):")
        
        for tf_name, interval in TIMEFRAMES.items():
            logger.info(f"  {tf_name}...")
            
            # Определяем дату начала
            api_ticker = get_full_code(ticker) if board == "RFUD" else ticker
            file_path = DATA_DIR / f"{ticker}_{tf_name}.parquet"
            # Ищем существующий файл (может быть с коротким или полным кодом)
            existing_files = list(DATA_DIR.glob(f"{ticker}_*.parquet")) + list(DATA_DIR.glob(f"{api_ticker}_*.parquet"))
            existing_files = [f for f in existing_files if f.stem.endswith(tf_name)]
            if existing_files:
                file_path = existing_files[0]  # Берём первый найденный
                existing = pd.read_parquet(file_path)
                if 'begin' in existing.columns:
                    existing['begin'] = pd.to_datetime(existing['begin'])
                if not existing.empty:
                    dt_from = existing['begin'].max()
                else:
                    dt_from = datetime.now() - timedelta(days=365)
            else:
                dt_from = datetime.now() - timedelta(days=30)
            
            dt_till = datetime.now()
            
            if dt_from >= dt_till:
                logger.info("нет новых данных")
                continue
            
            try:
                result = moex.get_candles(board, api_ticker, dt_from, dt_till, interval)
                
                if result is None or 'candles' not in result or len(result['candles']['data']) == 0:
                    logger.warning("нет данных")
                    continue
                
                # Преобразуем в DataFrame
                columns = result['candles']['columns']
                data = result['candles']['data']
                df = pd.DataFrame(data, columns=columns)
                
                # Переименовываем колонки
                col_map = {'open':'open','close':'close','high':'high','low':'low','value':'value','volume':'volume','begin':'begin','end':'end'}
                df = df.rename(columns=col_map)
                df['begin'] = pd.to_datetime(df['begin'])

                if file_path.exists():
                    existing = pd.read_parquet(file_path)
                    existing['begin'] = pd.to_datetime(existing['begin'])
                    
                    existing_begins = set(existing['begin'])
                    new_rows = ~df['begin'].isin(existing_begins)
                    new_df = df[new_rows]
                    
                    if len(new_df) == 0:
                        logger.info("нет новых данных")
                        continue
                    
                    combined = pd.concat([existing, new_df], ignore_index=True)
                    combined = combined.sort_values('begin')
                    combined = combined.drop_duplicates(subset=['begin'])
                    combined.to_parquet(file_path, index=False)
                    logger.info(f"+{len(new_df)} свечей")
                    total += len(new_df)
                else:
                    df.to_parquet(file_path, index=False)
                    logger.info(f"+{len(df)} свечей")
                    total += len(df)
            except Exception as e:
                logger.error(f"ошибка: {e}")
    
    logger.info("\n" + "=" * 60)
    logger.info(f"ГОТОВО! Всего новых свечей: {total}")
    logger.info(f"Данные в: {DATA_DIR}")
    logger.info("=" * 60)

if __name__ == '__main__':
    main()


