"""
Ежедневный сборщик данных FutOI (открытые позиции физ/юр лиц)
Сохраняет в Parquet для компактности и скорости
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import polars as pl
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Retry-сессия (DNS/сеть)
_session = requests.Session()
_retry = Retry(total=5, backoff_factor=1.0, status_forcelist=[500,502,503,504,429], allowed_methods=["GET"])
_session.mount('https://', HTTPAdapter(max_retries=_retry))
_session.mount('http://', HTTPAdapter(max_retries=_retry))

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'FinLabPy'))

from MOEXPy.MOEXPy import MOEXPy
from FinLabPy.Utils import setup_logger

logger = setup_logger('futoi_collector')

# Только реально торгуемые фьючерсы MOEX (VTBRF и LKOHF не торгуются)
def _load_tickers():
    import json
    cfg_path = Path(__file__).parent / 'futoi_tickers_config.json'
    if cfg_path.exists():
        with open(cfg_path) as f:
            cfg = json.load(f)
        return cfg.get('futures', ['GLDRUBF', 'SBERF', 'GAZPF', 'IMOEXF', 'CNYRUBF'])
    return ['GLDRUBF', 'SBERF', 'GAZPF', 'IMOEXF', 'CNYRUBF']

TICKERS = _load_tickers()
DATA_DIR = project_root / 'data' / 'futoi'
LOOKBACK_DAYS = 5


def _resolve_full_code(short_code):
    import json, requests
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
        r = _session.get(url, timeout=10)
        data = r.json()["securities"]
        cols = data["columns"]
        rows = data["data"]
        secid_idx = cols.index("SECID")
        sectype_idx = cols.index("SECTYPE")
        date_idx = cols.index("LASTTRADEDATE")
        active = []
        for row in rows:
            if row[sectype_idx].upper() == short_code.upper():
                try:
                    last_trade = datetime.strptime(str(row[date_idx])[:10], '%Y-%m-%d').strftime('%Y-%m-%d')
                    if last_trade > today:
                        active.append((last_trade, row[secid_idx]))
                except ValueError:
                    continue
        if active:
            active.sort()
            full_code = active[0][1]
            cache[short_code] = {"code": full_code, "date": today}
            with open(cache_file, "w") as f:
                json.dump(cache, f)
            return full_code
    except requests.exceptions.RequestException as e:
        logger.warning(f'Ошибка запроса контракта {short_code}: {e}')
    except (KeyError, IndexError) as e:
        logger.warning(f'Ошибка парсинга контракта {short_code}: {e}')
    return short_code


def collect_futoi(ticker: str, api: MOEXPy) -> pl.DataFrame:
    """Собрать данные FutOI за LOOKBACK_DAYS"""
    dt_till = datetime.now()
    dt_from = dt_till - timedelta(days=LOOKBACK_DAYS)

    try:
        raw_data = api.get_futoi(ticker, dt_from, dt_till)

        data_rows = raw_data.get('futoi', {}).get('data', [])
        columns = raw_data.get('futoi', {}).get('columns', [])

        if not data_rows:
            logger.warning(f"{ticker}: нет данных")
            return pl.DataFrame()

        col_idx = {name: i for i, name in enumerate(columns)}

        rows = []
        skipped = 0
        for row in data_rows:
            if len(row) < len(columns):
                skipped += 1
                continue
            pos_short_val = row[col_idx['pos_short']]
            rows.append({
                'sess_id': row[col_idx['sess_id']],
                'seqnum': row[col_idx['seqnum']],
                'tradedate': str(row[col_idx['tradedate']])[:10],
                'tradetime': str(row[col_idx['tradetime']]),
                'ticker': row[col_idx['ticker']],
                'clgroup': row[col_idx['clgroup']],
                'pos': int(row[col_idx['pos']]),
                'pos_long': int(row[col_idx['pos_long']]),
                'pos_short': abs(int(pos_short_val)) if pos_short_val else 0,
                'pos_long_num': int(row[col_idx['pos_long_num']]),
                'pos_short_num': int(row[col_idx['pos_short_num']]),
            })

        if skipped > 0:
            logger.warning(f"{ticker}: пропущено {skipped} коротких строк")

        df = pl.DataFrame(rows)
        logger.info(f"{ticker}: загружено {len(df)} записей")
        return df

    except Exception as e:
        logger.error(f"{ticker}: ошибка - {e}")
        return pl.DataFrame()


def merge_with_existing(new_df: pl.DataFrame, filepath: Path) -> pl.DataFrame:
    """Объединить новые данные с существующими, удалить дубли"""
    if not filepath.exists():
        return new_df

    existing = pl.read_parquet(filepath)

    key_cols = ['ticker', 'tradedate', 'tradetime', 'clgroup']
    existing_keys = existing.select(key_cols)
    new_unique = new_df.join(existing_keys, on=key_cols, how='anti')

    merged = pl.concat([existing, new_unique])
    logger.info(f"  Было: {len(existing)}, Новых: {len(new_unique)}, Стало: {len(merged)}")
    return merged


def main():
    logger.info("=" * 60)
    logger.info("ЗАПУСК СБОРЩИКА FutOI")
    logger.info(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Читаем токен из .env если нет в окружении
    token = os.getenv('MOEX_TOKEN')
    if not token:
        from dotenv import load_dotenv
        load_dotenv('/root/finlab/.env')
        token = os.getenv('MOEX_TOKEN')
    if not token:
        logger.error('MOEX_TOKEN не установлен')
        return
    api = MOEXPy(token=token)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    total_new = 0

    for ticker in TICKERS:
        logger.info(f"\n--- {ticker} ---")
        new_df = collect_futoi(ticker, api)

        if new_df.is_empty():
            continue

        filepath = DATA_DIR / f"{ticker}_futoi.parquet"
        merged = merge_with_existing(new_df, filepath)
        merged.write_parquet(filepath)

        total_new += len(new_df)

    logger.info(f"\nГотово! Всего новых записей: {total_new}")
    logger.info(f"Данные в: {DATA_DIR}")


if __name__ == '__main__':
    main()
