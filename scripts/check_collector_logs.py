#!/usr/bin/env python3
"""Проверка логов сборщиков на ошибки и уведомление в VK."""
import re
from pathlib import Path
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, '/root/finlab')
from dotenv import load_dotenv
load_dotenv('/root/finlab/.env')

import vk_api

LOGS_DIR = Path('/root/finlab/logs')
STATE_FILE = Path('/root/finlab/logs/collector_errors_state.json')
TOKEN = os.getenv('VK_TOKEN', '')
GROUP_ID = int(os.getenv('VK_GROUP_ID', '0'))

# Ключевые слова для поиска ошибок
ERROR_PATTERNS = [
    r'ERROR',
    r'ОШИБКА',
    r'Traceback',
    r'SSLCertVerificationError',
    r'ConnectionError',
    r'TimeoutError',
]

# Паттерны для игнорирования (не считаются ошибками)
IGNORE_PATTERNS = [
    r'keyring_pass\.cfg',
    r'РћС€РёР±РєР° РїСЂРё СЃРѕС…СЂР°РЅРµРЅРёРё С‚РѕРєРµРЅР°',
    r'РћС€РёР±РєР° РїСЂРё Р·Р°РіСЂСѓР·РєРµ С‚РѕРєРµРЅР°',
    r'ConnectionResetError',        # сканеры / обрывы клиента
    r'Connection reset by peer',    # то же, текст ошибки
    r'Bad request version',         # TLS на HTTP-порт
    r'Bad request syntax',          # бинарный мусор
    r'Unsupported method.*CONNECT', # прокси-сканеры
]

def load_state():
    """Загрузить предыдущее состояние ошибок."""
    import json
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_state(state):
    """Сохранить состояние ошибок."""
    import json
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def check_recent_logs():
    """Проверить логи за последние 2 часа на новые ошибки."""
    now = datetime.now()
    cutoff = now - timedelta(hours=2)
    state = load_state()
    problems = []
    new_errors = []
    
    for log_file in LOGS_DIR.glob('*.log'):
        # Пропускаем собственный лог
        if log_file.name == 'collector_logs_check.log':
            continue
        try:
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if mtime < cutoff:
                continue
            
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                # Проверяем последние 50 строк
                for line in lines[-50:]:
                    # Проверяем, не игнорируется ли строка
                    is_ignored = False
                    for ignore_pattern in IGNORE_PATTERNS:
                        if re.search(ignore_pattern, line, re.IGNORECASE):
                            is_ignored = True
                            break
                    
                    if is_ignored:
                        continue
                    
                    for pattern in ERROR_PATTERNS:
                        if re.search(pattern, line, re.IGNORECASE):
                            # Создаём ключ для дедупликации
                            error_key = f"{log_file.name}:{line.strip()[:80]}"
                            if error_key not in state:
                                problems.append(f"  📄 {log_file.name}: {line.strip()[:150]}")
                                new_errors.append(error_key)
                            break
        except:
            pass
    
    # Обновляем state
    for key in new_errors:
        state[key] = now.strftime('%Y-%m-%d %H:%M:%S')
    # Очищаем state от ошибок старше 24 часов
    state = {k: v for k, v in state.items() if (now - datetime.strptime(v, '%Y-%m-%d %H:%M:%S')).days < 1}
    save_state(state)
    
    return problems

def send_vk_message(msg):
    """Отправить сообщение в VK."""
    if not TOKEN:
        print("VK не настроен")
        return
    try:
        vk_session = vk_api.VkApi(token=TOKEN)
        vk = vk_session.get_api()
        vk.messages.send(
            peer_id=GROUP_ID,
            message=msg,
            random_id=int(datetime.now().timestamp() * 1000)
        )
        print("✅ VK-уведомление отправлено")
    except Exception as e:
        print(f"❌ Ошибка VK: {e}")

if __name__ == '__main__':
    state = load_state()
    problems = check_recent_logs()
    now_str = datetime.now().strftime('%d.%m %H:%M')

    # Ошибки, которые были в state
    prev_problems = set(state.get('active_problems', []))
    curr_problems = set(problems)

    # Новые проблемы
    new_problems = curr_problems - prev_problems

    # Восстановленные (были, теперь нет)
    recovered = prev_problems - curr_problems

    if new_problems:
        msg = f"⚠️ Обнаружены ошибки в логах сборщиков ({now_str}):\n"
        msg += "\n".join(sorted(new_problems)[:10])
        print(msg)
        send_vk_message(msg)

    if recovered:
        msg = f"✅ Сборщики восстановлены ({now_str}):\n"
        msg += "\n".join(sorted(recovered)[:10])
        print(msg)
        send_vk_message(msg)

    # Сохраняем текущие проблемы в state
    state['active_problems'] = sorted(curr_problems)
    state['last_check'] = now_str
    save_state(state)

    if not new_problems and not recovered:
        print(f'[{now_str}] Изменений нет. Активных проблем: {len(curr_problems)}')
    else:
        print(f"✅ Ошибок в логах не обнаружено ({datetime.now().strftime('%d.%m %H:%M')})")
