#!/bin/bash
FILE=finlab_dashboard/app_v2.py
cd /root/finlab
cp "$FILE" "$FILE.bak_spinner_$(date +%Y%m%d_%H%M%S)"

/root/finlab/venv/bin/python << 'PYEOF'
from pathlib import Path

p = Path('/root/finlab/finlab_dashboard/app_v2.py')
text = p.read_text()

# RESUME — spinner
old1 = """                if st.button("▶️ Старт", type="primary", use_container_width=True, key="start_resume"):
                    Path('/root/finlab/robots/robot_command.txt').write_text('RESUME')
                    import time as _time
                    _time.sleep(3)
                    st.success('▶️ RESUME отправлен')
                    st.rerun()"""

new1 = """                if st.button("▶️ Старт", type="primary", use_container_width=True, key="start_resume"):
                    Path('/root/finlab/robots/robot_command.txt').write_text('RESUME')
                    with st.spinner('⏳ Отправка RESUME... (робот применит в течение 5 сек)'):
                        import time as _time
                        _time.sleep(3)
                    st.success('▶️ RESUME отправлен')
                    st.rerun()"""

if old1 in text:
    text = text.replace(old1, new1)
    print('  OK: spinner для RESUME')
else:
    print('  НЕ НАЙДЕНО: RESUME кнопка')

# PAUSE — spinner
old2 = """                if st.button('⏸️ Пауза', type='secondary', use_container_width=True, key='pause_active'):
                    Path('/root/finlab/robots/robot_command.txt').write_text('PAUSE')
                    import time as _time
                    _time.sleep(3)
                    st.warning('⏸️ PAUSE отправлен. Новые позиции не открываются.')
                    st.rerun()"""

new2 = """                if st.button('⏸️ Пауза', type='secondary', use_container_width=True, key='pause_active'):
                    Path('/root/finlab/robots/robot_command.txt').write_text('PAUSE')
                    with st.spinner('⏳ Отправка PAUSE... (робот применит в течение 5 сек)'):
                        import time as _time
                        _time.sleep(3)
                    st.warning('⏸️ PAUSE отправлен. Новые позиции не открываются.')
                    st.rerun()"""

if old2 in text:
    text = text.replace(old2, new2)
    print('  OK: spinner для PAUSE')
else:
    print('  НЕ НАЙДЕНО: PAUSE кнопка')

# STOP — spinner
old3 = """                if st.button("🛑 Стоп", type="secondary", use_container_width=True, key="stop_running"):
                    Path('/root/finlab/robots/robot_command.txt').write_text('STOP')
                    import time as _time
                    _time.sleep(5)
                    subprocess.run(['systemctl', 'stop', 'finlab-robot'], capture_output=True)
                    st.success("Робот остановлен! Все позиции закрыты.")
                    st.rerun()"""

new3 = """                if st.button("🛑 Стоп", type="secondary", use_container_width=True, key="stop_running"):
                    Path('/root/finlab/robots/robot_command.txt').write_text('STOP')
                    with st.spinner('⏳ Graceful shutdown... (закрываю позиции, ~5 сек)'):
                        import time as _time
                        _time.sleep(5)
                    subprocess.run(['systemctl', 'stop', 'finlab-robot'], capture_output=True)
                    st.success("Робот остановлен! Все позиции закрыты.")
                    st.rerun()"""

if old3 in text:
    text = text.replace(old3, new3)
    print('  OK: spinner для STOP')
else:
    print('  НЕ НАЙДЕНО: STOP кнопка')

p.write_text(text)
PYEOF

echo ""
echo "=== Синтаксис ==="
/root/finlab/venv/bin/python -m py_compile "$FILE" && echo "OK"
