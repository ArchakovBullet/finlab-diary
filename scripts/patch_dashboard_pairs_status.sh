#!/bin/bash
FILE=finlab_dashboard/app_v2.py
cp "$FILE" "$FILE.bak_pairs_status_$(date +%Y%m%d_%H%M%S)"
echo "Бэкап создан"

/root/finlab/venv/bin/python << 'PYEOF'
from pathlib import Path

p = Path('/root/finlab/finlab_dashboard/app_v2.py')
text = p.read_text()

# ============================================================
# Патч A: _active_robots — добавить finlab-robot
# ============================================================
old_a = """        for _svc in ['finlab-futures-algopack', 'finlab-futures-algopack-v2', 'finlab-stocks-tradestats']:
            _r = _sp.run(['systemctl', 'is-active', _svc], capture_output=True, text=True)
            if _r.stdout.strip() == 'active':
                _active_robots += 1"""

new_a = """        for _svc in ['finlab-futures-algopack', 'finlab-futures-algopack-v2', 'finlab-stocks-tradestats', 'finlab-robot']:
            _r = _sp.run(['systemctl', 'is-active', _svc], capture_output=True, text=True)
            if _r.stdout.strip() == 'active':
                _active_robots += 1"""

if old_a in text:
    text = text.replace(old_a, new_a)
    print('  OK: _active_robots — finlab-robot добавлен')
else:
    print('  НЕ НАЙДЕНО: _active_robots')

# ============================================================
# Патч B: paused из state.json + статус
# ============================================================
old_b = """        # Проверяем статус через systemd
        _result = subprocess.run(['systemctl', 'is-active', 'finlab-robot'], capture_output=True, text=True)
        _robot_running = _result.stdout.strip() == 'active'"""

new_b = """        # Проверяем статус через systemd
        _result = subprocess.run(['systemctl', 'is-active', 'finlab-robot'], capture_output=True, text=True)
        _robot_running = _result.stdout.strip() == 'active'

        # Читаем paused из robot_state.json
        import json as _json
        _robot_paused = True  # безопасный default
        _state_file = Path('/root/finlab/robots/robot_state.json')
        if _state_file.exists():
            try:
                _state = _json.loads(_state_file.read_text())
                _robot_paused = bool(_state.get('paused', True))
            except Exception:
                _robot_paused = True"""

if old_b in text:
    text = text.replace(old_b, new_b)
    print('  OK: paused из state.json добавлен')
else:
    print('  НЕ НАЙДЕНО: _robot_running')

# ============================================================
# Патч C: статус с учётом paused
# ============================================================
old_c = """        if _robot_running:
            if _open_count > 0:
                st.success(f"🟢 Робот работает ({_open_count} откр. позиций)")
            else:
                st.success("🟢 Робот работает")
        else:
            if _open_count > 0:
                st.warning(f"🟡 Робот на паузе ({_open_count} откр. позиций)")
            else:
                st.error("🔴 Робот остановлен (все позиции закрыты)")"""

new_c = """        if _robot_running and not _robot_paused:
            if _open_count > 0:
                st.success(f"🟢 Робот работает ({_open_count} откр. позиций)")
            else:
                st.success("🟢 Робот работает")
        elif _robot_running and _robot_paused:
            if _open_count > 0:
                st.warning(f"🟡 Робот на паузе ({_open_count} откр. позиций)")
            else:
                st.warning("🟡 Робот на паузе (торговля приостановлена)")
        else:
            if _open_count > 0:
                st.warning(f"🟡 Робот остановлен, но есть {_open_count} откр. позиций")
            else:
                st.error("🔴 Робот остановлен")"""

if old_c in text:
    text = text.replace(old_c, new_c)
    print('  OK: статус с учётом paused')
else:
    print('  НЕ НАЙДЕНО: блок статуса')

# ============================================================
# Патч D: кнопка «Старт» — с учётом paused
# ============================================================
old_d = """        with col_start:
            if _robot_running:
                # Робот работает — если на паузе → RESUME; если торгует → disabled
                if st.button("▶️ Старт", type="primary", use_container_width=True, key="start_running"):
                    Path('/root/finlab/robots/robot_command.txt').write_text('RESUME')
                    st.success('▶️ RESUME отправлен')
                    st.rerun()
            else:
                # Робот остановлен — systemctl start (поднимется в паузе)
                if st.button("▶️ Старт", type="secondary", use_container_width=True, key="start_stopped"):
                    subprocess.run(['systemctl', 'start', 'finlab-robot'], capture_output=True)
                    st.success('▶️ Робот запущен в паузе. Нажмите «Старт» ещё раз для RESUMЕ.')
                    st.rerun()"""

new_d = """        with col_start:
            if _robot_running and not _robot_paused:
                # Робот торгует — disabled
                st.button("▶️ Старт", type="primary", use_container_width=True, key="start_running_disabled", disabled=True)
            elif _robot_running and _robot_paused:
                # Робот на паузе — RESUME
                if st.button("▶️ Старт", type="primary", use_container_width=True, key="start_resume"):
                    Path('/root/finlab/robots/robot_command.txt').write_text('RESUME')
                    st.success('▶️ RESUME отправлен')
                    st.rerun()
            else:
                # Робот остановлен — systemctl start (поднимется в паузе)
                if st.button("▶️ Старт", type="secondary", use_container_width=True, key="start_stopped"):
                    subprocess.run(['systemctl', 'start', 'finlab-robot'], capture_output=True)
                    st.success('▶️ Робот запущен в паузе. Нажмите «Старт» ещё раз для RESUMЕ.')
                    st.rerun()"""

if old_d in text:
    text = text.replace(old_d, new_d)
    print('  OK: кнопка «Старт» с учётом paused')
else:
    print('  НЕ НАЙДЕНО: кнопка «Старт»')

# ============================================================
# Патч E: кнопка «Пауза» — с учётом paused
# ============================================================
old_e = """        with col_pause:
            if _robot_running:
                if st.button('⏸️ Пауза', type='secondary', use_container_width=True, key='pause_running'):
                    # Отправляем команду PAUSE (робот продолжает работать, но не открывает новые позиции)
                    Path('/root/finlab/robots/robot_command.txt').write_text('PAUSE')
                    st.warning('⏸️ Робот на паузе. Новые позиции не открываются.')
                    st.rerun()
            else:
                if _open_count > 0:
                    # Пауза — жёлтая круглая, disabled
                    st.markdown('''
                    <style>
                    .btn-pause-active {
                        width: 80px;
                        height: 80px;
                        border-radius: 50%;
                        background: linear-gradient(145deg, #FFC107, #FFA000);
                        color: white;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 14px;
                        font-weight: bold;
                        box-shadow: 0 6px 15px rgba(0,0,0,0.3);
                        margin: 0 auto;
                        cursor: not-allowed;
                        opacity: 0.8;
                    }
                    </style>
                    <div class="btn-pause-active">⏸️<br>Пауза</div>
                    ''', unsafe_allow_html=True)
                else:
                    st.button('⏸️ Пауза', type='secondary', use_container_width=True, key='pause_stopped', disabled=True)"""

new_e = """        with col_pause:
            if _robot_running and not _robot_paused:
                # Робот торгует — PAUSE
                if st.button('⏸️ Пауза', type='secondary', use_container_width=True, key='pause_active'):
                    Path('/root/finlab/robots/robot_command.txt').write_text('PAUSE')
                    st.warning('⏸️ PAUSE отправлен. Новые позиции не открываются.')
                    st.rerun()
            else:
                # На паузе или остановлен — disabled
                st.button('⏸️ Пауза', type='secondary', use_container_width=True, key='pause_disabled', disabled=True)"""

if old_e in text:
    text = text.replace(old_e, new_e)
    print('  OK: кнопка «Пауза» с учётом paused')
else:
    print('  НЕ НАЙДЕНО: кнопка «Пауза»')

p.write_text(text)
PYEOF

echo ""
echo "=== Синтаксис ==="
/root/finlab/venv/bin/python -m py_compile "$FILE" && echo "OK"
