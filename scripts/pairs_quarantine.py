#!/usr/bin/env python3
"""pairs_quarantine.py — авто-карантин деградировавших пар.

Читает robot.log, считает циклы с |corr| < 0.3 подряд.
Если 3+ циклов — enabled=false в pairs_config.json.
Если пара в карантине 14+ дней и corr восстановилась — enabled=true.

Не трогает прод-робота. Только config.
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path('/root/finlab')
LOG_FILE = ROOT / 'robots' / 'robot.log'
CONFIG_FILE = ROOT / 'FinLabPy' / 'My_Indicators' / 'pairs_config.json'
STATE_FILE = ROOT / 'logs' / 'pairs_quarantine_state.json'
QUARANTINE_LOG = ROOT / 'logs' / 'pairs_quarantine.log'

CORR_THRESHOLD = 0.3
CYCLES_TO_QUARANTINE = 3
QUARANTINE_DAYS = 14
LOG_TAIL_LINES = 5000

# VK (опционально)
VK_TOKEN = os.getenv('VK_TOKEN', '')
VK_GROUP_ID = os.getenv('VK_GROUP_ID', '')


def load_state():
    if STATE_FILE.exists():
        try:
            return json.load(open(STATE_FILE))
        except Exception:
            return {}
    return {}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    json.dump(state, open(STATE_FILE, 'w'), indent=2, ensure_ascii=False)


def parse_corr_from_log():
    """Возвращает {pair_name: [corr_values...]} — последние N значений."""
    if not LOG_FILE.exists():
        return {}
    with open(LOG_FILE, 'r', errors='replace') as f:
        lines = f.readlines()[-LOG_TAIL_LINES:]
    result = {}
    pattern = re.compile(r'([A-Z0-9\-]+_[A-Z0-9]+):.*corr=([\-\d\.]+)')
    for line in lines:
        m = pattern.search(line)
        if m:
            pair = m.group(1)
            try:
                corr = float(m.group(2))
                result.setdefault(pair, []).append(corr)
            except ValueError:
                continue
    return result


def send_vk(msg):
    if not VK_TOKEN or not VK_GROUP_ID:
        return
    try:
        import vk_api
        vk = vk_api.VkApi(token=VK_TOKEN).get_api()
        vk.messages.send(
            peer_id=int(VK_GROUP_ID),
            message=msg,
            random_id=int(datetime.now().timestamp() * 1000),
        )
    except Exception as e:
        print(f'VK error: {e}')


def main():
    config = json.load(open(CONFIG_FILE))
    pairs = config.get('pairs', {})
    corr_history = parse_corr_from_log()
    state = load_state()
    now = datetime.now()
    changes = []

    for pair_name, pair_data in pairs.items():
        if not pair_data.get('enabled'):
            continue
        corrs = corr_history.get(pair_name, [])
        if len(corrs) < CYCLES_TO_QUARANTINE:
            continue
        last_n = corrs[-CYCLES_TO_QUARANTINE:]
        if all(abs(c) < CORR_THRESHOLD for c in last_n):
            pair_data['enabled'] = False
            state[pair_name] = {
                'quarantined_at': now.strftime('%Y-%m-%d %H:%M:%S'),
                'last_corrs': last_n,
            }
            changes.append(f'🔴 {pair_name}: карантин (corr={last_n})')

    # Проверка выхода из карантина
    for pair_name, info in list(state.items()):
        if pair_name not in pairs:
            continue
        if pairs[pair_name].get('enabled'):
            continue
        q_at = datetime.strptime(info['quarantined_at'], '%Y-%m-%d %H:%M:%S')
        days_in_q = (now - q_at).days
        corrs = corr_history.get(pair_name, [])
        if days_in_q >= QUARANTINE_DAYS and corrs and abs(corrs[-1]) >= CORR_THRESHOLD:
            pairs[pair_name]['enabled'] = True
            del state[pair_name]
            changes.append(f'🟢 {pair_name}: возврат из карантина (corr={corrs[-1]:.2f})')

    if changes:
        config['last_updated'] = now.strftime('%Y-%m-%d %H:%M:%S')
        json.dump(config, open(CONFIG_FILE, 'w'), indent=2, ensure_ascii=False)
        save_state(state)
        msg = f"⚠️ Карантин пар ({now.strftime('%d.%m %H:%M')}):\n" + '\n'.join(changes)
        print(msg)
        with open(QUARANTINE_LOG, 'a') as f:
            f.write(f'\n[{now}] \n{msg}\n')
        send_vk(msg)
    else:
        save_state(state)
        print(f'[{now}] Изменений нет.')


if __name__ == '__main__':
    main()
