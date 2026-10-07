#!/bin/bash
FILE=robots/pairs_robot.py
cp "$FILE" "$FILE.bak_check_signals_new_$(date +%Y%m%d_%H%M%S)"

/root/finlab/venv/bin/python << 'PYEOF'
from pathlib import Path
p = Path('/root/finlab/robots/pairs_robot.py')
text = p.read_text()

# Добавляем _new_ok в блок проверок
old = """                # Проверка экспирации (не открывать за 2 дня)
                _expiry_ok = True
                if is_expiring_soon(ticker_a, days=2) or is_expiring_soon(ticker_b, days=2):
                    _expiry_ok = False

                # Проверяем вход (с фильтрами)
                if _is_trading_time and _vol_ok and _corr_ok and _expiry_ok:
                    if current_z >= entry_z and spread_trend > 0:
                        open_position(pair_name, base_pair, tf, 'SHORT_SPREAD', VOLUME, current_z, price_a, price_b)
                    elif current_z <= -entry_z and spread_trend < 0:
                        open_position(pair_name, base_pair, tf, 'LONG_SPREAD', VOLUME, current_z, price_a, price_b)
                elif not _expiry_ok:
                    print(f'  ⏰ {pair_name}: экспирация ≤2 дн. — не открываем')"""

new = """                # Проверка экспирации (не открывать за 2 дня)
                _expiry_ok = True
                if is_expiring_soon(ticker_a, days=2) or is_expiring_soon(ticker_b, days=2):
                    _expiry_ok = False

                # Проверка нового контракта (не открывать <3 дней после rollover)
                _new_ok = True
                if is_new_contract(ticker_a, days=3) or is_new_contract(ticker_b, days=3):
                    _new_ok = False

                # Проверяем вход (с фильтрами)
                if _is_trading_time and _vol_ok and _corr_ok and _expiry_ok and _new_ok:
                    if current_z >= entry_z and spread_trend > 0:
                        open_position(pair_name, base_pair, tf, 'SHORT_SPREAD', VOLUME, current_z, price_a, price_b)
                    elif current_z <= -entry_z and spread_trend < 0:
                        open_position(pair_name, base_pair, tf, 'LONG_SPREAD', VOLUME, current_z, price_a, price_b)
                elif not _new_ok:
                    print(f'  ⏰ {pair_name}: новый контракт <3 дн. — не открываем')
                elif not _expiry_ok:
                    print(f'  ⏰ {pair_name}: экспирация ≤2 дн. — не открываем')"""

if old in text:
    text = text.replace(old, new)
    p.write_text(text)
    print('OK: check_signals — is_new_contract добавлен')
else:
    print('НЕ НАЙДЕНО: паттерн не совпал')
    import re
    m = re.search(r'# Проверка экспирации.*?экспирация ≤2 дн.*?не открываем.*?\n', text, re.DOTALL)
    if m:
        print('Текущий код:')
        print(m.group(0)[:800])
PYEOF

echo ""
/root/finlab/venv/bin/python -m py_compile "$FILE" && echo "OK"
