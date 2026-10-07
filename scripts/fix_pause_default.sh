#!/bin/bash

for FILE in robots/futures_algopack_robot.py robots/futures_algopack_robot_v2.py robots/tradestats_stocks_robot.py; do
    echo "=== $FILE ==="
    
    # Бэкап
    cp "$FILE" "$FILE.bak_pause_default_$(date +%Y%m%d_%H%M%S)"
    
    # Патч: get_state() — paused=True по умолчанию
    /root/finlab/venv/bin/python << PYEOF
from pathlib import Path
p = Path('$FILE')
text = p.read_text()

# Меняем два return {'paused': False} на True в get_state
old1 = """    if not STATE_FILE.exists():
        return {'paused': False}
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {'paused': False}"""

new1 = """    if not STATE_FILE.exists():
        # Безопасный default: не торговать, пока явно не получен RESUME
        return {'paused': True}
    try:
        state = json.loads(STATE_FILE.read_text())
        # Если ключа 'paused' нет — считаем, что на паузе (безопасно)
        if 'paused' not in state:
            state['paused'] = True
        return state
    except Exception:
        # Ошибка чтения — безопасный default
        return {'paused': True}"""

if old1 in text:
    text = text.replace(old1, new1)
    p.write_text(text)
    print('  OK: get_state() — paused=True по умолчанию')
else:
    print('  НЕ НАЙДЕНО: паттерн get_state не совпал')
    # показать текущий get_state
    import re
    m = re.search(r'def get_state\(\)[^}]+?\n\n', text, re.DOTALL)
    if m:
        print('  Текущий get_state:')
        print(m.group(0)[:600])
PYEOF
done

echo ""
echo "=== Проверка синтаксиса ==="
for FILE in robots/futures_algopack_robot.py robots/futures_algopack_robot_v2.py robots/tradestats_stocks_robot.py; do
    /root/finlab/venv/bin/python -m py_compile "$FILE" && echo "$FILE: OK"
done
