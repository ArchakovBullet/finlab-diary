#!/bin/bash
FILE=robots/pairs_robot.py
cp "$FILE" "$FILE.bak_new_contract_$(date +%Y%m%d_%H%M%S)"
echo "Бэкап создан"

/root/finlab/venv/bin/python << 'PYEOF'
from pathlib import Path
p = Path('/root/finlab/robots/pairs_robot.py')
text = p.read_text()

# 1. Добавить CONTRACT_CHANGE_LOG_PATH в константы (после LAST_TRADEDATE_CACHE_PATH)
old_const = """LAST_TRADEDATE_CACHE_PATH = ROOT / 'robots' / 'contract_last_tradedate.json'"""
new_const = """LAST_TRADEDATE_CACHE_PATH = ROOT / 'robots' / 'contract_last_tradedate.json'
CONTRACT_CHANGE_LOG_PATH = ROOT / 'logs' / 'contract_change_log.json'"""
if old_const in text and 'CONTRACT_CHANGE_LOG_PATH' not in text:
    text = text.replace(old_const, new_const)
    print('  OK: CONTRACT_CHANGE_LOG_PATH добавлен')
else:
    print('  ПРОПУСК: CONTRACT_CHANGE_LOG_PATH уже есть или паттерн не найден')

# 2. Добавить is_new_contract после is_expiring_soon
old_func = """def is_expiring_soon(ticker, days=2):
    \"\"\"True, если контракт истекает в ближайшие N дней (только для фьючерсов).\"\"\"
    from datetime import date as _date
    last = get_last_tradedate(ticker)
    if last is None:
        return False  # не фьючерс или нет данных — не блокируем
    today = _date.today()
    days_left = (last - today).days
    return days_left <= days"""

new_func = """def is_expiring_soon(ticker, days=2):
    \"\"\"True, если контракт истекает в ближайшие N дней (только для фьючерсов).\"\"\"
    from datetime import date as _date
    last = get_last_tradedate(ticker)
    if last is None:
        return False  # не фьючерс или нет данных — не блокируем
    today = _date.today()
    days_left = (last - today).days
    return days_left <= days


def is_new_contract(ticker, days=3):
    \"\"\"True, если контракт сменился менее N дней назад.
    Защита от нестабильности после rollover.\"\"\"
    if not CONTRACT_CHANGE_LOG_PATH.exists():
        return False
    try:
        log = json.loads(CONTRACT_CHANGE_LOG_PATH.read_text())
        entry = log.get(ticker)
        if not entry:
            return False
        changed_at = datetime.strptime(entry['changed_at'], '%Y-%m-%d')
        return (datetime.now() - changed_at).days < days
    except Exception as e:
        print(f"  ⚠️ {ticker}: ошибка is_new_contract: {e}")
        return False"""

if old_func in text:
    text = text.replace(old_func, new_func)
    print('  OK: is_new_contract добавлен')
else:
    print('  НЕ НАЙДЕНО: паттерн is_expiring_soon не совпал')
    # показать где is_expiring_soon
    import re
    m = re.search(r'def is_expiring_soon.*?return days_left <= days', text, re.DOTALL)
    if m:
        print('  Текущий код:')
        print(m.group(0)[:500])

p.write_text(text)
PYEOF

echo ""
echo "=== Синтаксис ==="
/root/finlab/venv/bin/python -m py_compile "$FILE" && echo "OK"
