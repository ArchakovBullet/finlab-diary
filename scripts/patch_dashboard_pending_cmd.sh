#!/bin/bash
FILE=finlab_dashboard/app_v2.py
cd /root/finlab
cp "$FILE" "$FILE.bak_pending_cmd_$(date +%Y%m%d_%H%M%S)"

/root/finlab/venv/bin/python << 'PYEOF'
from pathlib import Path

p = Path('/root/finlab/finlab_dashboard/app_v2.py')
text = p.read_text()

old = """        # Читаем paused из robot_state.json
        import json as _json
        _robot_paused = True  # безопасный default
        _state_file = Path('/root/finlab/robots/robot_state.json')
        if _state_file.exists():
            try:
                _state = _json.loads(_state_file.read_text())
                _robot_paused = bool(_state.get('paused', True))
            except Exception:
                _robot_paused = True"""

new = """        # Читаем paused из robot_state.json
        import json as _json
        _robot_paused = True  # безопасный default
        _state_file = Path('/root/finlab/robots/robot_state.json')
        if _state_file.exists():
            try:
                _state = _json.loads(_state_file.read_text())
                _robot_paused = bool(_state.get('paused', True))
            except Exception:
                _robot_paused = True

        # Проверяем, есть ли неприменённая команда в robot_command.txt
        _pending_cmd = ''
        _cmd_file = Path('/root/finlab/robots/robot_command.txt')
        if _cmd_file.exists():
            try:
                _pending_cmd = _cmd_file.read_text().strip().upper()
            except Exception:
                _pending_cmd = ''"""

if old in text:
    text = text.replace(old, new)
    print('  OK: pending_cmd добавлен')
else:
    print('  НЕ НАЙДЕНО: блок paused')

old2 = """        if _robot_running and not _robot_paused:"""
new2 = """        if _pending_cmd:
            st.info(f'⏳ Команда {_pending_cmd} в обработке (робот применит её в течение ~5 сек)...')

        if _robot_running and not _robot_paused:"""

if old2 in text:
    text = text.replace(old2, new2, 1)
    print('  OK: info о pending_cmd')
else:
    print('  НЕ НАЙДЕНО: блок статуса')

p.write_text(text)
PYEOF

echo ""
echo "=== Синтаксис ==="
/root/finlab/venv/bin/python -m py_compile "$FILE" && echo "OK"
