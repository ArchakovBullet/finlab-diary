# MIGRATION SUMMARY — finlab (28.09.2026)

## 2.1. Сервер и доступы
IP: 159.194.219.117 (VPS Beget, аккаунт gnomer123)
Проект: /root/finlab
Python venv: /root/finlab/venv/bin/python
VS Code Server: http://159.194.219.117:8080
Dashboard (Streamlit): :8501
HTTP (WORK_LOG + README): :8888

GitHub remotes:
- origin → https://github.com/ArchakovBullet/supercandles-data.git
- finlab-dashboard → https://github.com/ArchakovBullet/finlab-dashboard.git
- diary → https://github.com/ArchakovBullet/finlab-diary.git (не используем)

## 2.2. Состояние на 28.09.2026
Роботы (все masked):
- pairs_robot — убыточен, выключен. Оставляем, работаем позже
- stocks_robot — заменяем на megaalerts_robot
- futures_robot — заменяем на futures_algopack_robot
- futures_robot_baseline — удалить

Позиции бумажные: 0 / 0 / 0 / 0 (все закрыты FORCED_CLOSE 28.09).

Работают сервисы:
- finlab-dashboard.service (Streamlit :8501)
- finlab-http.service (:8888)

Cron сборщиков:
HI2, MegaAlerts, TradeStats, SuperCandles, candles, futoi, futoi_1h, futoi_4h,
funding, sector_indices, trin, lqdt.
Новое: candles_h4_aggregator.py — 30 18 * * * (21:30 МСК).
Закомментированы: restart, validate_crontab, weekly_pairs, дубликат futures_h4.
Эталон crontab: scripts/crontab/crontab_20260927.txt.
Бэкапы crontab: backups/crontab_*.txt.

## 2.3. Данные (в /root/finlab/data/)
(см. полную таблицу в исходной сводке — HI2, MegaAlerts, SuperCandles,
TradeStats, FutOI, Candles, Funding, Sector indices, LQDT)

## 2.4. Результаты тестов сигналов (подтверждено на данных)
ИСПОЛЬЗУЕМ:
MegaAlerts (акции), горизонт 5д:
- oi_low_min → ЛОНГ, mean +2.12%, excess +1.96%, n=112
- vol_b_99_9_pctl → ЛОНГ, +1.52%, +1.40%, n=28
- net_vol_99_9_pctl− → ШОРТ, −1.37%, −1.50%, n=16
Бенчмарк D1: +0.156% (5д). Комиссия: 0.28%.
Net edge: oi_low_min +1.68%, vol_b_99_9_pctl +1.07%, net_vol_− +0.5%.

FutOI (фьючерсы), 5д:
- yur_buy_ratio > 0.9q → ЛОНГ, +1.18%, +0.76%, n=235
- yur_buy_ratio > 0.8q → ЛОНГ, +0.88%, +0.46%, n=470
- fiz_buy_ratio < 0.2q → ЛОНГ, +1.04%, +0.62%, n=470
- yur_buy_ratio < 0.2q → ШОРТ, −0.53%, −0.95%, n=470
- fiz_buy_ratio > 0.9q → ШОРТ, −0.19%, −0.61%, n=236
Бенчмарк D1: +0.42% (5д).
Net edge: yur_buy_ratio > 0.9q +0.48%, fiz_buy_ratio < 0.2q +0.34%.

TradeStats (фьючерсы):
- val_net > 0.8q → ЛОНГ 5д, +0.87%, +1.15%, n=607
- val_net < 0.2q → ШОРТ 5д, −1.28%, −1.00%, n=607
- trades_net > 0.8q → ЛОНГ 5д, +0.62%, +0.90%, n=607
- trades_net < 0.2q → ШОРТ 5д, −1.24%, −0.96%, n=607
- disb > 0.8q → ЛОНГ 1д, +0.38%, +0.44%, n=607
- disb < 0.2q → ШОРТ 1д, −0.66%, −0.60%, n=607
Бенчмарк D1: −0.28% (5д), −0.06% (1д).
Net edge: val_net +0.6..+0.9%, trades_net +0.3..+0.6%.

ОТМЕТАЕМ:
- HI2 — walk-forward провал (fold 1: net_edge 0.16%, Sharpe −0.11)
- SuperCandles — направления нет, только vol → |fwd| = 0.24
- MegaAlerts pr_high_max — выбросы (median −0.79% << mean −5.02%)
- Синергия MegaAlerts + FutOI — артефакт дублей (n=1–3)
- Синергия с HI2 / IMOEX — не подтверждена

НЕ ТРОГАЛИ (потенциал):
- HI2: 11 из 14 метрик (hhi_passive*, hhi_volume)
- TradeStats: 31 из 33 (im, oi_open/high/low/close, pr_*)
- FutOI: 8 из 12 (fiz_total, yur_total, *_delta)
- MegaAlerts: 6 из 9 (threshold, value, reference)

## 2.5. Скрипты (в /root/finlab/scripts/)
Тестеры: signal_tester.py, megaalerts_inspect.py, megaalerts_debug.py,
megaalerts_tester.py, megaalerts_edge_test.py, megaalerts_wf_test.py,
megaalerts_synergy.py, megaalerts_triple_test.py, megaalerts_validate.py,
test_tradestats_extra.py, test_futoi_extra.py, microstructure_probe.py,
cross_tickers.py.
Утилиты: inspect_parquet.py, fix_keyring_dup.py.
Агрегаторы (FinLabPy/DataCollectors/): candles_h4_aggregator.py (новый).

## 2.6. План на 29.09.2026
1. Проверить pairs_config.json (закоммитить финальный результат).
2. Найти LQDT-сравнение: grep -n "lqdt\|LQDT" robots/*.py
3. megaalerts_robot.py (акции): лонг oi_low_min, vol_b_99_9_pctl;
   шорт net_vol_99_9_pctl−; горизонт 5д; LQDT; бумажный режим.
4. futures_algopack_robot.py (фьючерсы): FutOI + TradeStats; LQDT; бумажный.
5. Дашборд app_v2.py: новые роботы + beat_lqdt_rate.

## 2.7. Техбэклог
- push_supercandles: токен ghp_... в remote URL → credential.helper
- HHRU_D1.parquet отсутствует (робот masked) — разобраться
- FinLabPy/Utils/Logger.py:1 — SyntaxWarning: invalid escape sequence '\P'
- Кнопки Pause/Stop в дашборде:
  Pause — робот отключён, новые позиции не открывает, открытые НЕ закрывает.
  Stop — graceful shutdown, закрывает все позиции, VK-уведомление.
- VK-уведомления при systemctl stop
- Атомарное закрытие парных ног (pairs): двухфазное CLOSING → CLOSED,
  leg_a_state/leg_b_state, unwind, идемпотентность + crash-recovery
- pairs: оптимизатор долгий (timeout 300s), H4 есть — проверить «нет данных» для H4-пар
- Дополнительные метрики (85%):
  HI2: hhi_passive*, hhi_volume
  TradeStats: im, oi_*, pr_*
  FutOI: *_total, *_delta
  MegaAlerts: threshold, value
- Сравнение с LQDT — в новые роботы и в дашборд

## 2.8. Важные уроки и правила
- keyring_pass.cfg (base64) — только Python-скриптом, не nano/sed
- В nano нельзя вставлять команды из шелла
- H4 для акций не собирался — баг конфигурации, починен
- Валидация результатов обязательна: +6.7% оказались артефактом дублей
- Walk-forward обязателен для каждого сигнала
- Схемы БД роботов разные: positions (pairs), futures_positions,
  stock_positions. Нет closed_at/close_note
- systemctl stop НЕ закрывает позиции робота — чистится вручную
- disabled ≠ masked. Политика: робот, который может набрать позиции — только masked
- Комиссия 0.28% (0.14% × 2)
- Бенчмарк D1 — обязательно сравнивать с LQDT (безрисковая ~16–17% годовых)

## 2.9. Формат ответа
Проблема/Выяснение → Рекомендация → Команды → План → Ожидаемый результат.
Обращение: «Напарник».

## 2.10. Ссылки с commit hash
Актуальный коммит: 5ac7bf3
https://raw.githubusercontent.com/ArchakovBullet/supercandles-data/5ac7bf3/WORK_LOG.md
https://raw.githubusercontent.com/ArchakovBullet/supercandles-data/5ac7bf3/README.md
