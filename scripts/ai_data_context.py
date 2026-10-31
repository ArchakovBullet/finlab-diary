#!/usr/bin/env python3
"""ai_data_context.py — собирает контекст данных для AI-отчёта.

Возвращает dict:
- freshness: свежесть ключевых файлов (M10/H1/H4/D1).
- config: enabled-пары, best_params.
- quarantine: state карантина.
- algopack: сводка (obstats/tradestats/futoi).
- cron: ключевые задания.

Использование:
  python scripts/ai_data_context.py  # JSON в stdout
"""
import json
import sqlite3
import pandas as pd
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path('/root/finlab')
CANDLES = ROOT / 'data' / 'candles'
CONFIG = ROOT / 'FinLabPy' / 'My_Indicators' / 'pairs_config.json'
QUARANTINE_STATE = ROOT / 'logs' / 'pairs_quarantine_state.json'

DEAD_TICKERS = {"IN","PIKK","BY","RF","UT","I2"}  # мёртвые тикеры (не торгуются, freshness-шум)


def get_freshness():
    """Свежесть ключевых файлов (M10/H1/H4/D1)."""
    now = datetime.now()
    result = {}
    for tf in ['M10', 'H1', 'H4', 'D1']:
        files = list(CANDLES.glob(f'*_{tf}.parquet'))
        if not files:
            result[tf] = {'total': 0, 'fresh': 0, 'oldest_h': None}
            continue
        total = len(files)
        fresh = 0
        oldest = 0
        for f in files:
            stem = f.stem.split('_')[0]
            if stem in DEAD_TICKERS:
                continue
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            age_h = (now - mtime).total_seconds() / 3600
            if age_h < 25:
                fresh += 1
            oldest = max(oldest, age_h)
        result[tf] = {
            'total': total,
            'fresh': fresh,
            'oldest_h': round(oldest, 1),
        }
    return result


def get_index_divergence():
    """Divergence SBER/GAZP vs MOEXFN (D1) — для AI-отчёта."""
    import pandas as _pd, numpy as _np
    sector_path = ROOT / 'data' / 'sector_indices' / 'MOEXFN_D1.parquet'
    if not sector_path.exists():
        return {}
    try:
        sdf = _pd.read_parquet(sector_path)
        sdf['begin'] = _pd.to_datetime(sdf['begin'], errors='coerce').dt.normalize()
        sdf = sdf.dropna(subset=['begin','close']).sort_values('begin').reset_index(drop=True)
    except Exception:
        return {}
    out = {}
    for t in ('SBER','GAZP'):
        fp = ROOT / 'data' / 'candles' / f'{t}_D1.parquet'
        if not fp.exists():
            continue
        try:
            df = _pd.read_parquet(fp)
            df['begin'] = _pd.to_datetime(df['begin'], errors='coerce').dt.normalize()
            df = df.dropna(subset=['begin','close']).sort_values('begin').reset_index(drop=True)
        except Exception:
            continue
        m = _pd.merge(df[['begin','close']], sdf[['begin','close']], on='begin', how='inner', suffixes=('_stock','_sector')).sort_values('begin').reset_index(drop=True)
        if len(m) < 3:
            continue
        last = m.iloc[-1]; prev = m.iloc[-2]
        ret_stock = float(_np.log(last['close_stock']/prev['close_stock'])) if prev['close_stock']>0 else 0.0
        ret_sector = float(_np.log(last['close_sector']/prev['close_sector'])) if prev['close_sector']>0 else 0.0
        divergence = (bool(_np.sign(ret_stock) != _np.sign(ret_sector))) and (abs(ret_stock)>1e-6) and (abs(ret_sector)>1e-6)
        # z-score спреда (log_stock - beta*log_sector) на 60
        win = 60
        mm = m.copy()
        mm['ls'] = _np.log(mm['close_stock'].replace(0, _np.nan))
        mm['lc'] = _np.log(mm['close_sector'].replace(0, _np.nan))
        mm = mm.dropna(subset=['ls','lc']).reset_index(drop=True)
        z = None
        if len(mm) >= win+2:
            x = mm['lc'].values[-win:]; y = mm['ls'].values[-win:]
            xm, ym = x.mean(), y.mean()
            var = ((x-xm)**2).mean()
            if var > 0:
                beta = ((x-xm)*(y-ym)).mean()/var
                spread = mm['ls'] - beta*mm['lc']
                s_win = spread.iloc[-win:]
                mu, sd = s_win.mean(), s_win.std(ddof=1)
                if sd and sd > 0:
                    z = float((spread.iloc[-1]-mu)/sd)
        signal = None
        if divergence:
            signal = 'LONG' if ret_sector > 0 else 'SHORT'
        out[t] = {'ret_stock': round(ret_stock,6), 'ret_sector': round(ret_sector,6),
                  'divergence': divergence, 'z': (round(z,3) if z is not None else None),
                  'signal': signal, 'date': str(last['begin'].date())}
    return out


def get_index_algopack():
    """Algopack-фон для SBER/GAZP с ценой/временем/delta (FutOI, HI2, MegaAlerts, TradeStats, RVI)."""
    import pandas as _pd
    out = {}
    for t in ("SBER", "GAZP"):
        fut_t = t + "F"
        item = {}
        h1 = None
        m10 = None
        try:
            p = ROOT / "data" / "candles" / (t + "_H1.parquet")
            if p.exists():
                h1 = _pd.read_parquet(p)[["begin","close"]].copy()
                h1["begin"] = _pd.to_datetime(h1["begin"], errors="coerce")
                h1 = h1.dropna().sort_values("begin").reset_index(drop=True)
        except Exception:
            h1 = None
        try:
            p = ROOT / "data" / "candles" / (t + "_M10.parquet")
            if p.exists():
                m10 = _pd.read_parquet(p)[["begin","close"]].copy()
                m10["begin"] = _pd.to_datetime(m10["begin"], errors="coerce")
                m10 = m10.dropna().sort_values("begin").reset_index(drop=True)
        except Exception:
            m10 = None
        def _price_at(df, ts):
            if df is None or len(df) == 0: return None
            try:
                ts = _pd.to_datetime(ts)
                d = df[df["begin"] <= ts]
                if len(d): return float(d["close"].iloc[-1])
            except Exception:
                pass
            return None
        # --- FutOI (SBERF/GAZPF) ---
        try:
            p = ROOT / "data" / "futoi_1h" / "futoi_1h.parquet"
            if p.exists():
                d = _pd.read_parquet(p)
                d = d[d["ticker"] == fut_t].reset_index(drop=True)
                if len(d):
                    last = d.iloc[-1]
                    hour_ts = last.get("hour")
                    h1_last_begin = h1["begin"].iloc[-1] if h1 is not None and len(h1) else None
                    h1_last_close = float(h1["close"].iloc[-1]) if h1 is not None and len(h1) else None
                    h1_prev_close = float(h1["close"].iloc[-2]) if h1 is not None and len(h1) > 1 else None
                    delta_1h = (h1_last_close - h1_prev_close) if (h1_last_close is not None and h1_prev_close is not None) else None
                    item["futoi"] = {
                        "hour": str(hour_ts),
                        "h1_last_begin": str(h1_last_begin) if h1_last_begin is not None else None,
                        "price": h1_last_close,
                        "price_prev": h1_prev_close,
                        "delta_1h": (round(delta_1h, 4) if delta_1h is not None else None),
                        "fiz_buy_ratio": float(last.get("fiz_buy_ratio", 0)),
                        "yur_buy_ratio": float(last.get("yur_buy_ratio", 0)),
                        "fiz_ratio_delta": float(last.get("fiz_ratio_delta", 0)),
                        "yur_ratio_delta": float(last.get("yur_ratio_delta", 0)),
                    }
        except Exception:
            pass
        # --- HI2 (SBER/GAZP) ---
        try:
            p = ROOT / "data" / "hi2" / (t + "_hi2.parquet")
            if p.exists():
                d = _pd.read_parquet(p)
                last_day = d["tradedate"].max()
                d = d[d["tradedate"] == last_day]
                if len(d):
                    piv = d.pivot_table(index="tradetime", columns="metric", values="value", aggfunc="last")
                    last = piv.iloc[-1]
                    tt = str(piv.index[-1])
                    ts_at = _pd.to_datetime(str(last_day) + " " + tt) if last_day is not None else None
                    price_at = _price_at(m10, ts_at) if ts_at is not None else None
                    price_now = float(m10["close"].iloc[-1]) if m10 is not None and len(m10) else None
                    delta_1d = (price_now - price_at) if (price_now is not None and price_at is not None) else None
                    keys = ["hhi_buy","hhi_sell","hhi_netflow_buy","hhi_netflow_sell","hhi_agressive","hhi_volume"]
                    item["hi2"] = {k: (float(last[k]) if k in last.index and _pd.notna(last[k]) else None) for k in keys}
                    item["hi2"]["tradedate"] = str(last_day)[:10]
                    item["hi2"]["tradetime"] = tt
                    item["hi2"]["price_at_time"] = price_at
                    item["hi2"]["price_now"] = price_now
                    item["hi2"]["delta_1d"] = (round(delta_1d, 4) if delta_1d is not None else None)
        except Exception:
            pass
        # --- MegaAlerts (SBER/GAZP) ---
        try:
            p = ROOT / "data" / "mega_alerts" / (t + "_alerts.parquet")
            if p.exists():
                d = _pd.read_parquet(p)
                d["tradedate"] = _pd.to_datetime(d["tradedate"], errors="coerce")
                cutoff = d["tradedate"].max() - _pd.Timedelta(days=2)
                d2 = d[d["tradedate"] >= cutoff].copy()
                items = []
                for _, r in d2.iterrows():
                    ts = _pd.to_datetime(str(r.get("tradedate")) + " " + str(r.get("tradetime", "00:00:00")))
                    items.append({
                        "tradedate": str(r.get("tradedate", ""))[:10],
                        "tradetime": str(r.get("tradetime", "")),
                        "price": _price_at(m10, ts),
                        "value": float(r.get("value", 0)) if _pd.notna(r.get("value", None)) else None,
                        "type": str(r.get("alert_type", "")),
                    })
                item["mega"] = {"count": int(len(items)), "items": items}
        except Exception:
            pass
        # --- TradeStats (SBER/GAZP) ---
        try:
            p = ROOT / "data" / "tradestats" / (t + "_tradestats.parquet")
            if p.exists():
                d = _pd.read_parquet(p)
                last = d.iloc[-1]
                prev_ts = _pd.to_datetime(str(last.get("tradedate")) + " " + str(last.get("tradetime"))) - _pd.Timedelta(days=1)
                d_prev = d[(_pd.to_datetime(d["tradedate"].astype(str) + " " + d["tradetime"].astype(str))) <= prev_ts]
                price_prev = float(d_prev.iloc[-1]["pr_vwap"]) if len(d_prev) else None
                price_now = float(last.get("pr_vwap", 0))
                delta_1d = (price_now - price_prev) if (price_prev is not None) else None
                item["tradestats"] = {
                    "tradedate": str(last.get("tradedate", ""))[:10],
                    "tradetime": str(last.get("tradetime", "")),
                    "price": price_now,
                    "price_prev": price_prev,
                    "delta_1d": (round(delta_1d, 4) if delta_1d is not None else None),
                    "pr_change": float(last.get("pr_change", 0)),
                    "disb": float(last.get("disb", 0)),
                    "vol": float(last.get("vol", 0)),
                }
        except Exception:
            pass
        # --- RVI (общий, с ценой SBER/GAZP на D1 и сейчас) ---
        try:
            p = ROOT / "data" / "sector_indices" / "RVI_D1.parquet"
            if p.exists():
                d = _pd.read_parquet(p)
                d["begin"] = _pd.to_datetime(d["begin"], errors="coerce")
                d = d.dropna(subset=["begin"]).sort_values("begin").reset_index(drop=True)
                last = d.iloc[-1]
                price_at_rvi = _price_at(h1, last["begin"])
                price_now = float(h1["close"].iloc[-1]) if h1 is not None and len(h1) else None
                item["rvi"] = {
                    "begin": str(last["begin"])[:10],
                    "rvi": float(last.get("close", 0)),
                    "price_at_rvi_date": price_at_rvi,
                    "price_now": price_now,
                }
        except Exception:
            pass
        out[t] = item
    return out


def get_config():
    """Enabled-пары из pairs_config.json."""
    if not CONFIG.exists():
        return {}
    c = json.load(open(CONFIG))
    pairs = c.get('pairs', {})
    enabled = {k: v.get('best_params', {}) for k, v in pairs.items() if v.get('enabled')}
    return {
        'enabled_count': len(enabled),
        'enabled_pairs': list(enabled.keys()),
        'last_updated': c.get('last_updated', ''),
    }


def get_quarantine():
    """State карантина."""
    if not QUARANTINE_STATE.exists():
        return {}
    try:
        return json.load(open(QUARANTINE_STATE))
    except Exception:
        return {}


def get_algopack_summary():
    """Сводка по Algopack (свежесть + размеры)."""
    result = {}
    files = {
        'futoi_1h': ROOT / 'data' / 'futoi_1h' / 'futoi_1h.parquet',
        'supercandles_belu': ROOT / 'data' / 'supercandles' / 'BELU_supercandles.parquet',
    }
    now = datetime.now()
    for name, f in files.items():
        if f.exists():
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            age_h = (now - mtime).total_seconds() / 3600
            result[name] = {
                'size_kb': round(f.stat().st_size / 1024, 1),
                'age_h': round(age_h, 2),
            }
    return result


def get_cron_summary():
    """Ключевые cron-задания."""
    try:
        out = subprocess.check_output(['crontab', '-l'], text=True)
        lines = [l.strip() for l in out.splitlines() if l.strip() and not l.startswith('#')]
        key = [l for l in lines if any(k in l for k in
               ['ai_daily', 'quarantine', 'candles_h4', 'futures_h4', 'supercandles_h4'])]
        return {'total_lines': len(lines), 'key_jobs': key}
    except Exception as e:
        return {'error': str(e)}


def get_trades_history(limit=20):
    """Последние N закрытых сделок с метриками (z_entry + z_exit + правила)."""
    db = ROOT / 'robots' / 'pairs_robot.db'
    if not db.exists():
        return []
    try:
        conn = sqlite3.connect(str(db))
        cur = conn.cursor()
        cur.execute("""
            SELECT c.pair_name, c.base_pair, c.timeframe, c.direction,
                   c.zscore AS z_exit, c.pnl, c.time AS time_exit,
                   c.price_a AS price_a_exit, c.price_b AS price_b_exit,
                   o.zscore AS z_entry, o.time AS time_entry,
                   o.price_a AS price_a_entry, o.price_b AS price_b_entry
            FROM trades c
            LEFT JOIN trades o ON o.pair_name = c.pair_name
                AND o.action = 'OPEN'
                AND o.time <= c.time
            WHERE c.action = 'CLOSE'
            GROUP BY c.id
            ORDER BY c.time DESC
            LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        conn.close()

        # Загружаем config для правил (entry_z, exit_z)
        config = {}
        try:
            c = json.load(open(CONFIG))
            config = {k: v.get('best_params', {}) for k, v in c.get('pairs', {}).items()}
        except Exception:
            pass

        result = []
        for r in rows:
            pair = r[0]
            bp = config.get(pair, {})
            result.append({
                'pair': pair,
                'base_pair': r[1],
                'timeframe': r[2],
                'direction': r[3],
                'z_entry': r[9],
                'z_exit': r[4],
                'pnl': r[5],
                'time_entry': r[10],
                'time_exit': r[6],
                'price_a_entry': r[11],
                'price_b_entry': r[12],
                'price_a_exit': r[7],
                'price_b_exit': r[8],
                'entry_z_rule': bp.get('entry_z'),
                'exit_z_rule': bp.get('exit_z'),
                'window': bp.get('window'),
            })
        return result
    except Exception as e:
        return [{'error': str(e)}]


def get_rules():
    """Правила торговли (вход/выход/ML/corr)."""
    return {
        'entry': 'Открытие: |z| >= entry_z (2.0-2.5, из config)',
        'exit': 'Закрытие: |z| <= exit_z (0.5, из config)',
        'ml_filter': 'ML: proba >= 0.5 → PASS, иначе BLOCK',
        'corr_gate': 'Corr: |corr| >= 0.5, иначе пропуск',
        'short_stock': 'Шорт по акциям запрещён',
        'time_window': 'Торговля: 07:00-18:00 МСК (M10/H4)',
        'cooldown': 'COOLDOWN_HOURS=4, MAX_HOLD_HOURS=120, MAX_POSITIONS=10',
        'commission': '0.05% (0.0005) на ногу',
    }


def get_signals_summary(hours=24):
    """Сводка сигналов за N часов (executed, missed, blocked)."""
    db = ROOT / 'robots' / 'pairs_robot.db'
    if not db.exists():
        return {}
    try:
        conn = sqlite3.connect(str(db))
        cur = conn.cursor()
        cutoff = (datetime.now() - __import__('datetime').timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
        # Общая статистика
        cur.execute("""
            SELECT status, reason, COUNT(*)
            FROM signals
            WHERE time >= ?
            GROUP BY status, reason
            ORDER BY COUNT(*) DESC
        """, (cutoff,))
        rows = cur.fetchall()
        stats = [{'status': r[0], 'reason': r[1], 'count': r[2]} for r in rows]
        # Топ-5 свежих
        cur.execute("""
            SELECT pair_name, status, reason, z, corr, time
            FROM signals
            WHERE time >= ?
            ORDER BY time DESC
            LIMIT 20
        """, (cutoff,))
        recent = cur.fetchall()
        conn.close()
        return {
            'stats': stats,
            'recent': [
                {'pair': r[0], 'status': r[1], 'reason': r[2], 'z': r[3], 'corr': r[4], 'time': r[5]}
                for r in recent
            ],
        }
    except Exception as e:
        return {'error': str(e)}


def get_robot_state_v2():
    """Состояние v2-робота (paused, running, updated)."""
    state_file = ROOT / 'robots' / 'robot_state_v2.json'
    if not state_file.exists():
        return None
    try:
        return json.load(open(state_file))
    except Exception as e:
        return {'error': str(e)}


def get_trades_history_v2(limit=20):
    """История сделок v2 (positions CLOSED)."""
    db = ROOT / 'robots' / 'pairs_robot_v2.db'
    if not db.exists():
        return []
    try:
        conn = sqlite3.connect(db)
        df = pd.read_sql_query(f'SELECT pair_name, direction, entry_z, exit_z, entry_time, exit_time, pnl FROM positions WHERE status="CLOSED" ORDER BY id DESC LIMIT {limit}', conn)
        conn.close()
        return df.to_dict(orient='records')
    except Exception as e:
        return [{'error': str(e)}]


def get_signals_summary_v2(hours=24):
    """Сводка сигналов v2 за N часов."""
    db = ROOT / 'robots' / 'pairs_robot_v2.db'
    if not db.exists():
        return {'stats': [], 'recent': []}
    try:
        conn = sqlite3.connect(db)
        stats = pd.read_sql_query(f"""
            SELECT status, reason, COUNT(*) as cnt
            FROM signals
            WHERE time > datetime('now','-{hours} hours')
            GROUP BY status, reason
            ORDER BY cnt DESC
        """, conn)
        recent = pd.read_sql_query(f"""
            SELECT time, pair_name, timeframe, z, corr, status, reason
            FROM signals
            ORDER BY id DESC
            LIMIT 20
        """, conn)
        conn.close()
        return {
            'stats': stats.to_dict(orient='records'),
            'recent': recent.to_dict(orient='records'),
        }
    except Exception as e:
        return {'error': str(e), 'stats': [], 'recent': []}




def get_robot_state_v4():
    import json
    from pathlib import Path
    f = Path('/root/finlab/robots/robot_state_test.json')
    if not f.exists(): return {'status': 'no_file'}
    try:
        return json.loads(f.read_text())
    except Exception as e:
        return {'status': f'error: {e}'}


def get_trades_history_v4(limit=20):
    import sqlite3
    from pathlib import Path
    f = Path('/root/finlab/robots/pairs_robot_test.db')
    if not f.exists(): return []
    try:
        con = sqlite3.connect(f); cur = con.cursor()
        rows = list(cur.execute("select pair_name, action, direction, pnl, time from trades order by id desc limit ?", (limit,)))
        con.close()
        return [{'pair': r[0], 'action': r[1], 'direction': r[2], 'pnl': r[3], 'time': r[4]} for r in rows]
    except Exception as e:
        return [{'error': str(e)}]


def get_signals_summary_v4(hours=24):
    import sqlite3
    from pathlib import Path
    from datetime import datetime, timedelta
    f = Path('/root/finlab/robots/pairs_robot_test.db')
    if not f.exists(): return {'status': 'no_file'}
    try:
        con = sqlite3.connect(f); cur = con.cursor()
        cutoff = (datetime.now() - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
        rows = list(cur.execute("select status, reason, count(*) from signals where time>=? group by status, reason order by 3 desc", (cutoff,)))
        con.close()
        return [{'status': r[0], 'reason': r[1], 'count': r[2]} for r in rows]
    except Exception as e:
        return {'error': str(e)}

def get_legend():
    """Легенда: v1 vs v2, поля signals, роботы. Чтобы AI не смешивал."""
    return {
        'robots': {
            'pairs_v1': {
                'name': '📊 Парная торговля',
                'db': 'robots/pairs_robot.db',
                'state': 'robots/robot_state.json',
                'config': 'FinLabPy/My_Indicators/pairs_config.json',
                'window': '07:00–18:00 МСК',
                'role': 'ЭТАЛОН. Не трогать. Сравнивать с v2.',
            },
            'pairs_v2': {
                'name': '📊 Парная торговля_v2',
                'db': 'robots/pairs_robot_v2.db',
                'state': 'robots/robot_state_v2.json',
                'config': 'FinLabPy/My_Indicators/pairs_config_v2.json',
                'window': '07:00–23:00 МСК',
                'role': 'ЭКСПЕРИМЕНТ. M10=1.8 (было 2.5). BR-GAZPF_H4 off. НЕ смешивать с v1.',
            },
            'pairs_v3': {
                'name': '📊 Парная торговля_v3',
                'db': 'robots/pairs_robot_v3.db',
                'state': 'robots/robot_state_v3.json',
                'config': 'FinLabPy/My_Indicators/pairs_config_v3.json',
                'window': '07:00–23:00 МСК',
                'role': 'ЭКСПЕРИМЕНТ. Кальман (адаптивная beta). 8 пар. НЕ смешивать с v1/v2.',
            },
            'futures_algopack_v1': {'name': '📊 Робот фьючерсов (Algopack)', 'db': 'futures_algopack_robot.db'},
            'futures_algopack_v2': {'name': '📊 Робот фьючерсов (v2)', 'db': 'futures_algopack_robot_v2.db'},
            'stocks': {'name': '📈 Робот акций (TradeStats)', 'db': 'tradestats_stocks_robot.db'},
        },
        'signals_fields': {
            'MISSED': 'сигнал не открыт. reason: time (вне окна), z_below_entry (|z|<entry_z), corr_gate (corr<0.5), MAX_POSITIONS, COOLDOWN.',
            'BLOCKED': 'сигнал отклонён ML-фильтром (ML_BLOCK) ИЛИ open_position (open_failed: шорт запрещён, price<=0, volume<1).',
            'EXECUTED': 'сигнал прошёл фильтры И открыл позицию. Если EXECUTED, но positions/trades пусты — проверить лог (short_forbidden).',
        },
        'filters': {
            'time': 'окно 07:00–18:00 (v1) / 07:00–23:00 (v2).',
            'corr_gate': 'corr < 0.5 — пропуск. Применяется к СИГНАЛАМ, не к enabled.',
            'ML_BLOCK': 'ML-модель отклонила (proba < порог).',
            'short_forbidden': 'шорт акции запрещён (BANE, BELU и др.) — SHORT_SPREAD пропускается.',
            'open_failed': 'open_position вернул False (шорт запрещён, price<=0, volume<1).',
        },
        'pairs_vs_futures': 'pairs (v1, v2, v3) — парная торговля акция+фьючерс. futures-algopack (v1, v2) — одиночные фьючерсы. stocks — акции.',
        'rule': 'РАЗЛИЧАЙ v1, v2 и v3. Указывай [v1], [v2] или [v3]. Не смешивай их PnL, signals, trades, config.',
    }


def get_config_v2():
    """Config v2 (эксперимент)."""
    path = ROOT / 'FinLabPy' / 'My_Indicators' / 'pairs_config_v2.json'
    if not path.exists():
        return None
    try:
        d = json.loads(path.read_text())
        enabled = [k for k, p in d.get('pairs', {}).items() if p.get('enabled')]
        return {
            'last_updated': d.get('last_updated'),
            'enabled_count': len(enabled),
            'enabled_pairs': enabled,
            'entry_z': {k: p.get('best_params', {}).get('entry_z') for k, p in d.get('pairs', {}).items() if p.get('enabled')},
        }
    except Exception as e:
        return {'error': str(e)}


def get_robot_state_v3():
    """Состояние v3-робота (paused, running, updated)."""
    state_file = ROOT / 'robots' / 'robot_state_v3.json'
    if not state_file.exists():
        return None
    try:
        return json.load(open(state_file))
    except Exception as e:
        return {'error': str(e)}


def get_trades_history_v3(limit=20):
    """История сделок v3 (positions CLOSED)."""
    db = ROOT / 'robots' / 'pairs_robot_v3.db'
    if not db.exists():
        return []
    try:
        conn = sqlite3.connect(db)
        df = pd.read_sql_query(f'SELECT pair_name, direction, entry_z, exit_z, entry_time, exit_time, pnl FROM positions WHERE status="CLOSED" ORDER BY id DESC LIMIT {limit}', conn)
        conn.close()
        return df.to_dict(orient='records')
    except Exception as e:
        return [{'error': str(e)}]


def get_signals_summary_v3(hours=24):
    """Сводка сигналов v3 за N часов."""
    db = ROOT / 'robots' / 'pairs_robot_v3.db'
    if not db.exists():
        return {'stats': [], 'recent': []}
    try:
        conn = sqlite3.connect(db)
        stats = pd.read_sql_query(f"""
            SELECT status, reason, COUNT(*) as cnt
            FROM signals
            WHERE time > datetime('now','-{hours} hours')
            GROUP BY status, reason
            ORDER BY cnt DESC
        """, conn)
        recent = pd.read_sql_query(f"""
            SELECT time, pair_name, timeframe, z, corr, status, reason
            FROM signals
            ORDER BY id DESC
            LIMIT 20
        """, conn)
        conn.close()
        return {'stats': stats.to_dict(orient='records'), 'recent': recent.to_dict(orient='records')}
    except Exception as e:
        return {'error': str(e), 'stats': [], 'recent': []}


def get_config_v3():
    """Config v3 (эксперимент: Кальман)."""
    path = ROOT / 'FinLabPy' / 'My_Indicators' / 'pairs_config_v3.json'
    if not path.exists():
        return None
    try:
        d = json.loads(path.read_text())
        enabled = [k for k, p in d.get('pairs', {}).items() if p.get('enabled')]
        return {
            'last_updated': d.get('last_updated'),
            'enabled_count': len(enabled),
            'enabled_pairs': enabled,
            'entry_z': {k: p.get('best_params', {}).get('entry_z') for k, p in d.get('pairs', {}).items() if p.get('enabled')},
        }
    except Exception as e:
        return {'error': str(e)}




def get_discovery_summary(max_rows=15):
    """Читает последний logs/discovery_*.csv, возвращает top-N новых пар."""
    from pathlib import Path
    import glob
    import pandas as pd
    logs = Path('/root/finlab/logs')
    files = sorted(glob.glob(str(logs / 'discovery_*.csv')))
    if not files:
        return {'status': 'no_file', 'rows': 0, 'top': []}
    latest = files[-1]
    try:
        df = pd.read_csv(latest)
    except Exception as e:
        return {'status': f'error: {e}', 'rows': 0, 'top': []}
    # top по is_coint, потом corr
    if 'is_coint' in df.columns:
        df = df.sort_values(['is_coint','corr'], ascending=[False, False])
    top = df.head(max_rows).to_dict(orient='records')
    return {
        'status': 'ok',
        'file': latest,
        'rows': len(df),
        'coint_count': int(df['is_coint'].sum()) if 'is_coint' in df.columns else 0,
        'top': top,
    }

def main():
    now = datetime.now()
    context = {
        'generated_at': now.strftime('%Y-%m-%d %H:%M:%S'),
        'legend': get_legend(),
        'freshness': get_freshness(),
        'index_divergence': get_index_divergence(),
        'config': get_config(),
        'config_v2': get_config_v2(),
        'quarantine': get_quarantine(),
        'algopack': get_algopack_summary(),
        'cron': get_cron_summary(),
        'trades_history': get_trades_history(limit=20),
        'rules': get_rules(),
        'signals_summary': get_signals_summary(hours=24),
        'robot_state_v2': get_robot_state_v2(),
        'trades_history_v2': get_trades_history_v2(limit=20),
        'signals_summary_v2': get_signals_summary_v2(hours=24),
        'config_v3': get_config_v3(),
        'robot_state_v3': get_robot_state_v3(),
        'trades_history_v3': get_trades_history_v3(limit=20),
        'signals_summary_v3': get_signals_summary_v3(hours=24),
    }
    print(json.dumps(context, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
