#!/bin/bash
FILE=robots/pairs_robot.py
cp "$FILE" "$FILE.bak_pause_v2_$(date +%Y%m%d_%H%M%S)"
echo "Бэкап создан"

/root/finlab/venv/bin/python << 'PYEOF'
from pathlib import Path
p = Path('/root/finlab/robots/pairs_robot.py')
text = p.read_text()

# 1. Добавить STATE_FILE если нет
if 'STATE_FILE' not in text:
    old = """COMMAND_FILE = ROOT / 'robots' / 'robot_command.txt'"""
    new = """COMMAND_FILE = ROOT / 'robots' / 'robot_command.txt'
STATE_FILE = ROOT / 'robots' / 'robot_state.json'"""
    if old in text:
        text = text.replace(old, new)
        print('  OK: STATE_FILE добавлен')
    else:
        print('  НЕ НАЙДЕНО: COMMAND_FILE')
else:
    print('  ПРОПУСК: STATE_FILE уже есть')

# 2. Добавить load_state / save_state после get_open_positions
old_func = """def get_open_positions():
    \"\"\"Получить открытые позиции.\"\"\"
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM positions WHERE status = 'OPEN'")
    positions = cursor.fetchall()
    conn.close()
    return positions"""

new_func = """def get_open_positions():
    \"\"\"Получить открытые позиции.\"\"\"
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM positions WHERE status = 'OPEN'")
    positions = cursor.fetchall()
    conn.close()
    return positions


def load_state() -> dict:
    \"\"\"Загрузить состояние робота. Безопасный default: paused=True.\"\"\"
    if not STATE_FILE.exists():
        return {'paused': True, 'running': False}
    try:
        state = json.loads(STATE_FILE.read_text())
        # Гарантируем наличие paused (безопасный default — True)
        if 'paused' not in state:
            state['paused'] = True
        return state
    except Exception as e:
        print(f'  ⚠️ load_state: {e}')
        return {'paused': True, 'running': False}


def save_state(state: dict):
    \"\"\"Сохранить состояние робота.\"\"\"
    try:
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f'  ⚠️ save_state: {e}')"""

if old_func in text:
    text = text.replace(old_func, new_func)
    print('  OK: load_state / save_state добавлены')
else:
    print('  НЕ НАЙДЕНО: get_open_positions')

p.write_text(text)
PYEOF

echo ""
echo "=== Синтаксис ==="
/root/finlab/venv/bin/python -m py_compile "$FILE" && echo "OK"
