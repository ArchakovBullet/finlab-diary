"""
Проверка размера WORK_LOG.md в дневнике (локально).
Если файл превышает 500 КБ — отправляем уведомление в VK-бот.
"""
import os
import requests
from pathlib import Path

WORK_LOG_PATH = Path(r'E:\Python\FinLabProject\finlab-diary\WORK_LOG.md')
MAX_SIZE = 500 * 1024  # 500 КБ
VK_TOKEN = 'vk1.a.SlI9YR5W8dTnTYhVLlhNxXEmgDo6rImtWM1jEIpsZKb9KR8EB_x325YDm_Piu1QZffsffqKethgXWlBH3G0e_6h9DUmZEVzbCmXajTm3jW33hE1F49dUOVtjHGRLYN_5pYOnLN0ZiFpdu_DVVqPHLfShNWDBN1prFS7Yf1ec-PE75C_hhs5Mo7SANbnE_uWzA3dGP3_l3So8HfcUVW3f8A'
VK_GROUP_ID = '497763452'


def send_vk_message(message):
    """Отправить сообщение в VK"""
    if not VK_TOKEN:
        print('❌ VK_TOKEN не настроен')
        return
    
    url = 'https://api.vk.com/method/messages.send'
    params = {
        'access_token': VK_TOKEN,
        'peer_id': VK_GROUP_ID,
        'message': message,
        'random_id': 0,
        'v': '5.131'
    }
    r = requests.post(url, params=params, timeout=10)
    if r.status_code == 200:
        print('✅ VK уведомление отправлено')
    else:
        print(f'❌ Ошибка VK: {r.status_code} {r.text[:100]}')


def check_size():
    if not WORK_LOG_PATH.exists():
        print(f'❌ Файл не найден: {WORK_LOG_PATH}')
        return
    
    size = WORK_LOG_PATH.stat().st_size
    size_kb = size / 1024
    
    print(f'📄 WORK_LOG.md: {size_kb:.1f} КБ (макс: {MAX_SIZE/1024:.0f} КБ)')
    
    if size > MAX_SIZE:
        message = (
            f'⚠️ ВНИМАНИЕ!\n'
            f'WORK_LOG.md превысил допустимый размер:\n'
            f'Текущий: {size_kb:.1f} КБ\n'
            f'Максимум: {MAX_SIZE/1024:.0f} КБ\n\n'
            f'Пора архивировать!'
        )
        send_vk_message(message)
        print('⚠️ Размер превышен! VK уведомление отправлено.')
    else:
        print('✅ Размер в норме.')


if __name__ == '__main__':
    check_size()
