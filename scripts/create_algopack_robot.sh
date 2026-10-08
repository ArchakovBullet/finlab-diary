#!/bin/bash
cd /root/finlab

# Копия текущего робота
cp robots/pairs_robot.py robots/pairs_robot_algopack.py
cp robots/pairs_robot.db robots/pairs_robot_algopack.db

# Меняем пути
/root/finlab/venv/bin/python << 'PYEOF'
from pathlib import Path
p = Path('/root/finlab/robots/pairs_robot_algopack.py')
text = p.read_text()

# DB_PATH
text = text.replace(
    "DB_PATH = ROOT / 'robots' / 'pairs_robot.db'",
    "DB_PATH = ROOT / 'robots' / 'pairs_robot_algopack.db'"
)

# COMMAND_FILE
text = text.replace(
    "COMMAND_FILE = ROOT / 'robots' / 'robot_command.txt'",
    "COMMAND_FILE = ROOT / 'robots' / 'robot_command_algopack.txt'"
)

# STATE_FILE
text = text.replace(
    "STATE_FILE = ROOT / 'robots' / 'robot_state.json'",
    "STATE_FILE = ROOT / 'robots' / 'robot_state_algopack.json'"
)

p.write_text(text)
print('OK: пути изменены')
PYEOF

echo "=== Синтаксис ==="
/root/finlab/venv/bin/python -m py_compile robots/pairs_robot_algopack.py && echo "OK"
