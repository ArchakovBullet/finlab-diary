#!/usr/bin/env python3
"""Мониторинг изменений контрактов в contract_cache.json с уведомлением в VK."""
import os
import json
import sys
from pathlib import Path
from datetime import datetime

# Добавляем путь для импорта
sys.path.insert(0, '/root/finlab')

import requests

# ========== КОНФИГ ==========
from dotenv import load_dotenv
load_dotenv('/root/finlab/.env')
TOKEN = os.getenv("VK_TOKEN", "")
GROUP_ID = int(os.getenv("VK_GROUP_ID", "497763452"))
ADMIN_ID = 497763452

CACHE_FILE = Path("/root/finlab/FinLabPy/DataCollectors/contract_cache.json")
STATE_FILE = Path("/root/finlab/logs/contract_state.json")

def load_cache():
    """Загрузить текущий contract_cache.json"""
    with open(CACHE_FILE, 'r') as f:
        return json.load(f)

def load_state():
    """Загрузить предыдущее состояние"""
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_state(state):
    """Сохранить текущее состояние"""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2, default=str)


CHANGE_LOG_FILE = Path("/root/finlab/logs/contract_change_log.json")


def log_contract_change(ticker, old_code, new_code):
    """Записать смену контракта в лог."""
    log = {}
    if CHANGE_LOG_FILE.exists():
        try:
            with open(CHANGE_LOG_FILE, 'r') as f:
                log = json.load(f)
        except Exception:
            log = {}
    log[ticker] = {
        'old': old_code,
        'new': new_code,
        'changed_at': datetime.now().strftime('%Y-%m-%d'),
    }
    with open(CHANGE_LOG_FILE, 'w') as f:
        json.dump(log, f, indent=2, ensure_ascii=False)

def check_contract_changes():
    """Проверить изменения контрактов и отправить уведомление"""
    current = load_cache()
    previous = load_state()
    
    if not previous:
        # Первый запуск - просто сохраняем состояние
        save_state(current)
        print("✅ Первый запуск: состояние сохранено")
        return None
    
    changes = []
    for ticker, data in current.items():
        if ticker not in previous:
            changes.append(f"🆕 {ticker}: новый контракт {data.get('code', 'N/A')}")
        elif previous[ticker].get('code') != data.get('code'):
            changes.append(f"🔄 {ticker}: {previous[ticker].get('code', 'N/A')} → {data.get('code', 'N/A')}")
    
    save_state(current)
    
    if changes:
        return "📋 Обновление контрактов:\n" + "\n".join(changes)
    return None

def send_vk_message(message):
    """Отправить сообщение в VK через API (как в роботах)."""
    try:
        response = requests.post(
            'https://api.vk.com/method/messages.send',
            params={
                'access_token': TOKEN,
                'peer_id': GROUP_ID,
                'message': message,
                'random_id': int(datetime.now().timestamp() * 1000),
                'v': '5.131'
            }
        )
        result = response.json()
        if 'error' in result:
            print(f"❌ VK API error: {result['error']}")
            return False
        return True
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")
        return False

if __name__ == '__main__':
    # Проверить изменения
    message = check_contract_changes()

    if message:
        print(message)
        # Отправить в VK
        if send_vk_message(message):
            print("✅ Уведомление отправлено в VK")
    else:
        print("✅ Изменений контрактов не обнаружено")
