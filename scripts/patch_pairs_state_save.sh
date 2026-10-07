#!/bin/bash
FILE=robots/pairs_robot.py
cp "$FILE" "$FILE.bak_state_save_$(date +%Y%m%d_%H%M%S)"
echo "Бэкап создан"

/root/finlab/venv/bin/python << 'PYEOF'
from pathlib import Path

p = Path('/root/finlab/robots/pairs_robot.py')
text = p.read_text()

# Паттерн: после "init_db()" в main() — добавить save_state
old = """    # Инициализация БД
    init_db()

    # Проверка экспираций
    check_expiry()"""

new = """    # Инициализация БД
    init_db()

    # Сохраняем стартовое состояние (paused=True — безопасный default)
    _start_state = load_state()
    _start_state['running'] = True
    _start_state['updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    save_state(_start_state)
    print(f"📝 Состояние сохранено: running=True, paused={_start_state.get('paused')}")

    # Проверка экспираций
    check_expiry()"""

if old in text:
    text = text.replace(old, new)
    p.write_text(text)
    print('  OK: save_state при старте добавлен')
else:
    print('  НЕ НАЙДЕНО: паттерн init_db() + check_expiry()')
    # Показать контекст
    idx = text.find('init_db()')
    if idx != -1:
        print('  Контекст вокруг init_db():')
        print(repr(text[idx-50:idx+200]))

PYEOF

echo ""
echo "=== Синтаксис ==="
/root/finlab/venv/bin/python -m py_compile "$FILE" && echo "OK"
