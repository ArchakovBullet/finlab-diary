#!/bin/bash
FILE=robots/pairs_robot.py
cp "$FILE" "$FILE.bak_main_v2_$(date +%Y%m%d_%H%M%S)"
echo "Бэкап создан"

/root/finlab/venv/bin/python << 'PYEOF'
from pathlib import Path

p = Path('/root/finlab/robots/pairs_robot.py')
text = p.read_text()

# Уникальные маркеры
start_marker = 'def main():'
end_marker = 'def is_pair_in_cooldown('

start = text.find(start_marker)
end = text.find(end_marker)

if start == -1:
    print('  ❌ Не найден def main():')
elif end == -1:
    print('  ❌ Не найден def is_pair_in_cooldown(')
elif end <= start:
    print('  ❌ end_marker раньше start_marker')
else:
    # Показать текущий main() — первые 200 символов
    print('  Текущий main() (первые 200 симв):')
    print(repr(text[start:start+200]))
    print('')
    
    new_main = '''def main():
    print("=" * 60)
    print(f"🤖 РОБОТ ПАРНОЙ ТОРГОВЛИ | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print(f"Депозит: {DEPOSIT} ₽")
    print(f"Объём: {VOLUME} {VOLUME_TYPE}")
    print(f"Проверка: M10 — каждые {CHECK_INTERVALS['M10']//60} мин, H1 — каждые {CHECK_INTERVALS['H1']//3600} ч")
    print("=" * 60)

    # Инициализация БД
    init_db()

    # Проверка экспираций
    check_expiry()

    # Проверка TIME_EXIT
    check_time_exits()

    # Загружаем конфиг пар
    with open(CONFIG_PATH, 'r') as f:
        pairs_config = json.load(f)

    running = True
    last_check = {'M10': 0, 'H1': 0, 'H4': 0}

    while running:
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

            time.sleep(1)

        except KeyboardInterrupt:
            print("🛑 Остановлено пользователем")
            break
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(5)

    print("✅ Робот остановлен")

'''
    
    text = text[:start] + new_main + text[end:]
    p.write_text(text)
    print('  OK: main() заменён целиком')

PYEOF

echo ""
echo "=== Синтаксис ==="
/root/finlab/venv/bin/python -m py_compile "$FILE" && echo "OK"
