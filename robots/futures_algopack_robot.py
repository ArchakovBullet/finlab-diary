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

# ========== КОНСТАНТЫ ==========
MAX_POSITIONS = 10
STOP_ATR_MULT = 3.2
BE_MOVE_ATR = 1.5
BE_TARGET_MULT = 1.002
BE_EPS = 0.002
COOLDOWN_HOURS = 8  # как в futures_robot.py (whipsaw protection)
HOLD_DAYS = 5  # горизонт сигнала
DEPOSIT = 100000
CHECK_INTERVAL = 3600
STOP_CHECK_INTERVAL = 600
SCORE_MIN = 2  # минимум сигналов для входа


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


def is_moex_trading_day():
    """Проверить, торговый ли день (не сб/вс)."""
    wd = datetime.now().weekday()
    return wd < 5


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
    send_vk_message('🛑 ALGOPACK: graceful shutdown, закрываю позиции...')
    open_positions = get_open_positions()
    if not open_positions:
        print('Нет открытых позиций')
        send_vk_message('🛑 ALGOPACK: shutdown завершён (позиций не было)')
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
    send_vk_message(f'🛑 ALGOPACK: shutdown завершён, закрыто {closed}')


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

    if direction == 'LONG':
        stop_price = price - atr * STOP_ATR_MULT
    else:
        stop_price = price + atr * STOP_ATR_MULT

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
    message = f"🤖 ALGOPACK: {emoji} {direction} {ticker}: score={signal_data.get('score')}, price={price:.4f}, stop={stop_price:.4f}"
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
    message = f"🤖 ALGOPACK: ЗАКРЫТИЕ {ticker}: PnL={pnl:+.2f}₽ ({reason}){lqdt_str} {emoji}"
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
            if direction == 'LONG':
                if high >= entry_price + entry_atr * BE_MOVE_ATR:
                    if stop_price < _be_target:
                        stop_price = _be_target
                        cursor.execute('UPDATE algopack_positions SET stop_price = ? WHERE id = ?', (stop_price, pos_id))
                        conn.commit()
                        print(f'🔒 {ticker}: стоп в BE+комиссия ({stop_price:.4f})')
            else:  # SHORT
                if low <= entry_price - entry_atr * BE_MOVE_ATR:
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

    if not is_moex_trading_day():
        print('⏸️ Неторговый день — только стопы')
        check_stops_only()
        return

    open_positions = get_open_positions()
    open_tickers = {p[1] for p in open_positions}
    print(f'\nОткрыто: {len(open_positions)}/{MAX_POSITIONS}')

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


if __name__ == '__main__':
    import signal as _signal
    def _on_sigterm(signum, frame):
        print(f'\n📥 Получен SIGTERM')
        graceful_shutdown()
        raise SystemExit(0)
    _signal.signal(_signal.SIGTERM, _on_sigterm)
    _signal.signal(_signal.SIGINT, _on_sigterm)

    while True:
        try:
            main()
            print('Ожидание 1 час (стопы каждые 10 мин)...')
            for i in range(6):
                time.sleep(STOP_CHECK_INTERVAL)
                check_stops_only()
                print(f'  [{i+1}/6] Стопы проверены')
        except SystemExit:
            raise
        except KeyboardInterrupt:
            print('🛑 Остановлено')
            graceful_shutdown()
            break
        except Exception as e:
            print(f'❌ Ошибка: {e}')
            time.sleep(60)
