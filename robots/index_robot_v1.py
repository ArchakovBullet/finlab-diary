#!/usr/bin/env python3
"""
Робот индексный_v1 (paper).
Одиночная торговля SBER/GAZP по divergence с MOEXFN (индекс финсектора).
Логика:
  - D1: ret_акция, ret_сектор (MOEXFN).
  - divergence: знаки разные.
  - вход: в сторону сектора (сектор ↑, акция ↓ -> LONG акции; сектор ↓, акция ↑ -> SHORT акции).
  - выход: через H=1 день (следующий D1 close) ИЛИ |z| <= 0.5.
  - окно: 07:00–23:00, Пн–Сб (Вс — выходной; Сб — допсессия MOEX).
  - paper: депозит 100000, комиссия 0.28% (0.14*2), slip 0.02%*2.
Read-only по данным. v2/v3/v4 не трогает.
"""
import os, json, time, sqlite3
from datetime import datetime
import numpy as np
import pandas as pd

ROOT = "/root/finlab"
CANDLES = os.path.join(ROOT, "data", "candles")
SECTOR = os.path.join(ROOT, "data", "sector_indices")
DB_PATH = os.path.join(ROOT, "robots", "index_robot_v1.db")
STATE_PATH = os.path.join(ROOT, "robots", "robot_state_index_v1.json")
LOG_PATH = os.path.join(ROOT, "logs", "index_robot_v1.log")

TICKERS = ["SBER", "GAZP"]
SECTOR_FILE = os.path.join(SECTOR, "MOEXFN_D1.parquet")
H_DAYS = 1
EXIT_Z = 0.5
DEPOSIT = 100_000.0
FEE = 0.0028
SLIP = 0.0004
CHECK_INTERVAL_S = 3600
TRADE_START = "07:00"
TRADE_END = "23:00"
NO_TRADE_WEEKENDS = []  # список (месяц, день) — праздники/выходные (Сб НЕ включать — торговый)

def log(msg):
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")

def is_moex_trading_day(now):
    # MOEX: Пн–Сб — торговые (Сб — допсессия), Вс — выходной
    if now.weekday() == 6:  # Вс
        return False
    if (now.month, now.day) in NO_TRADE_WEEKENDS:
        return False
    return True

def in_trading_window(now):
    if not is_moex_trading_day(now):
        return False
    t = now.strftime("%H:%M")
    return TRADE_START <= t <= TRADE_END

def load_d1(ticker):
    p = os.path.join(CANDLES, f"{ticker}_D1.parquet")
    if not os.path.exists(p): return None
    df = pd.read_parquet(p)
    cols = {c.lower(): c for c in df.columns}
    df = df.rename(columns={cols.get("begin","begin"): "begin", cols.get("close","close"): "close"})
    df["begin"] = pd.to_datetime(df["begin"], errors="coerce").dt.normalize()
    df = df.dropna(subset=["begin","close"]).sort_values("begin").reset_index(drop=True)
    return df[["begin","close"]]

def load_sector():
    if not os.path.exists(SECTOR_FILE): return None
    df = pd.read_parquet(SECTOR_FILE)
    df["begin"] = pd.to_datetime(df["begin"], errors="coerce").dt.normalize()
    df = df.dropna(subset=["begin","close"]).sort_values("begin").reset_index(drop=True)
    return df[["begin","close"]].rename(columns={"close":"sector"})

def init_db():
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker TEXT, direction TEXT, volume REAL,
        entry_time TEXT, entry_price REAL, entry_sector REAL, entry_z REAL,
        exit_time TEXT, exit_price REAL, exit_sector REAL, exit_z REAL,
        status TEXT, pnl REAL, reason TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        time TEXT, ticker TEXT, ret_stock REAL, ret_sector REAL, z REAL,
        signal TEXT, status TEXT, reason TEXT
    )""")
    conn.commit(); conn.close()

def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f: return json.load(f)
    return {"running": True, "paused": False, "last_check": None, "open_positions": 0, "total_pnl": 0.0}

def save_state(st):
    with open(STATE_PATH, "w") as f: json.dump(st, f, ensure_ascii=False, indent=2)

def zscore_spread(df_stock, df_sector, window=60):
    m = pd.merge(df_stock, df_sector, on="begin", how="inner").sort_values("begin").reset_index(drop=True)
    if len(m) < window + 5: return None
    m["log_stock"] = np.log(m["close"].replace(0, np.nan))
    m["log_sector"] = np.log(m["sector"].replace(0, np.nan))
    m = m.dropna(subset=["log_stock","log_sector"]).reset_index(drop=True)
    x = m["log_sector"].values[-window:]; y = m["log_stock"].values[-window:]
    xm, ym = x.mean(), y.mean()
    var = ((x - xm) ** 2).mean()
    if var == 0: return None
    beta = ((x - xm) * (y - ym)).mean() / var
    spread = m["log_stock"] - beta * m["log_sector"]
    s = spread.iloc[-window:]
    mu, sd = s.mean(), s.std(ddof=1)
    if sd == 0: return None
    z = (spread.iloc[-1] - mu) / sd
    return {"z": float(z), "beta": float(beta), "last_begin": m["begin"].iloc[-1]}

def get_open_positions():
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute("SELECT id, ticker, direction, volume, entry_time, entry_price, entry_z FROM positions WHERE status='OPEN'")
    rows = cur.fetchall(); conn.close()
    return rows

def open_position(ticker, direction, price, sector_price, z):
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute("""INSERT INTO positions (ticker, direction, volume, entry_time, entry_price, entry_sector, entry_z, status)
                   VALUES (?,?,?,?,?,?,?, 'OPEN')""",
                (ticker, direction, 1.0, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), float(price), float(sector_price), float(z)))
    conn.commit(); conn.close()

def close_position(pid, price, sector_price, z, reason):
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute("SELECT ticker, direction, entry_price FROM positions WHERE id=?", (pid,))
    row = cur.fetchone()
    if not row: conn.close(); return
    ticker, direction, entry_price = row
    sign = 1 if direction == "LONG" else -1
    gross = sign * (price - entry_price)
    net = gross - 2 * (FEE/2 + SLIP/2) * entry_price
    cur.execute("""UPDATE positions SET exit_time=?, exit_price=?, exit_sector=?, exit_z=?, status='CLOSED', pnl=?, reason=?
                   WHERE id=?""",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), float(price), float(sector_price), float(z), float(net), reason, pid))
    conn.commit(); conn.close()

def log_signal(ticker, ret_stock, ret_sector, z, signal, status, reason):
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute("""INSERT INTO signals (time, ticker, ret_stock, ret_sector, z, signal, status, reason)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ticker, ret_stock, ret_sector, z, signal, status, reason))
    conn.commit(); conn.close()

def check_ticker(ticker, df_stock, df_sector):
    zs = zscore_spread(df_stock, df_sector)
    if zs is None:
        log(f"{ticker}: недостаточно данных для z-score"); return
    m = pd.merge(df_stock, df_sector, on="begin", how="inner").sort_values("begin").reset_index(drop=True)
    if len(m) < 3: return
    last = m.iloc[-1]; prev = m.iloc[-2]
    ret_stock = float(np.log(last["close"] / prev["close"])) if prev["close"] > 0 else 0.0
    ret_sector = float(np.log(last["sector"] / prev["sector"])) if prev["sector"] > 0 else 0.0
    z = zs["z"]
    divergence = (np.sign(ret_stock) != np.sign(ret_sector)) and (abs(ret_stock) > 1e-6) and (abs(ret_sector) > 1e-6)
    log(f"{ticker}: ret_stock={ret_stock:+.5f} ret_sector={ret_sector:+.5f} z={z:+.2f} divergence={divergence}")
    open_pos = [p for p in get_open_positions() if p[1] == ticker]
    # Выход: H_DAYS или EXIT_Z
    for p in open_pos:
        pid, tk, direction, vol, etime, eprice, ez = p
        _etime = pd.to_datetime(etime, errors="coerce")
        _held_days = (last["begin"] - _etime).days if pd.notna(_etime) else 0
        if _held_days >= H_DAYS:
            close_position(pid, float(last["close"]), float(last["sector"]), z, f"exit_H({_held_days}d)")
            log(f"  CLOSE {tk} {direction} id={pid} reason=H_DAYS ({_held_days}d) z={z:+.2f}")
        elif abs(z) <= EXIT_Z:
            close_position(pid, float(last["close"]), float(last["sector"]), z, f"exit_z(|z|<={EXIT_Z})")
            log(f"  CLOSE {tk} {direction} id={pid} reason=EXIT_Z z={z:+.2f}")
    # Вход: divergence и нет открытой, и в окне
    if divergence and not open_pos:
        _now = datetime.now()
        if not in_trading_window(_now):
            log_signal(ticker, ret_stock, ret_sector, z, None, "MISSED", "outside_window")
            log(f"  SKIP {ticker}: вне окна ({_now.strftime('%H:%M')} / weekday={_now.weekday()})")
            return
        direction = "LONG" if ret_sector > 0 else "SHORT"
        open_position(ticker, direction, float(last["close"]), float(last["sector"]), z)
        log_signal(ticker, ret_stock, ret_sector, z, direction, "EXECUTED", "divergence")
        log(f"  OPEN {ticker} {direction} price={last['close']} sector={last['sector']} z={z:+.2f}")
    elif divergence and open_pos:
        log_signal(ticker, ret_stock, ret_sector, z, None, "MISSED", "already_open")
    else:
        log_signal(ticker, ret_stock, ret_sector, z, None, "MISSED", "no_divergence")

def main():
    init_db()
    st = load_state()
    save_state(st)
    log(f"=== index_robot_v1 start | tickers={TICKERS} h={H_DAYS} exit_z={EXIT_Z} window={TRADE_START}-{TRADE_END} (Пн-Сб) ===")
    sector = load_sector()
    if sector is None:
        log("Нет MOEXFN_D1 — выход"); return
    while True:
        st = load_state()
        if st.get("paused"):
            log("paused=true — спим"); time.sleep(CHECK_INTERVAL_S); continue
        sector = load_sector()
        for t in TICKERS:
            df = load_d1(t)
            if df is None:
                log(f"{t}: нет D1"); continue
            try:
                check_ticker(t, df, sector)
            except Exception as e:
                log(f"{t}: ERROR {e}")
        st["last_check"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st["open_positions"] = len(get_open_positions())
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
        cur.execute("SELECT COALESCE(SUM(pnl),0) FROM positions WHERE status='CLOSED'")
        st["total_pnl"] = float(cur.fetchone()[0]); conn.close()
        save_state(st)
        log(f"state: last_check={st['last_check']} open={st['open_positions']} pnl={st['total_pnl']:.2f}")
        time.sleep(CHECK_INTERVAL_S)

if __name__ == "__main__":
    main()
