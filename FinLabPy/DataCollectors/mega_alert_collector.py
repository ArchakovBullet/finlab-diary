"""Сборщик Mega Alerts (торговые аномалии) через AlgoPack API."""
import os
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
import json

project_root = Path(__file__).parent.parent.parent if '__file__' in dir() else Path('.').absolute()
sys.path.insert(0, str(project_root))

import polars as pl
import requests
from MOEXPy.MOEXPy import MOEXPy
from FinLabPy.Utils import setup_logger

logger = setup_logger('mega_alert_collector')


class MegaAlertCollector:
    """Сборщик Mega Alerts для списка тикеров."""
    
    def __init__(self, api, data_dir: Path = None):
        self.api = api
        self.data_dir = data_dir or project_root / 'data' / 'mega_alerts'
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def _resolve_full_code(short_code):
        """Получить полный код фьючерса (ближайший активный контракт)."""
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
            r = requests.get(url, timeout=10)
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
    
    def collect_all(self):
        """Собрать Mega Alerts для всех тикеров."""
        logger.info(f'Начало сбора Mega Alerts за {date.today()}')
        
        cfg_path = Path(__file__).parent / 'tickers_config.json'
        if cfg_path.exists():
            with open(cfg_path) as f:
                cfg = json.load(f)
            tickers = cfg.get('stocks', []) + cfg.get('futures', [])
        else:
            tickers = ['SBER', 'GAZP', 'LKOH', 'ROSN']
        
        total_alerts = 0
        
        for ticker in tickers:
            try:
                alerts = self._collect_one(ticker)
                total_alerts += len(alerts)
                logger.info(f'  {ticker}: {len(alerts)} алертов')
            except Exception as e:
                logger.error(f'  {ticker}: ОШИБКА — {e}')
        
        logger.info(f'Готово! Всего алертов: {total_alerts}')
    
    def _collect_one(self, ticker: str) -> list:
        """Собрать Mega Alerts для одного тикера за 7 дней."""
        cfg_path = Path(__file__).parent / 'tickers_config.json'
        engine = 'stocks'
        api_ticker = ticker
        
        if cfg_path.exists():
            with open(cfg_path) as f:
                cfg = json.load(f)
            if ticker in cfg.get('futures', []):
                engine = 'futures'
                api_ticker = self._resolve_full_code(ticker)
        
        all_rows = []
        
        # Собираем за 7 дней по одному дню
        end_date = date.today()
        for days_back in range(7):
            target_date = end_date - timedelta(days=days_back)
            try:
                raw = self.api.get_alerts(engine, api_ticker, date=target_date)
                if raw and 'data' in raw and 'data' in raw['data']:
                    alerts_data = raw['data']
                    columns = alerts_data.get('columns', [])
                    data = alerts_data.get('data', [])
                    if data:
                        for row in data:
                            row_dict = dict(zip(columns, row))
                            all_rows.append(row_dict)
            except:
                pass
        
        if not all_rows:
            return []
        
        # Сохраняем (всегда перезапись)
        file_path = self.data_dir / f'{ticker}_alerts.parquet'
        
        # Нормализация типов перед созданием DataFrame
        if not all_rows:
            return []

        all_cols = sorted(set().union(*(r.keys() for r in all_rows)))

        normalized = []
        for row in all_rows:
            new_row = {}
            for col in all_cols:
                val = row.get(col)
                if val is None:
                    new_row[col] = None
                elif isinstance(val, (int, float)):
                    new_row[col] = float(val)
                elif isinstance(val, str):
                    try:
                        new_row[col] = float(val)
                    except ValueError:
                        new_row[col] = val
                else:
                    new_row[col] = str(val)
            normalized.append(new_row)

        try:
            df = pl.DataFrame(normalized)
            # Дедуп: один сигнал в день по ключу (secid, tradedate, tradetime, alert_type, threshold, value)
            dedup_cols = [c for c in ['secid','tradedate','tradetime','alert_type','threshold','value'] if c in df.columns]
            if dedup_cols:
                before = len(df)
                df = df.unique(subset=dedup_cols, keep='first')
                after = len(df)
                if before != after:
                    logger.info(f'  {ticker}: дедуп {before} → {after}')
            df.write_parquet(file_path)
        except Exception as e:
            logger.warning(f'{ticker}: ошибка создания DataFrame: {e}')
            return all_rows
        return all_rows


if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv('/root/finlab/.env')
    api = MOEXPy(token=os.getenv('MOEX_TOKEN'))
    collector = MegaAlertCollector(api)
    collector.collect_all()
