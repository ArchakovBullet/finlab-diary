#!/bin/bash
FILE=finlab_dashboard/app_v2.py
cp "$FILE" "$FILE.bak_sleep_buttons_$(date +%Y%m%d_%H%M%S)"
echo "Бэкап создан"

/root/finlab/venv/bin/python << 'PYEOF'
from pathlib import Path

p = Path('/root/finlab/finlab_dashboard/app_v2.py')
text = p.read_text()

# Патч: добавить sleep после отправки PAUSE/RESUME/STOP
# 1. RESUME (кнопка «Старт» для парного)
old = """                if st.button("▶️ Старт", type="primary", use_container_width=True, key="start_resume"):
                    Path('/root/finlab/robots/robot_command.txt').write_text('RESUME')
                    st.success('▶️ RESUME отправлен')
                    st.rerun()"""

new = """                if st.button("▶️ Старт", type="primary", use_container_width=True, key="start_resume"):
                    Path('/root/finlab/robots/robot_command.txt').write_text('RESUME')
                    import time as _time
                    _time.sleep(3)
                    st.success('▶️ RESUME отправлен')
                    st.rerun()"""

if old in text:
    text = text.replace(old, new)
    print('  OK: sleep после RESUME')
else:
    print('  НЕ НАЙДЕНО: RESUME кнопка')

# 2. PAUSE
old2 = """                if st.button('⏸️ Пауза', type='secondary', use_container_width=True, key='pause_active'):
                    Path('/root/finlab/robots/robot_command.txt').write_text('PAUSE')
                    st.warning('⏸️ PAUSE отправлен. Новые позиции не открываются.')
                    st.rerun()"""

new2 = """                if st.button('⏸️ Пауза', type='secondary', use_container_width=True, key='pause_active'):
                    Path('/root/finlab/robots/robot_command.txt').write_text('PAUSE')
                    import time as _time
                    _time.sleep(3)
                    st.warning('⏸️ PAUSE отправлен. Новые позиции не открываются.')
                    st.rerun()"""

if old2 in text:
    text = text.replace(old2, new2)
    print('  OK: sleep после PAUSE')
else:
    print('  НЕ НАЙДЕНО: PAUSE кнопка')

# 3. STOP — уже есть sleep(5) — оставляем

p.write_text(text)
PYEOF

echo ""
echo "=== Синтаксис ==="
/root/finlab/venv/bin/python -m py_compile "$FILE" && echo "OK"
