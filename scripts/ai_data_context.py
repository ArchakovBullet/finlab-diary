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
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path('/root/finlab')
CANDLES = ROOT / 'data' / 'candles'
CONFIG = ROOT / 'FinLabPy' / 'My_Indicators' / 'pairs_config.json'
QUARANTINE_STATE = ROOT / 'logs' / 'pairs_quarantine_state.json'


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
    """Последние N закрытых сделок с метриками (z_entry + z_exit)."""
    db = ROOT / 'robots' / 'pairs_robot.db'
    if not db.exists():
        return []
    try:
        conn = sqlite3.connect(str(db))
        cur = conn.cursor()
        # Берём CLOSE-записи, для каждой ищем OPEN-запись по pair_name
        cur.execute("""
            SELECT c.pair_name, c.direction, c.zscore AS z_exit, c.pnl, c.time AS time_exit,
                   o.zscore AS z_entry, o.time AS time_entry
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
        return [
            {'pair': r[0], 'direction': r[1],
             'z_entry': r[5], 'z_exit': r[2],
             'pnl': r[3],
             'time_entry': r[6], 'time_exit': r[4]}
            for r in rows
        ]
    except Exception as e:
        return [{'error': str(e)}]


def main():
    now = datetime.now()
    context = {
        'generated_at': now.strftime('%Y-%m-%d %H:%M:%S'),
        'freshness': get_freshness(),
        'config': get_config(),
        'quarantine': get_quarantine(),
        'algopack': get_algopack_summary(),
        'cron': get_cron_summary(),
        'trades_history': get_trades_history(limit=20),
    }
    print(json.dumps(context, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
