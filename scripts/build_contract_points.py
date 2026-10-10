#!/usr/bin/env python3
"""
Построение contract_points.json
================================
Для фьючерсов: point_value = STEPPRICE × MINSTEP (MOEX ISS)
Для акций:     point_value = 1.0

Ключи — короткие коды (как в БД роботов).
"""
import json
import sqlite3
from pathlib import Path

import requests

# === Пути ===
ROOT = Path('/root/finlab')
TICKERS_CONFIG = ROOT / 'FinLabPy' / 'DataCollectors' / 'tickers_config.json'
CONTRACT_CACHE = ROOT / 'FinLabPy' / 'DataCollectors' / 'contract_cache.json'
OUTPUT_FILE = ROOT / 'robots' / 'contract_points.json'
PAIRS_DB = ROOT / 'robots' / 'pairs_robot.db'
FUTURES_DB = ROOT / 'robots' / 'futures_robot.db'

# === MOEX ISS ===
ISS_FORTS = 'https://iss.moex.com/iss/engines/futures/markets/forts/securities.json'

# === Исключения (ручные значения) ===
EXCEPTIONS = {
    'MX': 1.0,  # Индекс МосБиржи — стоимость пункта 1₽ (STEPPRICE=25, MINSTEP=25 не работает)
}

# === Вечные фьючерсы (нет в contract_cache, но SECID = тикер) ===
PERPETUAL_FUTURES = {
    'CNYRUBF', 'EURRUBF', 'GAZPF', 'GLDRUBF',
    'IMOEXF', 'RGBIF', 'SBERF', 'USDRUBF',
}


def fetch_moex_futures():
    """Загрузить все фьючерсы FORTS с MOEX ISS."""
    r = requests.get(ISS_FORTS, params={'iss.meta': 'off'}, timeout=30)
    r.raise_for_status()
    data = r.json()
    sec = data['securities']
    cols = sec['columns']
    rows = [dict(zip(cols, row)) for row in sec['data']]
    return {row['SECID']: row for row in rows if row.get('SECID')}


def get_tickers_from_dbs():
    """Собрать все тикеры из обоих роботов."""
    tickers = set()

    # Парный
    if PAIRS_DB.exists():
        conn = sqlite3.connect(PAIRS_DB)
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT leg_a_ticker FROM positions WHERE leg_a_ticker IS NOT NULL")
        tickers |= {r[0] for r in cur.fetchall()}
        cur.execute("SELECT DISTINCT leg_b_ticker FROM positions WHERE leg_b_ticker IS NOT NULL")
        tickers |= {r[0] for r in cur.fetchall()}
        conn.close()

    # Фьючерсный
    if FUTURES_DB.exists():
        conn = sqlite3.connect(FUTURES_DB)
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT ticker FROM futures_positions")
        tickers |= {r[0] for r in cur.fetchall()}
        conn.close()

    return tickers


def main():
    print('=' * 60)
    print('Построение contract_points.json')
    print('=' * 60)

    # Загружаем конфиг
    with open(TICKERS_CONFIG) as f:
        cfg = json.load(f)
    futures_cfg = set(cfg.get('futures', []))
    stocks_cfg = set(cfg.get('stocks', []))

    # Тикеры из БД
    # Тикеры из tickers_config.json (НЕ из БД)
    db_tickers = futures_cfg | stocks_cfg
    print(f'\nТикеров из config: {len(db_tickers)}')

    # Загружаем кэш контрактов
    with open(CONTRACT_CACHE) as f:
        cache = json.load(f)

    # Загружаем MOEX ISS
    print('Загружаю MOEX ISS...')
    moex = fetch_moex_futures()
    print(f'  Фьючерсов на ISS: {len(moex)}')

    # Строим результат
    result = {}
    errors = []

    # 1) Фьючерсы — только из БД
    print('\n--- Фьючерсы (из БД) ---')
    futures_in_db = futures_cfg & db_tickers
    for short in sorted(futures_in_db):
        if short in EXCEPTIONS:
            result[short] = EXCEPTIONS[short]
            print(f'  {short:<10} исключение → {EXCEPTIONS[short]}')
            continue

        # Ищем SECID
        if short in PERPETUAL_FUTURES:
            secid = short  # вечный фьючерс — SECID = короткий код
        else:
            cache_entry = cache.get(short)
            if cache_entry:
                secid = cache_entry.get('code')
            else:
                errors.append(f'{short}: нет в contract_cache и не в PERPETUAL')
                continue

        info = moex.get(secid)
        if not info:
            errors.append(f'{short} ({secid}): нет на MOEX ISS')
            continue

        step = info.get('STEPPRICE')
        minstep = info.get('MINSTEP')
        if step is None or minstep is None:
            errors.append(f'{short} ({secid}): нет STEPPRICE/MINSTEP')
            continue

        # point_value = рублей за 1 пункт = STEPPRICE / MINSTEP
        pv = round(step / minstep, 6) if minstep else step
        result[short] = pv
        print(f'  {short:<10} {secid:<10} STEP={step:<12} MINSTEP={minstep:<10} → {pv}')

    # 2) Акции — только из БД
    print('\n--- Акции (из БД) ---')
    stocks_in_db = stocks_cfg & db_tickers
    for short in sorted(stocks_in_db):
        result[short] = 1.0
        print(f'  {short}: 1.0')

    # Сохраняем
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(result, f, indent=4, ensure_ascii=False, sort_keys=True)

    print(f'\n✅ Сохранено: {len(result)} тикеров')
    print(f'   Фьючерсов: {len(futures_in_db)}')
    print(f'   Акций: {len(stocks_in_db)}')

    if errors:
        print(f'\n⚠️ Ошибки ({len(errors)}):')
        for e in errors[:20]:
            print(f'  {e}')

    # Проверка — все тикеры из БД должны быть
    missing = [t for t in db_tickers if t not in result]
    if missing:
        print(f'\n🔴 НЕ НАЙДЕНО ({len(missing)}): {sorted(missing)}')
    else:
        print('\n🎉 ВСЕ тикеры из БД покрыты!')


if __name__ == '__main__':
    main()
