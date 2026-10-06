#!/usr/bin/env python3
"""
fix_keyring_dup.py — пересборка keyring_pass.cfg из .env MOEX_TOKEN.

Проблема: MOEXPy при ротации токена дописывает token0 в keyring_pass.cfg,
не удаляя старый. Файл накапливает дубли и перестаёт парситься
(configparser.DuplicateOptionError).

Решение: НЕ пытаться «спасти» битый файл. Пересобрать его из .env MOEX_TOKEN
заново. Логика MOEXPy:
  - длинный JWT (base64) → байты (utf-8)
  - разбить на чанки по 500 байт
  - каждый чанк → base64
  - записать как token0, token1, ... с отступом \t

Использование:
  python scripts/fix_keyring_dup.py            # fix
  python scripts/fix_keyring_dup.py --check    # только проверить
"""
import argparse
import base64
import shutil
import sys
from datetime import datetime
from pathlib import Path

from dotenv import dotenv_values
import configparser


CFG = Path('/root/.local/share/python_keyring/keyring_pass.cfg')
ENV = Path('/root/finlab/.env')
SERVICE = 'MOEXPy'
CHUNK_SIZE = 500


def rebuild():
    # 1. Читаем токен
    v = dotenv_values(ENV)
    token = v.get('MOEX_TOKEN', '').strip()
    if not token:
        print('ОШИБКА: MOEX_TOKEN не найден в .env', file=sys.stderr)
        return 1

    parts = token.split('.')
    if len(parts) != 3:
        print(f'ОШИБКА: MOEX_TOKEN не JWT ({len(parts)} частей)', file=sys.stderr)
        return 1

    print(f'Токен из .env: len={len(token)}, dots={token.count(".")}')

    # 2. Разбиваем на чанки по 500 байт
    token_bytes = token.encode('utf-8')
    chunks = [token_bytes[i:i+CHUNK_SIZE] for i in range(0, len(token_bytes), CHUNK_SIZE)]
    print(f'Байт: {len(token_bytes)}, чанков: {len(chunks)}')

    # 3. Кодируем каждый чанк в base64
    encoded = [base64.b64encode(c).decode('ascii') for c in chunks]
    for i, e in enumerate(encoded):
        print(f'  token{i}: len={len(e)}')

    # 4. Бэкап текущего файла
    TS = datetime.now().strftime('%Y%m%d_%H%M%S')
    if CFG.exists():
        bak = CFG.parent / f'{CFG.name}.bak_rebuild_{TS}'
        shutil.copy(CFG, bak)
        print(f'Бэкап: {bak}')

    # 5. Пишем keyring_pass.cfg
    lines = [f'[{SERVICE}]']
    for i, e in enumerate(encoded):
        lines.append(f'token{i} =')
        lines.append(f'\t{e}')
    lines.append('')
    content = '\n'.join(lines)
    CFG.write_text(content)
    print(f'Записан: {CFG} ({len(content)} байт)')


    # 6. Проверка
    print('\n--- Проверка ---')
    c = configparser.ConfigParser()
    c.read(CFG)
    print(f'configparser OK, keys: {list(c[SERVICE].keys())}')

    import keyring
    chunks_back = []
    for i in range(20):
        pw = keyring.get_password(SERVICE, f'token{i}')
        if pw is None:
            break
        chunks_back.append(pw)
    jwt = ''.join(chunks_back)
    match = (jwt == token)
    print(f'Склеено из keyring: len={len(jwt)}, dots={jwt.count(".")}')
    print(f'Совпадает с .env: {match}')
    return 0 if match else 1


def check():
    c = configparser.ConfigParser()
    try:
        c.read(CFG)
        print(f'configparser OK, sections: {c.sections()}')
        for s in c.sections():
            print(f'  [{s}] keys: {list(c[s].keys())}')
    except Exception as e:
        print(f'configparser FAIL: {e}', file=sys.stderr)
        return 1

    import keyring
    chunks = []
    for i in range(20):
        pw = keyring.get_password(SERVICE, f'token{i}')
        if pw is None:
            break
        chunks.append(pw)
    jwt = ''.join(chunks)
    env_tok = dotenv_values(ENV).get('MOEX_TOKEN', '').strip()
    print(f'keyring чанков: {len(chunks)}, jwt len: {len(jwt)}, dots: {jwt.count(".")}')
    print(f'Совпадает с .env: {jwt == env_tok}')
    return 0 if jwt == env_tok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true', help='только проверить')
    args = ap.parse_args()
    if args.check:
        return check()
    return rebuild()


if __name__ == '__main__':
    sys.exit(main())
