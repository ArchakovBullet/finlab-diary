"""
Торговый робот фьючерсов на сигналах Algopack (TradeStats + FutOI).
=====================================================================
Логика:
- Сигналы: vol_net, val_net, trades_net, pr_body, sec_pr_range (TradeStats)
          yur_buy_ratio, yur_long_ratio, fiz_buy_ratio (FutOI)
- Вход: score >= 2 (2+ сигнала сработало)
- Выход: стоп (ATR×3.2), безубыток, time-exit (5д), обратный сигнал
- Горизонт: 5 дней
- Бумажный режим
- LQDT-сравнение
"""
import json
import sqlite3
import time
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import numpy as np

sys.path.insert(0, '/root/finlab/FinLabPy')

from dotenv import load_dotenv
from My_Indicators.algopack_signals import get_combined_signal
from Utils.lqdt_benchmark import compare_to_lqdt, beat_lqdt_rate

# ========== КОНФИГ ==========
ROOT = Path('/root/finlab')
DATA_ROOT = ROOT / 'data'
DB_PATH = ROOT / 'robots' / 'futures_algopack_robot.db'
COMMAND_FILE = ROOT / 'robots' / 'futures_algopack_robot_command.txt'
STATE_FILE = ROOT / 'robots' / 'futures_algopack_robot_state.json'

load_dotenv(ROOT / '.env')
VK_TOKEN = os.getenv('VK_TOKEN', '')
VK_GROUP_ID = os.getenv('VK_GROUP_ID', '497763452')

# Стоимость пункта
CONTRACT_POINTS_PATH = ROOT / 'robots' / 'contract_points.json'
try:
    with open(CONTRACT_POINTS_PATH) as _f:
        CONTRACT_POINTS = json.load(_f)
except Exception:
    CONTRACT_POINTS = {}

# Тикеры: 22 фьючерса (пересечение TradeStats + FutOI)
# RI исключён (аномальные показатели point_value). Данные собираются, но не торгуем.
TICKERS = [
    'BR', 'CE', 'CNYRUBF', 'CR', 'ED', 'EURRUBF', 'FF', 'GAZPF',
    'GD', 'GLDRUBF', 'IMOEXF', 'MX', 'OJ', 'PD', 'PT',
    'SBERF', 'SI', 'SV', 'USDRUBF', 'VI', 'W4',
]

# ========== ИНДИВИДУАЛЬНЫЕ СТОПЫ (из futures_robot.py) ==========
def load_stop_config():
    cfg_file = ROOT / 'robots' / 'stop_config.json'
    if not cfg_file.exists():
        return {}, {}, 1.5
    try:
        import json as _json_sc
        with open(cfg_file) as f:
            cfg = _json_sc.load(f)
        return (
            cfg.get('individual', {}),
            cfg.get('individual_be', {}),
            cfg.get('BE_MOVE_ATR', 1.5),
        )
    except Exception as e:
        print(f"⚠️ Ошибка чтения stop_config.json: {e}")
        return {}, {}, 1.5


STOP_ATR_INDIVIDUAL, STOP_BE_INDIVIDUAL, STOP_BE_DEFAULT = load_stop_config()


def get_stop_mult(ticker):
    """Множитель ATR для тикера (стоп)."""
    return STOP_ATR_INDIVIDUAL.get(ticker, STOP_ATR_MULT)


def get_be_move(ticker):
    """Множитель ATR для безубытка."""
    return STOP_BE_INDIVIDUAL.get(ticker, STOP_BE_DEFAULT)


# ========== КОНСТАНТЫ ==========
MAX_POSITIONS = 15  # было 10
STOP_ATR_MULT = 3.2
BE_MOVE_ATR = 1.5
BE_ENABLED = False  # Временно отключено 01.10.2026 — проверяем точку входа
BE_TARGET_MULT = 1.002
BE_EPS = 0.002
COOLDOWN_HOURS = 8  # как в futures_robot.py (whipsaw protection)
HOLD_DAYS = 5  # горизонт сигнала
DEPOSIT = 100000
CHECK_INTERVAL = 600  # 10 мин (было 3600)
STOP_CHECK_INTERVAL = 600
SCORE_MIN = 3  # минимум сигналов для входа (было 2)


def send_vk_message(message):
    """VK-уведомление (без блокировки)."""
    if not VK_TOKEN:
        return
    try:
        import vk_api
        vk = vk_api.VkApi(token=VK_TOKEN)
        vk.method('messages.send', {
            'user_id': VK_GROUP_ID,
            'message': message,
            'random_id': int(time.time() * 1000),
        })
    except Exception as e:
        print(f"⚠️ VK: {e}")


# ========== ПРОВЕРКА СВЕЖЕСТИ (из futures_robot.py) ==========
FRESHNESS_THRESHOLDS = {
    'M10': 2, 'H1': 4, 'H4': 25, 'D1': 25,
    'tradestats': 24, 'futoi': 24,
}


def is_moex_trading_day():
    """Проверить, что сегодня торговый день MOEX (с праздниками)."""
    now = datetime.now()
    # MOEX с 2026 торгует 7 дней в неделю (сб/вс — сокращённая сессия).
    # Выходные только по праздникам — списки ниже.
    no_trade_weekends = [
        (1,3),(1,4),(1,10),(1,11),(2,14),(2,15),(3,7),(3,8),
        (3,21),(3,22),(5,9),(5,10),(6,20),(6,21),(8,1),(8,2),
        (8,15),(8,16),(9,12),(9,13),(10,24),(10,25),(12,5),(12,6),
    ]
    no_trade_holidays = [
        (1,1),(1,2),(1,5),(1,6),(1,7),(1,8),(3,8),(5,9),(12,31),
    ]
    md = (now.month, now.day)
    if md in no_trade_weekends or md in no_trade_holidays:
        return False
    return True


def is_trading_time():
    """Проверить торговое время (10:00-18:00 МСК)."""
    from datetime import timezone, timedelta
    _now_msk = datetime.now(timezone(timedelta(hours=3)))
    _hour = _now_msk.hour
    return (10 <= _hour < 18)


def is_tradestats_fresh(ticker):
    """Проверить свежесть TradeStats. Возвращает (fresh: bool, age_hours: float|None)."""
    if not is_moex_trading_day():
        return True, 0.0
    now_hour = datetime.now().hour
    if now_hour < 10 or now_hour >= 19:
        return True, 0.0

    ts_file = DATA_ROOT / 'tradestats' / f'{ticker}_tradestats.parquet'
    if not ts_file.exists():
        return False, None
    try:
        df = pd.read_parquet(ts_file)
        if len(df) == 0:
            return False, None
        # ФИКС: используем tradedate + tradetime (полный timestamp),
        # а не только tradedate. Иначе age считается от 00:00.
        if 'tradedate' in df.columns and 'tradetime' in df.columns:
            _dt_series = pd.to_datetime(
                df['tradedate'].astype(str) + ' ' + df['tradetime'].astype(str),
                errors='coerce'
            )
            last_dt = _dt_series.max()
        elif 'tradedate' in df.columns:
            last_dt = pd.to_datetime(df['tradedate']).max()
        else:
            last_dt = None
        if last_dt is None or pd.isna(last_dt):
            return False, None
        if last_dt.tzinfo is not None:
            last_dt = last_dt.tz_localize(None)
        age_hours = (pd.Timestamp.now() - last_dt).total_seconds() / 3600
        return age_hours <= FRESHNESS_THRESHOLDS['tradestats'], age_hours
    except Exception as e:
        print(f"  ⚠️ {ticker}: ошибка проверки TradeStats: {e}")
        return False, None


def is_futoi_fresh(ticker):
    """Проверить свежесть FutOI. Возвращает (fresh: bool, age_hours: float|None)."""
    if not is_moex_trading_day():
        return True, 0.0
    now_hour = datetime.now().hour
    if now_hour < 10 or now_hour >= 19:
        return True, 0.0

    futoi_file = DATA_ROOT / 'futoi_1h' / 'futoi_1h.parquet'
    if not futoi_file.exists():
        return False, None
    try:
        df = pd.read_parquet(futoi_file)
        df = df[df['ticker'] == ticker]
        if len(df) == 0:
            return False, None
        last_row = df.iloc[-1]
        last_dt = None
        if 'hour' in df.columns:
            last_dt = pd.to_datetime(last_row['hour'])
        if last_dt is None:
            return False, None
        if last_dt.tzinfo is not None:
            last_dt = last_dt.tz_localize(None)
        age_hours = (pd.Timestamp.now() - last_dt).total_seconds() / 3600
        return age_hours <= FRESHNESS_THRESHOLDS['futoi'], age_hours
    except Exception as e:
        print(f"  ⚠️ {ticker}: ошибка проверки FutOI: {e}")
        return False, None


# ========== ЭКСПИРАЦИЯ (из futures_robot.py) ==========
LAST_TRADEDATE_CACHE_PATH = ROOT / 'robots' / 'contract_last_tradedate.json'
try:
    with open(LAST_TRADEDATE_CACHE_PATH, 'r') as _f:
        import json as _json_exp
        LAST_TRADEDATE_CACHE = _json_exp.load(_f)
except Exception:
    LAST_TRADEDATE_CACHE = {}


def get_last_tradedate(ticker):
    """Получить LASTTRADEDATE для тикера (из кеша)."""
    try:
        with open(ROOT / 'FinLabPy' / 'DataCollectors' / 'contract_cache.json') as _f:
            import json as _json_cc
            cc = _json_cc.load(_f)
        code = cc.get(ticker, {}).get('code')
    except Exception:
        code = None
    if not code:
        return None
    last_str = LAST_TRADEDATE_CACHE.get(code)
    if not last_str:
        return None
    try:
        return datetime.strptime(last_str, '%Y-%m-%d').date()
    except Exception:
        return None


# Вечные фьючерсы (нет экспирации, не закрываем по EXPIRY)
PERPETUAL_TICKERS = {
    'EURRUBF', 'USDRUBF', 'CNYRUBF', 'GLDRUBF',  # валютные/золото
    'SBERF', 'GAZPF', 'IMOEXF',                   # фондовые/индексные
}


def is_perpetual(ticker):
    """Вечный фьючерс — по явному списку."""
    return ticker in PERPETUAL_TICKERS


CONTRACT_CHANGE_LOG_PATH = ROOT / 'logs' / 'contract_change_log.json'


def is_new_contract(ticker, days=3):
    """Новый контракт доступен для входа только через N дней после смены."""
    if not CONTRACT_CHANGE_LOG_PATH.exists():
        return False
    try:
        log = json.loads(CONTRACT_CHANGE_LOG_PATH.read_text())
        entry = log.get(ticker)
        if not entry:
            return False
        changed_at = datetime.strptime(entry['changed_at'], '%Y-%m-%d')
        return (datetime.now() - changed_at).days < days
    except Exception as e:
        print(f"  ⚠️ {ticker}: ошибка is_new_contract: {e}")
        return False


def is_expiring_soon(ticker, days=2):
    """Проверить, истекает ли контракт в ближайшие N дней.
    Возвращает False для вечных фьючерсов (у них нет экспирации)."""
    from datetime import date as _date
    if is_perpetual(ticker):
        return False
    last = get_last_tradedate(ticker)
    if last is None:
        return False
    today = _date.today()
    days_left = (last - today).days
    return days_left <= days


def init_db():
    """Инициализировать БД."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS algopack_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            direction TEXT NOT NULL,
            volume REAL DEFAULT 1.0,
            entry_price REAL,
            entry_atr REAL,
            stop_price REAL,
            entry_score INTEGER,
            entry_time TEXT,
            status TEXT DEFAULT 'OPEN',
            exit_price REAL,
            exit_time TEXT,
            exit_reason TEXT,
            pnl REAL DEFAULT 0,
            signal_type TEXT,
            signal_details TEXT,
            filter_metrics TEXT,
            lqdt_diff REAL
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ticker ON algopack_positions(ticker)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON algopack_positions(status)')
    conn.commit()
    conn.close()


def read_command():
    """Прочитать команду из файла. Возвращает 'PAUSE' / 'STOP' / 'RESUME' / None."""
    if not COMMAND_FILE.exists():
        return None
    try:
        cmd = COMMAND_FILE.read_text().strip().upper()
        if not cmd:
            return None
        COMMAND_FILE.write_text('')
        print(f'📥 Команда: {cmd}')
        return cmd
    except Exception as e:
        print(f'⚠️ read_command: {e}')
        return None


def set_state(state: dict):
    """Сохранить состояние робота."""
    try:
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False))
    except Exception as e:
        print(f'⚠️ set_state: {e}')


def get_state() -> dict:
    """Прочитать состояние робота."""
    if not STATE_FILE.exists():
        return {'paused': False}
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {'paused': False}


def graceful_shutdown():
    """Graceful shutdown: закрыть все открытые позиции по рынку, VK, exit."""
    print('\n🛑 GRACEFUL SHUTDOWN')
    send_vk_message('🛑Робот_фьючерсов: graceful shutdown, закрываю позиции...')
    open_positions = get_open_positions()
    if not open_positions:
        print('Нет открытых позиций')
        send_vk_message('🛑Робот_фьючерсов: shutdown завершён (позиций не было)')
        return
    closed = 0
    for pos in open_positions:
        pos_id = pos[0]; ticker = pos[1]; direction = pos[2]
        entry_price = pos[4]
        m10_file = DATA_ROOT / 'candles' / f'{ticker}_M10.parquet'
        if not m10_file.exists():
            continue
        try:
            df = pd.read_parquet(m10_file)
            if len(df) == 0:
                continue
            price = float(df['close'].iloc[-1])
            close_position(pos_id, ticker, direction, price, 'SHUTDOWN', entry_price, 1.0)
            closed += 1
        except Exception as e:
            print(f'  ❌ {ticker}: {e}')
    print(f'✅ Закрыто: {closed}')
    send_vk_message(f'🛑Робот_фьючерсов: shutdown завершён, закрыто {closed}')


def get_open_positions():
    """Получить открытые позиции."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM algopack_positions WHERE status = 'OPEN'")
    positions = cursor.fetchall()
    conn.close()
    return positions


def is_in_cooldown(ticker):
    """Проверить cooldown после стопа."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cutoff = (datetime.now() - timedelta(hours=COOLDOWN_HOURS)).strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("""
        SELECT COUNT(*) FROM algopack_positions
        WHERE ticker = ? AND status = 'CLOSED'
          AND exit_reason IN ('STOP', 'BREAKEVEN')
          AND exit_time >= ?
    """, (ticker, cutoff))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0


def calc_atr(df, period=14):
    """ATR."""
    high = df['high'].astype(float)
    low = df['low'].astype(float)
    close = df['close'].astype(float)
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean().iloc[-1]


def get_atr(ticker):
    """ATR по D1."""
    f = DATA_ROOT / 'candles' / f'{ticker}_D1.parquet'
    if not f.exists():
        return None
    try:
        df = pd.read_parquet(f)
        if len(df) < 20:
            return None
        return float(calc_atr(df))
    except Exception:
        return None


def open_position(ticker, direction, signal_data, price, atr):
    """Открыть позицию."""
    if not is_moex_trading_day():
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    _stop_mult = get_stop_mult(ticker)
    if direction == 'LONG':
        stop_price = price - atr * _stop_mult
    else:
        stop_price = price + atr * _stop_mult

    signal_type = 'combined'
    signal_details = json.dumps(signal_data.get('tradestats', {}).get('signals', {}) or {})
    filter_metrics = json.dumps(signal_data.get('tradestats', {}).get('weak_metrics', {}) or {})

    cursor.execute('''
        INSERT INTO algopack_positions
            (ticker, direction, volume, entry_price, entry_atr, stop_price,
             entry_score, entry_time, signal_type, signal_details, filter_metrics)
        VALUES (?, ?, 1.0, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        ticker, direction, price, atr, stop_price,
        signal_data.get('score', 0),
        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        signal_type, signal_details, filter_metrics
    ))
    conn.commit()
    conn.close()

    emoji = '🟢' if direction == 'LONG' else '🔴'
    message = f"🤖Робот_фьючерсов: {emoji} {direction} {ticker}: score={signal_data.get('score')}, price={price:.4f}, stop={stop_price:.4f}"
    send_vk_message(message)
    print(f"✅ {message}")


def close_position(position_id, ticker, direction, exit_price, reason, entry_price, volume):
    """Закрыть позицию."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # PnL с учётом point_value (фьючерсы)
    point_value = CONTRACT_POINTS.get(ticker, 1.0)
    if direction == 'LONG':
        pnl = (exit_price - entry_price) * point_value * volume
    else:
        pnl = (entry_price - exit_price) * point_value * volume

    # LQDT diff
    cursor.execute('SELECT entry_time FROM algopack_positions WHERE id = ?', (position_id,))
    row = cursor.fetchone()
    lqdt_diff = None
    if row:
        entry_time = row[0]
        exit_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            lqdt = compare_to_lqdt(entry_time, exit_time, 0, deposit=DEPOSIT, pnl=pnl)
            if lqdt['diff'] is not None:
                lqdt_diff = lqdt['diff']
        except Exception:
            pass

    cursor.execute('''
        UPDATE algopack_positions SET
            status = 'CLOSED', exit_time = ?, exit_price = ?, pnl = ?, exit_reason = ?, lqdt_diff = ?
        WHERE id = ?
    ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), exit_price, pnl, reason, lqdt_diff, position_id))
    conn.commit()
    conn.close()

    emoji = '🟢' if pnl > 0 else '🔴'
    lqdt_str = f", LQDT={lqdt_diff:+.2f}%" if lqdt_diff is not None else ""
    message = f"🤖Робот_фьючерсов: ЗАКРЫТИЕ {ticker}: PnL={pnl:+.2f}₽ ({reason}){lqdt_str} {emoji}"
    send_vk_message(message)
    print(f"✅ {message}")


def check_stops_only():
    """Проверка стопов по M10 (high/low) + time-exit."""
    if not is_moex_trading_day():
        return

    open_positions = get_open_positions()
    if not open_positions:
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    closed_count = 0
    for pos in open_positions:
        pos_id = pos[0]
        ticker = pos[1]
        direction = pos[2]
        entry_price = pos[4]
        entry_atr = pos[5]
        stop_price = pos[6] if pos[6] is not None else None
        entry_time = pos[8]

        if not entry_atr or entry_atr <= 0:
            continue

        # Time-exit (5 дней)
        try:
            entry_dt = pd.to_datetime(entry_time)
            days_held = (datetime.now() - entry_dt).days
            if days_held >= HOLD_DAYS:
                # Закрываем по последней цене M10
                m10_file = DATA_ROOT / 'candles' / f'{ticker}_M10.parquet'
                if m10_file.exists():
                    df = pd.read_parquet(m10_file)
                    if len(df) > 0:
                        last_price = float(df['close'].iloc[-1])
                        close_position(pos_id, ticker, direction, last_price, 'TIME_EXIT', entry_price, 1.0)
                        closed_count += 1
                        print(f'⏰ {ticker}: TIME_EXIT по {last_price:.4f}')
                        continue
        except Exception:
            pass

        # Стоп по M10
        m10_file = DATA_ROOT / 'candles' / f'{ticker}_M10.parquet'
        if not m10_file.exists():
            continue

        try:
            df = pd.read_parquet(m10_file)
            if len(df) == 0:
                continue
            last = df.iloc[-1]
            low = float(last['low'])
            high = float(last['high'])

            if stop_price is None:
                stop_price = entry_price - entry_atr * STOP_ATR_MULT if direction == 'LONG' else entry_price + entry_atr * STOP_ATR_MULT

            # Безубыток
            _be_target = entry_price * BE_TARGET_MULT
            if BE_ENABLED:
                _be_move = get_be_move(ticker)
                if direction == 'LONG':
                    if high >= entry_price + entry_atr * _be_move:
                        if stop_price < _be_target:
                            stop_price = _be_target
                            cursor.execute('UPDATE algopack_positions SET stop_price = ? WHERE id = ?', (stop_price, pos_id))
                            conn.commit()
                            print(f'🔒 {ticker}: стоп в BE+комиссия ({stop_price:.4f})')
                else:  # SHORT
                    if low <= entry_price - entry_atr * _be_move:
                        if stop_price > _be_target:
                            stop_price = _be_target
                            cursor.execute('UPDATE algopack_positions SET stop_price = ? WHERE id = ?', (stop_price, pos_id))
                            conn.commit()
                            print(f'🔒 {ticker}: стоп в BE+комиссия ({stop_price:.4f})')

            # Срабатывание стопа
            if direction == 'LONG' and low <= stop_price:
                _be_eps = entry_price * BE_EPS
                _is_breakeven = abs(stop_price - entry_price) < _be_eps
                reason = 'BREAKEVEN' if _is_breakeven else 'STOP'
                close_position(pos_id, ticker, direction, stop_price, reason, entry_price, 1.0)
                closed_count += 1
            elif direction == 'SHORT' and high >= stop_price:
                _be_eps = entry_price * BE_EPS
                _is_breakeven = abs(stop_price - entry_price) < _be_eps
                reason = 'BREAKEVEN' if _is_breakeven else 'STOP'
                close_position(pos_id, ticker, direction, stop_price, reason, entry_price, 1.0)
                closed_count += 1
        except Exception as e:
            print(f'  ❌ {ticker}: {e}')

    conn.close()
    if closed_count:
        print(f'  ✅ Закрыто: {closed_count}')


def main():
    print("=" * 60)
    print("🤖 ALGOPACK ROBOT |", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("=" * 60)
    print(f"Тикеров: {len(TICKERS)}")
    print(f"MAX_POSITIONS: {MAX_POSITIONS}")
    print(f"SCORE_MIN: {SCORE_MIN}")
    print(f"HOLD_DAYS: {HOLD_DAYS}")
    print("=" * 60)

    init_db()

    # ===== Проверка команд (PAUSE/STOP/RESUME) =====
    cmd = read_command()
    state = get_state()
    if cmd == 'PAUSE':
        state['paused'] = True
        set_state(state)
        print('⏸️ PAUSED — новые позиции не открываются')
        send_vk_message('⏸️Робот_фьючерсов: пауза')
    elif cmd == 'STOP':
        state['paused'] = False
        set_state(state)
        print('🛑 STOP — graceful shutdown')
        graceful_shutdown()
        raise SystemExit(0)
    elif cmd == 'RESUME':
        state['paused'] = False
        set_state(state)
        print('▶️ RESUMED')
        send_vk_message('▶️Робот_фьючерсов: возобновление')

    if not is_moex_trading_day():
        print('⏸️ Неторговый день — только стопы')
        check_stops_only()
        return

    if not is_trading_time():
        print('⏰ Вне торгового времени (10:00–18:00) — только стопы')
        check_stops_only()
        return

    if state.get('paused'):
        print('⏸️ На паузе — только проверка стопов')
        check_stops_only()
        return

    open_positions = get_open_positions()
    open_tickers = {p[1] for p in open_positions}
    print(f'\nОткрыто: {len(open_positions)}/{MAX_POSITIONS}')

    # Проверка экспирации — закрыть позиции за 2 дня
    for pos in open_positions:
        _pos_id, _ticker, _direction = pos[0], pos[1], pos[2]
        if is_expiring_soon(_ticker, days=2):
            print(f'  ⏰ {_ticker}: экспирация через ≤2 дн. — закрываю')
            try:
                _m10 = DATA_ROOT / 'candles' / f'{_ticker}_M10.parquet'
                if _m10.exists():
                    _df_m10 = pd.read_parquet(_m10)
                    if len(_df_m10) > 0:
                        _exit_price = float(_df_m10['close'].iloc[-1])
                        _entry_price = pos[4]
                        close_position(_pos_id, _ticker, _direction, _exit_price, 'EXPIRY', _entry_price, 1.0)
            except Exception as _e:
                print(f'    ❌ {_ticker}: {_e}')

    # Сканирование
    for ticker in TICKERS:
        if len(open_positions) >= MAX_POSITIONS:
            print(f'⛔ Лимит позиций ({MAX_POSITIONS})')
            break
        if ticker in open_tickers:
            continue
        if is_in_cooldown(ticker):
            print(f'  ⏸️ {ticker}: cooldown')
            continue
        if is_expiring_soon(ticker, days=2):
            print(f'  ⏰ {ticker}: экспирация ≤2 дн. — пропуск')
            continue
        if is_new_contract(ticker, days=3):
            print(f'  ⏰ {ticker}: новый контракт <3 дн. — пропуск')
            continue
        _ts_fresh, _ts_age = is_tradestats_fresh(ticker)
        if not _ts_fresh:
            _age_str = f'{_ts_age:.1f}ч' if _ts_age else 'нет данных'
            print(f'  ⚠️ {ticker}: TradeStats устарел ({_age_str}) — пропуск')
            continue
        _fo_fresh, _fo_age = is_futoi_fresh(ticker)
        if not _fo_fresh:
            _age_str = f'{_fo_age:.1f}ч' if _fo_age else 'нет данных'
            print(f'  ⚠️ {ticker}: FutOI устарел ({_age_str}) — пропуск')
            continue

        try:
            sig = get_combined_signal(ticker)
            if not sig['direction'] or sig['score'] < SCORE_MIN:
                continue

            # ATR
            atr = get_atr(ticker)
            if not atr or atr <= 0:
                continue

            # Цена (M10 close)
            m10_file = DATA_ROOT / 'candles' / f'{ticker}_M10.parquet'
            if not m10_file.exists():
                continue
            df = pd.read_parquet(m10_file)
            if len(df) == 0:
                continue
            price = float(df['close'].iloc[-1])

            open_position(ticker, sig['direction'], sig, price, atr)
            open_tickers.add(ticker)
            open_positions.append((None, ticker))
        except Exception as e:
            print(f'  ❌ {ticker}: {e}')

    print("\n✅ Проверка завершена")


INTERRUPT = False

INTERRUPT = False

if __name__ == '__main__':
    import signal as _signal

    def _on_sigterm(signum, frame):
        print(f'\n📥 Получен SIGTERM — завершение без закрытия позиций')
        raise SystemExit(0)

    def _on_sigusr1(signum, frame):
        global INTERRUPT
        INTERRUPT = True
        print(f'\n📥 Получен SIGUSR1 — прерывание sleep, читаю команду')

    _signal.signal(_signal.SIGTERM, _on_sigterm)
    _signal.signal(_signal.SIGINT, _on_sigterm)
    _signal.signal(_signal.SIGUSR1, _on_sigusr1)

    while True:
        try:
            main()
            print('Ожидание 10 мин (read_command каждые 30 сек)...')
            for i in range(20):  # 20 × 30 = 600 сек = 10 мин
                # sleep 30 сек, но прерывается SIGUSR1 (INTERRUPT)
                INTERRUPT = False
                for _s in range(30):
                    if INTERRUPT:
                        break
                    time.sleep(1)
                # Проверка команды каждые 30 сек (или сразу после SIGUSR1)
                cmd = read_command()
                if cmd == 'PAUSE':
                    state = get_state(); state['paused'] = True; set_state(state)
                    print('⏸️ PAUSED')
                    send_vk_message('⏸️Робот_фьючерсов: пауза')
                    break
                elif cmd == 'STOP':
                    state = get_state(); state['paused'] = False; set_state(state)
                    graceful_shutdown()
                    raise SystemExit(0)
                elif cmd == 'RESUME':
                    state = get_state(); state['paused'] = False; set_state(state)
                    print('▶️ RESUMED')
                    break
                check_stops_only()
                print(f'  [{i+1}/20] Стопы проверены')
        except SystemExit:
            raise
        except KeyboardInterrupt:
            print('🛑 Остановлено')
            graceful_shutdown()
            break
        except Exception as e:
            print(f'❌ Ошибка: {e}')
            time.sleep(60)
