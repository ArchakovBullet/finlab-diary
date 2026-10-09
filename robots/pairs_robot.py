"""
Торговый робот парной торговли (бумажный режим)
===================================================
Работает в фоновом режиме, проверяет сигналы по парам,
открывает/закрывает позиции в SQLite, отправляет VK-уведомления.

Управление:
- Файл-команда: /root/finlab/robots/robot_command.txt
  Команды: START, STOP, PAUSE, RESUME
- Кнопки Старт/Стоп в дашборде записывают команды в этот файл
"""
import json
import sqlite3
import time
import os
import sys
import pickle
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

# ========== КОНФИГ ==========
ROOT = Path('/root/finlab')
load_dotenv(ROOT / '.env')

# Загружаем справочник стоимости пункта
try:
    import json as _json
    with open(CONTRACT_POINTS_PATH, 'r') as _f:
        CONTRACT_POINTS = _json.load(_f)
except:
    CONTRACT_POINTS = {}
CONFIG_PATH = ROOT / 'FinLabPy' / 'My_Indicators' / 'pairs_config.json'

# ========== ML-ФИЛЬТР ==========
ML_MODELS_DIR = ROOT / 'models'
_ML_MODELS = {}


def load_ml_models():
    """Загрузить ML-модели из models/*.pkl в _ML_MODELS."""
    global _ML_MODELS
    _ML_MODELS = {}
    if not ML_MODELS_DIR.exists():
        print('⚠️ models/ не найдена — ML-фильтр отключён')
        return
    for pkl in sorted(ML_MODELS_DIR.glob('lr_*.pkl')):
        try:
            with open(pkl, 'rb') as f:
                d = pickle.load(f)
            pair = d['pair_name']
            _ML_MODELS[pair] = {
                'model': d['model'],
                'scaler': d['scaler'],
                'features': d['features'],
                'window': d['window'],
                'resid_window': d['resid_window'],
                'avg_auc': d.get('avg_auc', 0),
            }
            print(f'✅ ML: {pair} (auc={d.get("avg_auc", 0):.3f}, n={d.get("n_signals", 0)})')
        except Exception as e:
            print(f'❌ ML: {pkl.name} — ошибка: {e}')
    print(f'📦 ML-моделей загружено: {len(_ML_MODELS)}')


def ml_filter(pair_name, features_dict):
    """ML-фильтр. Возвращает (pass_bool, proba_or_None).

    Если модели нет — (True, None) — пропускаем без фильтра.
    Если proba >= 0.5 — (True, proba) — PASS.
    Если proba < 0.5  — (False, proba) — BLOCK.
    """
    if pair_name not in _ML_MODELS:
        return True, None
    m = _ML_MODELS[pair_name]
    try:
        feats = [features_dict.get(f, 0.0) for f in m['features']]
        X = m['scaler'].transform([feats])
        proba = float(m['model'].predict_proba(X)[0, 1])
        return (proba >= 0.5), proba
    except Exception as e:
        print(f'  ⚠️ ML filter error {pair_name}: {e}')
        return True, None


# ========== Загрузка тикеров (акции / фьючерсы) ==========
TICKERS_CONFIG_PATH = ROOT / 'FinLabPy' / 'DataCollectors' / 'tickers_config.json'
STOCKS_SET = set()
FUTURES_SET = set()

def _load_tickers():
    """Загрузить списки акций и фьючерсов."""
    global STOCKS_SET, FUTURES_SET
    try:
        import json as _json
        with open(TICKERS_CONFIG_PATH) as _f:
            _cfg = _json.load(_f)
        STOCKS_SET = set(_cfg.get('stocks', []))
        FUTURES_SET = set(_cfg.get('futures', []))
        print(f'✅ Загружено тикеров: акций={len(STOCKS_SET)}, фьючерсов={len(FUTURES_SET)}')
    except Exception as _e:
        print(f'⚠️ Ошибка загрузки tickers_config.json: {_e}')

def is_stock(ticker):
    """Проверить, что тикер — акция."""
    return ticker in STOCKS_SET

def is_futures(ticker):
    """Проверить, что тикер — фьючерс."""
    return ticker in FUTURES_SET

_load_tickers()
CANDLES_DIR = ROOT / 'data' / 'candles'
DB_PATH = ROOT / 'robots' / 'pairs_robot.db'
COMMAND_FILE = ROOT / 'robots' / 'robot_command.txt'
STATE_FILE = ROOT / 'robots' / 'robot_state.json'

# ========== TIME_EXIT ==========
MAX_HOLD_HOURS = 120   # Максимальное время удержания пары (5 дней)

# VK
VK_TOKEN = os.getenv('VK_TOKEN', '')
VK_GROUP_ID = os.getenv('VK_GROUP_ID', '497763452')

# Настройки робота
DEPOSIT = 100_000  # Виртуальный капитал
VOLUME_TYPE = 'contracts'  # contracts / contract_currency / deposit_percent
VOLUME = 1.0  # 1 контракт/акция
CHECK_INTERVALS = {'M10': 600, 'H1': 3600, 'H4': 14400}  # секунд
# ========== ПАРАМЕТРЫ ТОРГОВЛИ ==========
ENTRY_Z_DEFAULT = 3.0        # порог входа по Z-score (по умолчанию)
EXIT_Z_DEFAULT = 0.5         # порог выхода по Z-score
MAX_POSITIONS = 10           # максимум одновременных открытых пар
COOLDOWN_HOURS = 4           # пауза после убытка по паре (часы)


# Состояние свежести данных (сохраняется в файл, чтобы не спамить при перезапуске)
TF_FRESH_STATE_FILE = ROOT / 'robots' / 'tf_fresh_state.json'

# Кеш LASTTRADEDATE (общий с futures_robot)
LAST_TRADEDATE_CACHE_PATH = ROOT / 'robots' / 'contract_last_tradedate.json'
CONTRACT_CHANGE_LOG_PATH = ROOT / 'logs' / 'contract_change_log.json'
try:
    with open(LAST_TRADEDATE_CACHE_PATH, 'r') as _f:
        LAST_TRADEDATE_CACHE = json.load(_f)
except Exception:
    LAST_TRADEDATE_CACHE = {}


def get_last_tradedate(ticker):
    """Получить LASTTRADEDATE для тикера (из кеша)."""
    from datetime import datetime as _dt
    try:
        with open(ROOT / 'FinLabPy' / 'DataCollectors' / 'contract_cache.json') as _f:
            cc = json.load(_f)
        code = cc.get(ticker, {}).get('code')
    except Exception:
        code = None
    if not code:
        return None
    last_str = LAST_TRADEDATE_CACHE.get(code)
    if not last_str:
        return None
    try:
        return _dt.strptime(last_str, '%Y-%m-%d').date()
    except Exception:
        return None


def is_expiring_soon(ticker, days=2):
    """True, если контракт истекает в ближайшие N дней (только для фьючерсов)."""
    from datetime import date as _date
    last = get_last_tradedate(ticker)
    if last is None:
        return False  # не фьючерс или нет данных — не блокируем
    today = _date.today()
    days_left = (last - today).days
    return days_left <= days


def is_new_contract(ticker, days=3):
    """True, если контракт сменился менее N дней назад.
    Защита от нестабильности после rollover."""
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


def load_tf_fresh_state():
    """Загрузить состояние свежести из файла"""
    try:
        with open(TF_FRESH_STATE_FILE, 'r') as f:
            return json.load(f)
    except:
        return {'M10': True, 'H1': True, 'H4': True}

def save_tf_fresh_state(state):
    """Сохранить состояние свежести в файл"""
    with open(TF_FRESH_STATE_FILE, 'w') as f:
        json.dump(state, f)

TF_FRESH_STATE = load_tf_fresh_state()


def load_state() -> dict:
    """Загрузить состояние робота. Безопасный default: paused=True."""
    if not STATE_FILE.exists():
        return {'paused': True, 'running': False}
    try:
        state = json.loads(STATE_FILE.read_text())
        if 'paused' not in state:
            state['paused'] = True
        return state
    except Exception as e:
        print(f'  ⚠️ load_state: {e}')
        return {'paused': True, 'running': False}


def save_state(state: dict):
    """Сохранить состояние робота."""
    try:
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f'  ⚠️ save_state: {e}')

# Пороги свежести данных (в часах)
FRESHNESS_THRESHOLDS = {
    'M10': 3,
    'H1': 4,
    'H4': 25,
    'D1': 25,
}

def is_moex_trading_day():
    """Проверить, что сегодня торговый день MOEX (упрощённо, 2026).

    Сб (5) — ТОРГОВЫЙ (допсессия MOEX).
    Вс (6) — неторговый.
    Праздники — по спискам.
    """
    from datetime import datetime as _dt
    now = _dt.now()
    # Только Вс (6) — неторговый. Сб (5) — торговый (допсессия).
    if now.weekday() == 6:
        return False
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

def _get_last_candle_dt(df):
    """Универсально получить datetime последней свечи (max, а не iloc[-1])."""
    if len(df) == 0:
        return None

    # 1. begin (datetime)
    if 'begin' in df.columns:
        try:
            return pd.to_datetime(df['begin']).max()
        except Exception:
            pass

    # 2. tradedate + block (SuperCandles H4)
    if 'tradedate' in df.columns and 'block' in df.columns:
        try:
            df_sorted = df.sort_values(['tradedate', 'block'])
            last_date = str(df_sorted['tradedate'].iloc[-1])
            last_block = str(df_sorted['block'].iloc[-1])
            return pd.to_datetime(f'{last_date} {last_block}')
        except Exception:
            pass

    # 3. tradedate + tradetime (FutOI)
    if 'tradedate' in df.columns and 'tradetime' in df.columns:
        try:
            df_sorted = df.sort_values(['tradedate', 'tradetime'])
            last_date = str(df_sorted['tradedate'].iloc[-1])
            last_time = str(df_sorted['tradetime'].iloc[-1])
            return pd.to_datetime(f'{last_date} {last_time}')
        except Exception:
            pass

    # 4. tradedate (fallback)
    if 'tradedate' in df.columns:
        try:
            return pd.to_datetime(df['tradedate'].iloc[-1])
        except Exception:
            pass

    # 5. datetime
    if 'datetime' in df.columns:
        try:
            return pd.to_datetime(df['datetime'].iloc[-1])
        except Exception:
            pass

    return None


def is_tf_fresh(tf):
    """Проверить, что данные ТФ свежие (по дате последней свечи)."""
    from datetime import datetime as _dt

    if not is_moex_trading_day():
        return True

    # Вне торговых часов (до 10:00 или после 19:00 МСК) — не проверяем
    now_hour = _dt.now().hour
    if now_hour < 10 or now_hour >= 19:
        return True

    max_age_hours = FRESHNESS_THRESHOLDS.get(tf, 4)

    try:
        with open(CONFIG_PATH, 'r') as f:
            pairs_config = json.load(f)
    except Exception as e:
        print(f'  ⚠️ is_tf_fresh({tf}): ошибка чтения pairs_config: {e}')
        return False

    fresh_count = 0
    total_count = 0
    now = _dt.now()

    for pair_name in pairs_config.get('pairs', {}):
        if not pair_name.endswith(f'_{tf}'):
            continue
        cfg_pair = pairs_config['pairs'][pair_name]
        if not cfg_pair.get('enabled', False):
            continue  # не проверять отключённые
        base_pair = pair_name.replace(f'_{tf}', '')
        if '-' not in base_pair:
            continue

        ticker_a, ticker_b = base_pair.split('-')
        file_a = CANDLES_DIR / f'{ticker_a}_{tf}.parquet'
        file_b = CANDLES_DIR / f'{ticker_b}_{tf}.parquet'

        if not file_a.exists() or not file_b.exists():
            continue

        total_count += 1

        pair_fresh = True
        for f in [file_a, file_b]:
            try:
                df = pd.read_parquet(f)
                last_candle = _get_last_candle_dt(df)

                if last_candle is None:
                    print(f'  ⚠️ {f.name}: не найдена колонка с датой')
                    pair_fresh = False
                    break

                if last_candle.tzinfo is not None:
                    last_candle = last_candle.tz_localize(None)

                age_hours = (now - last_candle).total_seconds() / 3600
                if age_hours >= max_age_hours:
                    print(f'  ⚠️ {f.name}: age={age_hours:.1f}ч >= {max_age_hours}ч')
                    pair_fresh = False
                    break

            except Exception as e:
                print(f'  ❌ {f.name}: {e}')
                pair_fresh = False
                break

        if pair_fresh:
            fresh_count += 1

    if total_count == 0:
        print(f'  ✅ is_tf_fresh({tf}): нет активных пар — не блокируем')
        return True

    result = fresh_count >= total_count / 2
    print(f'  📊 is_tf_fresh({tf}): {fresh_count}/{total_count} свежих → {result}')
    return result

def init_db():
    """Создать таблицы в SQLite"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Таблица позиций
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pair_name TEXT NOT NULL,
            base_pair TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            direction TEXT NOT NULL,  -- LONG_SPREAD / SHORT_SPREAD
            volume REAL NOT NULL,
            entry_z REAL NOT NULL,
            entry_time TEXT NOT NULL,
            entry_price_a REAL,
            entry_price_b REAL,
            status TEXT DEFAULT 'OPEN',  -- OPEN / CLOSED
            exit_time TEXT,
            exit_z REAL,
            exit_price_a REAL,
            exit_price_b REAL,
            pnl REAL DEFAULT 0
        )
    ''')
    
    # Таблица сделок (журнал)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pair_name TEXT NOT NULL,
            base_pair TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            action TEXT NOT NULL,  -- OPEN / CLOSE
            direction TEXT,
            volume REAL,
            zscore REAL,
            price_a REAL,
            price_b REAL,
            pnl REAL DEFAULT 0,
            time TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ БД инициализирована")

# ========== РАСЧЁТ СИГНАЛОВ ==========
def calculate_correlation(df_a, df_b, window=20):
    """Рассчитать корреляцию Пирсона между close_a и close_b (последние window свечей)."""
    try:
        import numpy as np
        _time_col_a = 'begin' if 'begin' in df_a.columns else 'tradedate'
        _time_col_b = 'begin' if 'begin' in df_b.columns else 'tradedate'
        df_a_r = df_a[[_time_col_a, 'close']].rename(columns={_time_col_a: 'begin'})
        df_b_r = df_b[[_time_col_b, 'close']].rename(columns={_time_col_b: 'begin'})
        merged = pd.merge(df_a_r, df_b_r, on='begin', suffixes=('_a', '_b'))
        if len(merged) < window:
            return None
        # Конвертируем в float
        ca = merged['close_a'].apply(lambda x: float(x) if not isinstance(x, bytes) else 0.0)
        cb = merged['close_b'].apply(lambda x: float(x) if not isinstance(x, bytes) else 0.0)
        corr = ca.tail(window).corr(cb.tail(window))
        return float(corr) if not pd.isna(corr) else None
    except Exception as e:
        print(f"❌ Correlation error: {e}")
        return None


def calculate_zscore(df_a, df_b, window=20, use_coint=False, resid_window=60):
    """Z-score спреда.

    Если use_coint=True — rolling OLS residuals:
        log_a = beta * log_b + alpha + resid
        z-score по resid.
    Иначе — простой spread = log_a - log_b.
    """
    import numpy as np
    _ca = 'begin' if 'begin' in df_a.columns else 'tradedate'
    _cb = 'begin' if 'begin' in df_b.columns else 'tradedate'
    a = df_a[[_ca, 'close']].rename(columns={_ca: 'dt'})
    b = df_b[[_cb, 'close']].rename(columns={_cb: 'dt'})
    m = pd.merge(a, b, on='dt', suffixes=('_a', '_b')).sort_values('dt').reset_index(drop=True)
    m['close_a'] = m['close_a'].apply(lambda x: float(x) if not isinstance(x, bytes) else 0.0)
    m['close_b'] = m['close_b'].apply(lambda x: float(x) if not isinstance(x, bytes) else 0.0)
    m['log_a'] = np.log(m['close_a'].replace(0, np.nan))
    m['log_b'] = np.log(m['close_b'].replace(0, np.nan))

    if use_coint:
        # Rolling OLS residuals
        import numpy as _np
        try:
            from statsmodels.regression.linear_model import OLS as _OLS
            from statsmodels.tools import add_constant as _add_constant
        except ImportError:
            use_coint = False

    if use_coint:
        resid = []
        betas = []
        for i in range(len(m)):
            if i < resid_window:
                resid.append(_np.nan); betas.append(_np.nan); continue
            y = m['log_a'].iloc[i-resid_window:i].values
            x = _add_constant(m['log_b'].iloc[i-resid_window:i].values)
            try:
                model = _OLS(y, x).fit()
                beta = model.params[1]; alpha = model.params[0]
                r = m['log_a'].iloc[i] - beta * m['log_b'].iloc[i] - alpha
                resid.append(r); betas.append(beta)
            except Exception:
                resid.append(_np.nan); betas.append(_np.nan)
        m['resid'] = resid
        m['beta'] = betas
        m['spread'] = m['resid']
    else:
        m['spread'] = m['log_a'] - m['log_b']

    m['mean'] = m['spread'].rolling(window).mean()
    m['std'] = m['spread'].rolling(window).std()
    m['z'] = (m['spread'] - m['mean']) / m['std']
    # Rolling correlation для ML-фильтра (совпадает с ml_pairs_lr.py)
    if len(m) >= 50:
        m['corr'] = m['close_a'].rolling(50).corr(m['close_b'])
    else:
        m['corr'] = None

    return {
        'current_zscore': float(m['z'].iloc[-1]) if len(m) > 0 and not pd.isna(m['z'].iloc[-1]) else 0.0,
        'price_a': float(m['close_a'].iloc[-1]),
        'price_b': float(m['close_b'].iloc[-1]),
        'spread_trend': float(m['z'].iloc[-1] - m['z'].iloc[-2]) if len(m) > 1 and not pd.isna(m['z'].iloc[-1]) and not pd.isna(m['z'].iloc[-2]) else 0.0,
        'std': float(m['std'].iloc[-1]) if len(m) > 0 and not pd.isna(m['std'].iloc[-1]) else 0.0,
        'mean': float(m['mean'].iloc[-1]) if len(m) > 0 and not pd.isna(m['mean'].iloc[-1]) else 0.0,
        'beta': float(m['beta'].iloc[-1]) if 'beta' in m.columns and len(m) > 0 and not pd.isna(m['beta'].iloc[-1]) else 0.0,
        'corr': float(m['corr'].iloc[-1]) if 'corr' in m.columns and len(m) > 0 and m['corr'] is not None and not pd.isna(m['corr'].iloc[-1]) else 0.0,
    }



def send_vk_message(message):
    """Отправить сообщение в VK"""
    if not VK_TOKEN:
        print("❌ VK_TOKEN не настроен")
        return False
    
    url = 'https://api.vk.com/method/messages.send'
    params = {
        'access_token': VK_TOKEN,
        'peer_id': VK_GROUP_ID,
        'message': message,
        'random_id': 0,
        'v': '5.131'
    }
    r = requests.post(url, params=params, timeout=10)
    return r.status_code == 200

# ========== ЖУРНАЛ СДЕЛОК ==========
def log_trade(pair_name, base_pair, tf, action, direction, volume, zscore, price_a, price_b, pnl=0):
    """Записать сделку в SQLite"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO trades (pair_name, base_pair, timeframe, action, direction, volume, zscore, price_a, price_b, pnl, time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (pair_name, base_pair, tf, action, direction, volume, zscore, price_a, price_b, pnl, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()

# ========== ПОЗИЦИИ ==========
def get_open_positions():
    """Получить открытые позиции из БД"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM positions WHERE status = "OPEN"')
    positions = cursor.fetchall()
    conn.close()
    return positions

def open_position(pair_name, base_pair, tf, direction, volume, zscore, price_a, price_b):
    """Открыть позицию (две ноги)"""
    ticker_a, ticker_b = base_pair.split('-')
    
    if direction == 'SHORT_SPREAD':
        leg_a_dir = 'SELL'
        leg_b_dir = 'BUY'
    else:  # LONG_SPREAD
        leg_a_dir = 'BUY'
        leg_b_dir = 'SELL'

    # === ЗАЩИТА: запрет шорта по акциям (20.09.2026) ===
    # Определяем, какая нога в шорте (SELL)
    _short_ticker = ticker_a if leg_a_dir == 'SELL' else ticker_b
    if is_stock(_short_ticker):
        print(f'  ⏸️ {pair_name}: шорт по акции {_short_ticker} запрещён — пропуск')
        return
    
    conn = sqlite3.connect(DB_PATH)
    # Получаем contract_code и expiry_date для обеих ног
    contract_code_a = None
    contract_code_b = None
    expiry_date_a = None
    expiry_date_b = None
    try:
        with open(ROOT / 'FinLabPy' / 'DataCollectors' / 'contract_cache.json') as _f:
            _cc = json.load(_f)
        contract_code_a = _cc.get(ticker_a, {}).get('code')
        contract_code_b = _cc.get(ticker_b, {}).get('code')
    except Exception:
        pass
    _ltd_a = get_last_tradedate(ticker_a)
    if _ltd_a:
        expiry_date_a = _ltd_a.strftime('%Y-%m-%d')
    _ltd_b = get_last_tradedate(ticker_b)
    if _ltd_b:
        expiry_date_b = _ltd_b.strftime('%Y-%m-%d')

    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO positions (
            pair_name, base_pair, timeframe, direction, volume, 
            entry_z, entry_time, entry_price_a, entry_price_b,
            leg_a_ticker, leg_a_direction, leg_b_ticker, leg_b_direction,
            contract_code_a, contract_code_b, expiry_date_a, expiry_date_b
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        pair_name, base_pair, tf, direction, volume, 
        zscore, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
        price_a, price_b,
        ticker_a, leg_a_dir, ticker_b, leg_b_dir,
        contract_code_a, contract_code_b, expiry_date_a, expiry_date_b
    ))
    conn.commit()
    conn.close()
    
    # Журнал
    log_trade(pair_name, base_pair, tf, 'OPEN', direction, volume, zscore, price_a, price_b)
    
    # VK
    emoji = '🔴' if direction == 'SHORT_SPREAD' else '🟢'
    action = 'ШОРТ' if direction == 'SHORT_SPREAD' else 'ЛОНГ'
    message = f"🤖 ПАРНЫЙ-РОБОТ: {emoji} {action} {base_pair}_{tf}: Z={zscore:.2f}\n"
    message += f"  Нога A: {leg_a_dir} {ticker_a} @ {price_a:.2f}\n"
    message += f"  Нога B: {leg_b_dir} {ticker_b} @ {price_b:.2f}"
    send_vk_message(message)
    print(f"✅ Открыта позиция: {message}")

def close_position(position_id, pair_name, base_pair, tf, zscore, price_a, price_b):
    """Закрыть позицию (двухногая модель)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Получаем параметры позиции
    cursor.execute('SELECT direction, volume, entry_z, entry_price_a, entry_price_b, leg_a_ticker, leg_a_direction, leg_b_ticker, leg_b_direction FROM positions WHERE id = ?', (position_id,))
    pos = cursor.fetchone()
    if not pos:
        conn.close()
        return

    direction, volume, entry_z, entry_price_a, entry_price_b, leg_a_ticker, leg_a_direction, leg_b_ticker, leg_b_direction = pos

    # Безопасная конвертация
    def safe_float(val, default=0.0):
        if isinstance(val, bytes):
            try:
                return float(val.decode('utf-8', errors='ignore') or default)
            except (ValueError, UnicodeDecodeError):
                return default
        try:
            return float(val)
        except (TypeError, ValueError):
            return default

    entry_price_a = safe_float(entry_price_a)
    entry_price_b = safe_float(entry_price_b)
    price_a = safe_float(price_a)
    price_b = safe_float(price_b)

    # Расчёт PnL по ногам
    point_value_a = CONTRACT_POINTS.get(leg_a_ticker, 1.0) if leg_a_ticker else 1.0
    point_value_b = CONTRACT_POINTS.get(leg_b_ticker, 1.0) if leg_b_ticker else 1.0

    if leg_a_direction == 'SELL':
        leg_a_pnl = (entry_price_a - price_a) * point_value_a * volume
    else:
        leg_a_pnl = (price_a - entry_price_a) * point_value_a * volume

    if leg_b_direction == 'SELL':
        leg_b_pnl = (entry_price_b - price_b) * point_value_b * volume
    else:
        leg_b_pnl = (price_b - entry_price_b) * point_value_b * volume

    # Комиссия 0.28% (0.14% x 2) от номинала двух ног
    notional_a = abs(entry_price_a) * point_value_a * volume
    notional_b = abs(entry_price_b) * point_value_b * volume
    commission = (notional_a + notional_b) * 0.0028
    total_pnl = leg_a_pnl + leg_b_pnl - commission

    # PnL в пунктах (без учёта point_value)
    if leg_a_direction == 'SELL':
        leg_a_pnl_points = (entry_price_a - price_a) * volume
    else:
        leg_a_pnl_points = (price_a - entry_price_a) * volume

    if leg_b_direction == 'SELL':
        leg_b_pnl_points = (entry_price_b - price_b) * volume
    else:
        leg_b_pnl_points = (price_b - entry_price_b) * volume

    total_pnl_points = leg_a_pnl_points + leg_b_pnl_points

    # Обновляем позицию
    cursor.execute('''UPDATE positions SET 
        status = "CLOSED", exit_time = ?, exit_z = ?, exit_price_a = ?, exit_price_b = ?, 
        leg_a_pnl = ?, leg_b_pnl = ?, pnl = ?,
        leg_a_pnl_points = ?, leg_b_pnl_points = ?, total_pnl_points = ?
        WHERE id = ?''', (
        datetime.now().strftime('%Y-%m-%d %H:%M:%S'), zscore, price_a, price_b, 
        leg_a_pnl, leg_b_pnl, total_pnl,
        leg_a_pnl_points, leg_b_pnl_points, total_pnl_points,
        position_id))
    conn.commit()
    conn.close()

    # Журнал
    log_trade(pair_name, base_pair, tf, 'CLOSE', direction, volume, zscore, price_a, price_b, total_pnl)

    # VK
    emoji = '🟢' if total_pnl > 0 else '🔴'
    message = f"🤖 ПАРНЫЙ-РОБОТ: ЗАКРЫТИЕ {base_pair}_{tf}: PnL={total_pnl:+.2f}₽ (A: {leg_a_pnl:+.2f}₽, B: {leg_b_pnl:+.2f}₽) {emoji}"
    send_vk_message(message)
    print(f"✅ Закрыта позиция: {message}")

# ========== ПРОВЕРКА КОМАНД ==========
def process_command():
    """Проверить команду из файла"""
    if COMMAND_FILE.exists():
        cmd = COMMAND_FILE.read_text().strip().upper()
        if cmd:
            COMMAND_FILE.write_text('')
            return cmd
    return None

# ========== ОСНОВНОЙ ЦИКЛ ==========
def check_expiry():
    """Проверить приближающиеся экспирации. Закрывать пары за N дней."""
    if not is_moex_trading_day():
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, pair_name, base_pair, timeframe, direction, entry_price_a, entry_price_b,
               leg_a_ticker, leg_b_ticker, expiry_date_a, expiry_date_b
        FROM positions
        WHERE status='OPEN' AND (expiry_date_a IS NOT NULL OR expiry_date_b IS NOT NULL)
    """)
    positions = cursor.fetchall()
    conn.close()

    from datetime import datetime as _dt, date as _date
    today = _date.today()

    for pos in positions:
        (pid, pair_name, base_pair, tf, direction, ea, eb,
         ta, tb, exp_a, exp_b) = pos
        try:
            # Определяем ближайшую экспирацию
            min_days = None
            for exp in [exp_a, exp_b]:
                if not exp:
                    continue
                exp_dt = _dt.strptime(exp, '%Y-%m-%d').date()
                days_left = (exp_dt - today).days
                if min_days is None or days_left < min_days:
                    min_days = days_left

            if min_days is not None and min_days <= 2:
                # Получить текущие цены (одно чтение)
                file_a = CANDLES_DIR / f'{ta}_{tf}.parquet'
                file_b = CANDLES_DIR / f'{tb}_{tf}.parquet'
                if not file_a.exists() or not file_b.exists():
                    print(f'  ⚠️ {pair_name}: нет данных {tf} для {ta} или {tb} — пропуск')
                    continue
                df_a = pd.read_parquet(file_a)
                df_b = pd.read_parquet(file_b)
                if len(df_a) == 0 or len(df_b) == 0:
                    continue
                _last_a = df_a['close'].iloc[-1]
                _last_b = df_b['close'].iloc[-1]
                price_a = float(_last_a) if not isinstance(_last_a, bytes) else 0.0
                price_b = float(_last_b) if not isinstance(_last_b, bytes) else 0.0

                print(f'  ⏰ {pair_name}: экспирация через {min_days} дн. — ЗАКРЫВАЕМ')
                close_position(pid, pair_name, base_pair, tf, 0, price_a, price_b)
        except Exception as e:
            print(f'  ⚠️ check_expiry({pair_name}): {e}')


def check_time_exits():
    """Закрыть пары, висящие дольше MAX_HOLD_HOURS (TIME_EXIT)."""
    if not is_moex_trading_day():
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cutoff = (datetime.now() - timedelta(hours=MAX_HOLD_HOURS)).strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("""
        SELECT id, pair_name, base_pair, timeframe, leg_a_ticker, leg_b_ticker
        FROM positions
        WHERE status='OPEN' AND entry_time < ?
    """, (cutoff,))
    stale = cursor.fetchall()
    conn.close()

    for pid, pair_name, base_pair, tf, ta, tb in stale:
        try:
            df_a = pd.read_parquet(CANDLES_DIR / f'{ta}_{tf}.parquet')
            df_b = pd.read_parquet(CANDLES_DIR / f'{tb}_{tf}.parquet')
            price_a = float(df_a['close'].iloc[-1]) if not isinstance(df_a['close'].iloc[-1], bytes) else 0.0
            price_b = float(df_b['close'].iloc[-1]) if not isinstance(df_b['close'].iloc[-1], bytes) else 0.0
            print(f'  ⏰ {pair_name}: держится > {MAX_HOLD_HOURS}ч — TIME_EXIT')
            close_position(pid, pair_name, base_pair, tf, 0, price_a, price_b)
        except Exception as e:
            print(f'  ⚠️ check_time_exits({pair_name}): {e}')


def close_all_positions(reason='STOP'):
    """Закрыть все открытые позиции по M10 close (реальные цены)."""
    for pos in get_open_positions():
        _pid = pos[0]; _pair = pos[1]; _base = pos[2]; _tf = pos[3]
        _ta = pos[16] if len(pos) > 16 else None
        _tb = pos[18] if len(pos) > 18 else None
        _pa = 0.0; _pb = 0.0
        try:
            if _ta:
                _fa = CANDLES_DIR / f'{_ta}_{_tf}.parquet'
                if _fa.exists():
                    _pa = float(pd.read_parquet(_fa)['close'].iloc[-1])
            if _tb:
                _fb = CANDLES_DIR / f'{_tb}_{_tf}.parquet'
                if _fb.exists():
                    _pb = float(pd.read_parquet(_fb)['close'].iloc[-1])
        except Exception as e:
            print(f'  ⚠️ close_all_positions({_pair}): {e}')
        close_position(_pid, _pair, _base, _tf, 0, _pa, _pb)


def main():
    print("=" * 60)
    print(f"🤖 РОБОТ ПАРНОЙ ТОРГОВЛИ | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print(f"Депозит: {DEPOSIT} ₽")
    print(f"Объём: {VOLUME} {VOLUME_TYPE}")
    print(f"Проверка: M10 — каждые {CHECK_INTERVALS['M10']//60} мин, H1 — каждые {CHECK_INTERVALS['H1']//3600} ч")
    print("=" * 60)

    # Инициализация БД
    init_db()

    # Загрузка ML-моделей (для фильтра)
    load_ml_models()

    # Сохраняем стартовое состояние (paused=True — безопасный default)
    _start_state = load_state()
    _start_state['running'] = True
    _start_state['updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    save_state(_start_state)
    print(f"📝 Состояние сохранено: running=True, paused={_start_state.get('paused')}")

    # Проверка экспираций
    check_expiry()

    # Проверка TIME_EXIT
    check_time_exits()

    # Загружаем конфиг пар
    with open(CONFIG_PATH, 'r') as f:
        pairs_config = json.load(f)

    running = True
    last_check = {'M10': 0, 'H1': 0, 'H4': 0}

    while running:
        try:
            # Неторговый день — новые позиции не открываем
            if not is_moex_trading_day():
                print('⏸️ Неторговый день — новые позиции не открываются')
                time.sleep(3600)
                continue

            # Загружаем состояние (безопасный default: paused=True)
            state = load_state()

            # Проверяем команды
            cmd = process_command()
            if cmd == 'STOP':
                print("🛑 Команда STOP: закрываем все позиции")
                for pos in get_open_positions():
                    close_all_positions()
                state['running'] = False
                save_state(state)
                running = False
                break
            elif cmd == 'PAUSE':
                state['paused'] = True
                save_state(state)
                print("⏸️ Команда PAUSE: новые позиции не открываются (робот продолжает проверять стопы)")
                continue
            elif cmd == 'RESUME':
                state['paused'] = False
                save_state(state)
                print("▶️ Команда RESUME: торговля возобновлена")
                continue

            # Если на паузе — только проверка стопов и экспирации
            if state.get('paused', True):
                check_expiry()
                check_time_exits()
                # Проверяем команды каждые 5 сек (быстрая реакция на RESUME)
                _paused_exit = False
                for _ in range(12):  # 12 × 5 = 60 сек
                    time.sleep(5)
                    _cmd = process_command()
                    if _cmd == 'PAUSE':
                        state['paused'] = True
                        save_state(state)
                        print('⏸️ PAUSE: уже на паузе')
                        break
                    elif _cmd == 'RESUME':
                        state['paused'] = False
                        save_state(state)
                        print('▶️ RESUME: торговля возобновлена')
                        break
                    elif _cmd == 'STOP':
                        print('🛑 STOP: graceful shutdown')
                        for pos in get_open_positions():
                            close_all_positions()
                        state['running'] = False
                        save_state(state)
                        running = False
                        _paused_exit = True
                        break
                if _paused_exit:
                    break
                continue

            current_time = time.time()

            # Проверяем сигналы по ТФ
            for tf, interval in CHECK_INTERVALS.items():
                if current_time - last_check[tf] >= interval:
                    check_signals_by_tf(pairs_config, tf)
                    last_check[tf] = current_time

            time.sleep(1)

        except KeyboardInterrupt:
            print("🛑 Остановлено пользователем")
            break
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(5)

    print("✅ Робот остановлен")

def is_pair_in_cooldown(pair_name):
    """Проверить, был ли убыток по паре за последние COOLDOWN_HOURS."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cutoff = (datetime.now() - timedelta(hours=COOLDOWN_HOURS)).strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("""
        SELECT COUNT(*) FROM positions
        WHERE pair_name = ? AND status = 'CLOSED'
        AND pnl < 0 AND exit_time > ?
    """, (pair_name, cutoff))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0


def check_signals_by_tf(pairs_config, tf):
    """Проверить сигналы по парам на конкретном ТФ"""
    print(f"\n📊 Проверка сигналов {tf}...")
    
    # === ПРОВЕРКА СВЕЖЕСТИ ДАННЫХ ===
    # В боевом режиме: не закрываем позиции при сбое, только не открываем новые
    # Открытые позиции ждут восстановления данных (стопы на бирже защитят)
    global TF_FRESH_STATE
    
    _is_fresh = is_tf_fresh(tf)
    
    if not _is_fresh:
        print(f"  ⚠️ Данные {tf} устарели! Новые позиции по {tf} не открываются.")
        # Отправляем уведомление ТОЛЬКО при смене состояния
        if TF_FRESH_STATE.get(tf, True):
            send_vk_message(f"⚠️ Данные {tf} устарели! Новые позиции по {tf} приостановлены. Открытые позиции ждут восстановления.")
            TF_FRESH_STATE[tf] = False
            save_tf_fresh_state(TF_FRESH_STATE)
        return
    else:
        # Данные свежие — проверяем, было ли восстановление
        if not TF_FRESH_STATE.get(tf, True):
            send_vk_message(f"✅ Данные {tf} восстановлены! Торговля по {tf} возобновлена.")
            TF_FRESH_STATE[tf] = True
            save_tf_fresh_state(TF_FRESH_STATE)



    for pair_name, pair_data in pairs_config.get('pairs', {}).items():
        if not pair_name.endswith(f'_{tf}'):
            continue
        
        # Проверка enabled (если отключена — пропускаем)
        if pair_data.get('enabled', True) is False:
            continue
        
        base_pair = pair_name.replace(f'_{tf}', '')
        if '-' not in base_pair:
            continue
        
        ticker_a, ticker_b = base_pair.split('-')
        file_a = CANDLES_DIR / f'{ticker_a}_{tf}.parquet'
        file_b = CANDLES_DIR / f'{ticker_b}_{tf}.parquet'
        
        if not file_a.exists() or not file_b.exists():
            continue
        
        try:
            df_a = pd.read_parquet(file_a)
            df_b = pd.read_parquet(file_b)
            # Конвертируем close в float, отбрасывая bytes
            df_a['close'] = df_a['close'].apply(lambda x: float(x) if not isinstance(x, bytes) else 0.0)
            df_b['close'] = df_b['close'].apply(lambda x: float(x) if not isinstance(x, bytes) else 0.0)
            
            # Параметры
            _bp = pair_data.get('best_params', {})
            window = _bp.get('window', 20)
            entry_z = _bp.get('entry_z', ENTRY_Z_DEFAULT)
            exit_z = _bp.get('exit_z', EXIT_Z_DEFAULT)
            use_coint = _bp.get('use_coint', False)
            resid_window = _bp.get('resid_window', 60)

            # Z-score (с поддержкой cointegration residuals)
            result = calculate_zscore(df_a, df_b, window=window,
                                      use_coint=use_coint,
                                      resid_window=resid_window)
            if not result:
                continue
            
            current_z = result['current_zscore']
            price_a = result['price_a']
            price_b = result['price_b']
            spread_trend = result.get('spread_trend', 0)
            
            # Проверяем открытые позиции
            open_positions = get_open_positions()
            
            # Проверка лимита позиций (контроль риска)
            if len(open_positions) >= MAX_POSITIONS:
                print(f'  ⚠️ Лимит позиций ({MAX_POSITIONS}) — не открываем новые')
                continue
            
            # Проверка cooldown после убытка по паре
            if is_pair_in_cooldown(pair_name):
                print(f'  ⏸️ {pair_name}: cooldown после убытка ({COOLDOWN_HOURS}ч)')
                continue
            
            has_position = any(p[1] == pair_name and p[3] == tf for p in open_positions)

            # Логируем z-score для каждой пары
            _beta = result.get('beta', 0.0)
            _corr_val = result.get('corr', 0.0)
            print(f'  📊 {pair_name}: z={current_z:+.2f} (entry={entry_z}), corr={_corr_val:.2f}, beta={_beta:.2f}')
            
            if not has_position:
                # Фильтр времени: не входить в конце сессии (после 18:00 МСК)
                import datetime as _dt
                _now_msk = _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=3)))
                _hour = _now_msk.hour
                _minute = _now_msk.minute
                _is_trading_time = (7 <= _hour < 18)
                
                # Фильтр волатильности: только для простого spread
                # (для cointegration residuals — не применять)
                _std = result.get('std', 0)
                _mean = result.get('mean', 0)
                _vol_ok = True
                if not use_coint and _std and _mean and abs(_mean) > 0.0001:
                    _vol_ratio = _std / abs(_mean)
                    if _vol_ratio > 0.02:
                        _vol_ok = False
                
                # Фильтр корреляции: только для простого spread.
                # Для cointegration residuals — не применять (residuals уже коинтегрированы,
                # corr close не показатель).
                _corr_ok = True
                _corr = calculate_correlation(df_a, df_b, window=50)
                if not use_coint and _corr is not None and abs(_corr) < 0.7:
                    _corr_ok = False

                # Проверка экспирации (не открывать за 2 дня)
                _expiry_ok = True
                if is_expiring_soon(ticker_a, days=2) or is_expiring_soon(ticker_b, days=2):
                    _expiry_ok = False

                # Проверка нового контракта (не открывать <3 дней после rollover)
                _new_ok = True
                if is_new_contract(ticker_a, days=3) or is_new_contract(ticker_b, days=3):
                    _new_ok = False

                # Логируем причины отказа
                if not (_is_trading_time and _vol_ok and _corr_ok and _expiry_ok and _new_ok):
                    _reasons = []
                    if not _is_trading_time: _reasons.append('time')
                    if not _vol_ok: _reasons.append('vol')
                    if not _corr_ok: _reasons.append('corr')
                    if not _expiry_ok: _reasons.append('expiry')
                    if not _new_ok: _reasons.append('new_contract')
                    print(f'  ⛔ {pair_name}: фильтры — {", ".join(_reasons)} (z={current_z:+.2f})')

                # Проверяем вход (с фильтрами)
                if _is_trading_time and _vol_ok and _corr_ok and _expiry_ok and _new_ok:
                    _signal = None
                    if current_z >= entry_z and spread_trend > 0:
                        _signal = 'SHORT_SPREAD'
                    elif current_z <= -entry_z and spread_trend < 0:
                        _signal = 'LONG_SPREAD'

                    if _signal is not None:
                        # ML-фильтр (только для пар с обученной моделью)
                        _ml_feats = {
                            'z': current_z,
                            'std': result.get('std', 0.0),
                            'corr': result.get('corr', 0.0),
                            'spread_trend': spread_trend,
                            'beta': result.get('beta', 0.0),
                        }
                        _ml_pass, _ml_proba = ml_filter(pair_name, _ml_feats)
                        if _ml_pass:
                            if _ml_proba is not None:
                                print(f'  🤖 ML PASS {pair_name}: proba={_ml_proba:.3f} → {_signal}')
                            open_position(pair_name, base_pair, tf, _signal, VOLUME, current_z, price_a, price_b)
                        else:
                            print(f'  🚫 ML BLOCK {pair_name}: proba={_ml_proba:.3f} → {_signal} (z={current_z:+.2f})')
                elif not _new_ok:
                    print(f'  ⏰ {pair_name}: новый контракт <3 дн. — не открываем')
                elif not _expiry_ok:
                    print(f'  ⏰ {pair_name}: экспирация ≤2 дн. — не открываем')
                elif not _is_trading_time:
                    pass  # Пропускаем — не торгуем в конце сессии
                elif not _vol_ok:
                    pass  # Пропускаем — волатильность аномальная
            else:
                # Проверяем выход
                if abs(current_z) <= exit_z:
                    for pos in open_positions:
                        if pos[1] == pair_name and pos[3] == tf:
                            close_position(pos[0], pair_name, base_pair, tf, current_z, price_a, price_b)
        
        except Exception as e:
            print(f"  ❌ {pair_name}: {e}")

if __name__ == '__main__':
    main()
