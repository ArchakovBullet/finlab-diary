#!/bin/bash
FILE=robots/pairs_robot.py
cp "$FILE" "$FILE.bak_main_pause_$(date +%Y%m%d_%H%M%S)"

/root/finlab/venv/bin/python << 'PYEOF'
from pathlib import Path
p = Path('/root/finlab/robots/pairs_robot.py')
text = p.read_text()

# Патч блока main() — PAUSE + RESUME + проверка paused
old = """    while running:
        try:
            # Неторговый день — новые позиции не открываем
            if not is_moex_trading_day():
                print('⏸️ Неторговый день — новые позиции не открываются')
                time.sleep(3600)
                continue

            # Проверяем команды
            cmd = process_command()
            if cmd == 'STOP':
                print("🛑 Команда STOP: закрываем все позиции")
                for pos in get_open_positions():
                    close_position(pos[0], pos[1], pos[2], pos[3], 0, 0, 0)
                running = False
                break
            elif cmd == 'PAUSE':
                print("⏸️ Команда PAUSE: робот приостановлен")
                running = False
                break

            current_time = time.time()

            # Проверяем сигналы по ТФ
            for tf, interval in CHECK_INTERVALS.items():
                if current_time - last_check[tf] >= interval:
                    check_signals_by_tf(pairs_config, tf)
                    last_check[tf] = current_time

            time.sleep(1)"""

new = """    while running:
        try:
            # Неторговый день — новые позиции не открываем
            if not is_moex_trading_day():
                print('⏸️ Неторговый день — новые позиции не открываются')
                time.sleep(3600)
                continue

            # Загружаем состояние
            state = load_state()

            # Проверяем команды
            cmd = process_command()
            if cmd == 'STOP':
                print("🛑 Команда STOP: закрываем все позиции")
                for pos in get_open_positions():
                    close_position(pos[0], pos[1], pos[2], pos[3], 0, 0, 0)
                state['running'] = False
                save_state(state)
                running = False
                break
            elif cmd == 'PAUSE':
                state['paused'] = True
                save_state(state)
                print("⏸️ Команда PAUSE: новые позиции не открываются (робот продолжает проверять стопы)")
                continue
            elif cmd == 'RESUME':
                state['paused'] = False
                save_state(state)
                print("▶️ Команда RESUME: торговля возобновлена")
                continue

            # Если на паузе — только проверка стопов и экспирации, новые позиции не открываем
            if state.get('paused', True):
                check_expiry()
                check_time_exits()
                time.sleep(60)
                continue

            current_time = time.time()

            # Проверяем сигналы по ТФ
            for tf, interval in CHECK_INTERVALS.items():
                if current_time - last_check[tf] >= interval:
                    check_signals_by_tf(pairs_config, tf)
                    last_check[tf] = current_time

            time.sleep(1)"""

if old in text:
    text = text.replace(old, new)
    p.write_text(text)
    print('OK: main() — PAUSE/RESUME/paused')
else:
    print('НЕ НАЙДЕНО: паттерн main() не совпал')
    import re
    m = re.search(r'while running:.*?time\.sleep\(1\)', text, re.DOTALL)
    if m:
        print('Текущий main():')
        print(m.group(0)[:1500])

p.write_text(text)
PYEOF

echo ""
echo "=== Синтаксис ==="
/root/finlab/venv/bin/python -m py_compile "$FILE" && echo "OK"
