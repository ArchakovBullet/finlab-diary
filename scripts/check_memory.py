#!/usr/bin/env python3
"""Мониторинг заполнения памяти сервера с уведомлением в VK."""
import requests
import os
import shutil
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
load_dotenv('/root/finlab/.env')

# Добавляем путь для импорта
sys.path.insert(0, '/root/finlab')

import vk_api

# ========== КОНФИГ ==========
TOKEN = os.getenv("VK_TOKEN", "")
GROUP_ID = 238639379
ADMIN_ID = 497763452

# Пороги для уведомлений (в процентах)
DISK_THRESHOLD = 80  # Уведомлять при заполнении диска > 80%
RAM_THRESHOLD = 90   # Уведомлять при заполнении RAM > 90%
SWAP_THRESHOLD = 50  # Уведомлять при использовании swap > 50%

STATE_FILE = Path("/root/finlab/logs/memory_state.json")

def get_disk_usage():
    """Получить заполнение диска"""
    total, used, free = shutil.disk_usage('/')
    percent = (used / total) * 100
    return {
        'total_gb': round(total / (1024**3), 1),
        'used_gb': round(used / (1024**3), 1),
        'free_gb': round(free / (1024**3), 1),
        'percent': round(percent, 1)
    }

def get_ram_usage():
    """Получить заполнение RAM"""
    with open('/proc/meminfo', 'r') as f:
        lines = f.readlines()
    
    meminfo = {}
    for line in lines:
        parts = line.split(':')
        if len(parts) == 2:
            key = parts[0].strip()
            value = parts[1].strip().split()[0]
            try:
                meminfo[key] = int(value)
            except ValueError:
                pass
    
    total = meminfo.get('MemTotal', 0)
    available = meminfo.get('MemAvailable', 0)
    free = meminfo.get('MemFree', 0)
    
    if total > 0:
        used = total - available
        percent = (used / total) * 100
    else:
        used = 0
        percent = 0
    
    # Swap
    swap_total = meminfo.get('SwapTotal', 0)
    swap_free = meminfo.get('SwapFree', 0)
    swap_used = swap_total - swap_free if swap_total > 0 else 0
    swap_percent = (swap_used / swap_total * 100) if swap_total > 0 else 0
    
    return {
        'total_gb': round(total / (1024**2), 1),
        'used_gb': round(used / (1024**2), 1),
        'available_gb': round(available / (1024**2), 1),
        'percent': round(percent, 1),
        'swap_total_gb': round(swap_total / (1024**2), 1),
        'swap_used_gb': round(swap_used / (1024**2), 1),
        'swap_percent': round(swap_percent, 1)
    }

def load_state():
    """Загрузить предыдущее состояние"""
    if STATE_FILE.exists():
        import json
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_state(state):
    """Сохранить текущее состояние"""
    import json
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def check_memory():
    """Проверить память и вернуть сообщение при проблемах"""
    import json
    
    disk = get_disk_usage()
    ram = get_ram_usage()
    
    problems = []
    
    # Проверка диска
    if disk['percent'] > DISK_THRESHOLD:
        problems.append(f"💾 Диск заполнен на {disk['percent']}% ({disk['used_gb']}GB из {disk['total_gb']}GB)")
    
    # Проверка RAM
    if ram['percent'] > RAM_THRESHOLD:
        problems.append(f"🧠 RAM заполнена на {ram['percent']}% ({ram['used_gb']}GB из {ram['total_gb']}GB)")
    
    # Проверка swap
    if ram['swap_percent'] > SWAP_THRESHOLD:
        problems.append(f"🔄 Swap используется на {ram['swap_percent']}% ({ram['swap_used_gb']}GB из {ram['swap_total_gb']}GB)")
    
    # Сохранить состояние
    state = {
        'disk': disk,
        'ram': ram,
        'checked_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    save_state(state)
    
    if problems:
        return "⚠️ Внимание! Память сервера:\n" + "\n".join(problems)
    
    return None

def send_vk_message(peer_id, message):
    """Отправить сообщение в VK через API (как в роботах)."""
    try:
        response = requests.post(
            'https://api.vk.com/method/messages.send',
            params={
                'access_token': TOKEN,
                'peer_id': peer_id,
                'message': message,
                'random_id': int(datetime.now().timestamp() * 1000),
                'v': '5.131'
            },
            timeout=10
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
    # Инициализация VK
    vk_session = vk_api.VkApi(token=TOKEN)
    vk = vk_session.get_api()
    
    # Проверить память
    message = check_memory()
    
    # Получить текущее состояние для вывода
    disk = get_disk_usage()
    ram = get_ram_usage()
    
    print(f"💾 Диск: {disk['percent']}% ({disk['used_gb']}GB / {disk['total_gb']}GB)")
    print(f"🧠 RAM: {ram['percent']}% ({ram['used_gb']}GB / {ram['total_gb']}GB)")
    print(f"🔄 Swap: {ram['swap_percent']}% ({ram['swap_used_gb']}GB / {ram['swap_total_gb']}GB)")
    
    if message:
        print(f"\n{message}")
        # Отправить админу
        if send_vk_message(ADMIN_ID, message):
            print("✅ Уведомление отправлено в VK")
    else:
        print("\n✅ Память в норме")
