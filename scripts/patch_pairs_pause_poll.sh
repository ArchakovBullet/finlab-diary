#!/bin/bash
FILE=robots/pairs_robot.py
cd /root/finlab
cp "$FILE" "$FILE.bak_pause_poll_$(date +%Y%m%d_%H%M%S)"
echo "Бэкап создан"

/root/finlab/venv/bin/python << 'PYEOF'
from pathlib import Path

p = Path('/root/finlab/robots/pairs_robot.py')
text = p.read_text()

old = """            # Если на паузе — только проверка стопов и экспирации
            if state.get('paused', True):
                check_expiry()
                check_time_exits()
                time.sleep(60)
                continue"""

new = """            # Если на паузе — только проверка стопов и экспирации
            if state.get('paused', True):
                check_expiry()
                check_time_exits()
                # Проверяем команды каждые 5 сек (быстрая реакция на RESUME)
                _paused_exit = False
                for _ in range(12):  # 12 × 5 = 60 сек
                    time.sleep(5)
                    _cmd = process_command()
                    if _cmd == 'PAUSE':
                        state['paused'] = True
                        save_state(state)
                        print('⏸️ PAUSE: уже на паузе')
                        break
                    elif _cmd == 'RESUME':
                        state['paused'] = False
                        save_state(state)
                        print('▶️ RESUME: торговля возобновлена')
                        break
                    elif _cmd == 'STOP':
                        print('🛑 STOP: graceful shutdown')
                        for pos in get_open_positions():
                            close_position(pos[0], pos[1], pos[2], pos[3], 0, 0, 0)
                        state['running'] = False
                        save_state(state)
                        running = False
                        _paused_exit = True
                        break
                if _paused_exit:
                    break
                continue"""

if old in text:
    text = text.replace(old, new)
    p.write_text(text)
    print('  OK: проверка команд каждые 5 сек при паузе')
else:
    print('  НЕ НАЙДЕНО: блок паузы')
    idx = text.find("if state.get('paused', True):")
    if idx != -1:
        print('  Контекст:')
        print(repr(text[idx:idx+300]))
PYEOF

echo ""
echo "=== Синтаксис ==="
/root/finlab/venv/bin/python -m py_compile "$FILE" && echo "OK"
