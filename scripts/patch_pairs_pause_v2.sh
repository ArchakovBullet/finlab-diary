#!/bin/bash
FILE=robots/pairs_robot.py
cp "$FILE" "$FILE.bak_pause_v3_$(date +%Y%m%d_%H%M%S)"
echo "Бэкап создан"

/root/finlab/venv/bin/python << 'PYEOF'
from pathlib import Path
import re

p = Path('/root/finlab/robots/pairs_robot.py')
text = p.read_text()

# ============================================================
# 1. Добавить load_state / save_state — после save_tf_fresh_state
# ============================================================
marker = 'def save_tf_fresh_state(state):'
idx = text.find(marker)
if idx == -1:
    print('  ⚠️ Не найден save_tf_fresh_state — пропуск добавления')
else:
    # Найти конец функции save_tf_fresh_state — следующая "def " после marker
    next_def = text.find('\ndef ', idx + len(marker))
    if next_def == -1:
        print('  ⚠️ Не найден следующий def после save_tf_fresh_state')
    else:
        insert_pos = next_def + 1  # после \n
        new_funcs = '''def load_state() -> dict:
    """Загрузить состояние робота. Безопасный default: paused=True."""
    if not STATE_FILE.exists():
        return {'paused': True, 'running': False}
    try:
        state = json.loads(STATE_FILE.read_text())
        if 'paused' not in state:
            state['paused'] = True
        return state
    except Exception as e:
        print(f'  ⚠️ load_state: {e}')
        return {'paused': True, 'running': False}


def save_state(state: dict):
    """Сохранить состояние робота."""
    try:
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f'  ⚠️ save_state: {e}')


'''
        if 'def load_state' not in text:
            text = text[:insert_pos] + new_funcs + text[insert_pos:]
            print('  OK: load_state / save_state добавлены')
        else:
            print('  ПРОПУСК: load_state уже есть')

# ============================================================
# 2. Заменить блок while running: в main() через regex
# ============================================================
# Паттерн: от "    while running:" (с любым отступом) до "            time.sleep(1)"
pattern = re.compile(
    r'(\n[ \t]*while running:\n[\s\S]*?\n[ \t]*time\.sleep\(1\))',
    re.MULTILINE
)

old_main_block = '''    while running:
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

            time.sleep(1)'''

new_main_block = '''    while running:
        try:
            # Неторговый день — новые позиции не открываем
            if not is_moex_trading_day():
                print('⏸️ Неторговый день — новые позиции не открываются')
                time.sleep(3600)
                continue

            # Загружаем состояние (безопасный default: paused=True)
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

            # Если на паузе — только проверка стопов и экспирации
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

            time.sleep(1)'''

if old_main_block in text:
    text = text.replace(old_main_block, new_main_block)
    print('  OK: main() — PAUSE/RESUME/paused (точное совпадение)')
elif pattern.search(text):
    # Fallback: заменить через regex
    text = pattern.sub(new_main_block, text, count=1)
    print('  OK: main() — заменён через regex')
else:
    print('  НЕ НАЙДЕНО: блок main() не совпал')
    # Показать текущий блок
    m = pattern.search(text)
    if m:
        print('  Текущий блок:')
        print(m.group(0)[:800])

p.write_text(text)
PYEOF

echo ""
echo "=== Синтаксис ==="
/root/finlab/venv/bin/python -m py_compile "$FILE" && echo "OK"
