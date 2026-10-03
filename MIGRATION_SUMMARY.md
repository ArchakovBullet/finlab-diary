# MIGRATION SUMMARY — FinLabPy

**Дата:** 03.10.2026 (суббота)
**Commit:** 0124980
**Сервер:** 159.194.219.117 (VPS Beget, root@lvkseaqdin)
**Проект:** /root/finlab
**Python:** /root/finlab/venv/bin/python

---

## 1. ССЫЛКИ (commit hash — не master, кэш CDN)

- https://raw.githubusercontent.com/ArchakovBullet/supercandles-data/0124980/WORK_LOG.md
- https://raw.githubusercontent.com/ArchakovBullet/supercandles-data/0124980/README.md
- https://raw.githubusercontent.com/ArchakovBullet/supercandles-data/0124980/MIGRATION_SUMMARY.md

---

## 2. АРХИТЕКТУРА

### Сервер
- IP: 159.194.219.117
- VS Code Server: http://159.194.219.117:8080
- Dashboard: :8501 (finlab-dashboard.service)
- HTTP: :8888 (finlab-http.service)

### Git remotes
- origin → https://github.com/ArchakovBullet/supercandles-data.git
- finlab-dashboard → https://github.com/ArchakovBullet/finlab-dashboard.git
- diary → https://github.com/ArchakovBullet/finlab-diary.git (не используем)

### Роботы в проде (3 шт)
| Сервис | Файл | БД | Статус |
|---|---|---|---|
| finlab-futures-algopack | robots/futures_algopack_robot.py | futures_algopack_robot.db | active |
| finlab-futures-algopack-v2 | robots/futures_algopack_robot_v2.py | futures_algopack_robot_v2.db | active |
| finlab-stocks-tradestats | robots/tradestats_stocks_robot.py | tradestats_stocks_robot.db | active |

### Старые роботы (masked)
- pairs_robot (masked, работает позже)
- stocks_robot (masked, DEAD CODE в дашборде)
- futures_robot (masked, удалён из дашборда)
- futures_robot_baseline (masked, удалить)

### Дашборд (finlab_dashboard/app_v2.py)
**Табы** (5):
1. 📊 Обзор (общая аналитика, 3 робота)
2. 📊 Парная торговля (DEAD CODE — masked)
3. 📈 Робот акций (TradeStats) — новый
4. 📊 Робот фьючерсов (v1) — старый
5. 📊 Робот фьючерсов (v2) — новый

**Убрано:**
- 📊 Сводка (навигация)
- 💰 Риск-менеджмент (сайдбар)
- 📈 Робот акций (старый) — DEAD CODE
- 📉 Робот фьючерсов (старый) — DEAD CODE

---

## 3. ДАННЫЕ (в /root/finlab/data/)

| Источник | Путь | Объём | Статус |
|---|---|---|---|
| HI2 | hi2_daily.parquet | 7971 строк, 216 тикеров | ✅ |
| TradeStats | tradestats/*.parquet | 69 файлов (49 акций + 20 фьючерсов) | ✅ |
| FutOI | futoi_1h/futoi_1h.parquet | 63 тикера | ✅ |
| Candles | candles/*_{D1,H1,M10,H4}.parquet | 299 тикеров × 4 ТФ | ✅ |
| MegaAlerts | mega_alerts/*.parquet | 303 файла, 1395 событий (после дедупа) | ✅ |
| Funding | funding/funding.parquet | 973 | ✅ |
| Sector | sector_indices/*.parquet | IMOEX, MOEXCH, MOEXCN, RVI | ✅ |
| LQDT | candles/LQDT_D1.parquet | ~93, benchmark ~16-17% годовых | ✅ |
| SuperCandles | supercandles/*.parquet | 134 (только акции) | ⚠️ vol only |

---

## 4. СИГНАЛЫ — РЕЗУЛЬТАТЫ ТЕСТОВ

### ✅ ИСПОЛЬЗУЕМ (для фьючерсов)

**TradeStats (5 сигналов):**
- pr_change — Sharpe 2.79 (H=5)
- pr_body — Sharpe 1.98
- sec_pr_range — Sharpe 1.54
- val_net — Sharpe 1.36
- vol_net — Sharpe 1.22

**FutOI (для v1):**
- yur_buy_ratio — Sharpe 2.47
- yur_long_ratio — Sharpe 1.36
- fiz_buy_ratio — Sharpe 0.96

**Честные тесты (rolling quantile 60д + вход по open):**
- Фьючерсы 5 сигналов + RVI>=30: H=3, порог=4 → Sharpe 2.17
- Фьючерсы 8 сигналов + RVI>=30: H=3, порог=2 → Sharpe 1.10
- Старая логика (8 сигналов, порог=3, H=5, без RVI): Sharpe 0.19

### ✅ ИСПОЛЬЗУЕМ (для акций)

**TradeStats (5 сигналов, только LONG):**
- pr_change, pr_body, sec_pr_range, val_net, vol_net

**Честные тесты:**
- Акции H=5, порог=4, RVI>=30: Sharpe 1.73, WR 53%, n=66

### ❌ ОТМЕТАЕМ
- HI2 — walk-forward провал (только отдельные метрики)
- SuperCandles — только волатильность
- MegaAlerts — oi_low_min только фьючерсы, vol_b мёртв после дедупа
- HMM — ОТКАЗ (03.10, не улучшает RVI)

---

## 5. РОБОТЫ — ПАРАМЕТРЫ

### futures_algopack_robot.py (v1)
- Сигналы: 5 TradeStats + 3 FutOI (8)
- Порог: SCORE_MIN = 3
- Горизонт: HOLD_DAYS = 5
- RVI: без фильтра
- MAX_POSITIONS: 15
- Тикеры: 21 фьючерс
- БД: futures_algopack_robot.db
- VK: 🤖Робот_фьючерсов

### futures_algopack_robot_v2.py (v2)
- Сигналы: 5 TradeStats
- Порог: SCORE_MIN = 4
- Горизонт: HOLD_DAYS = 3
- RVI: >= 30
- MAX_POSITIONS: 15
- Тикеры: 21 фьючерс
- БД: futures_algopack_robot_v2.db
- VK: 🤖Робот_фьючерсов_v2
- Ожидаемый Sharpe: 2.17 (честный)

### tradestats_stocks_robot.py
- Сигналы: 5 TradeStats (только LONG)
- Порог: SCORE_MIN = 4
- Горизонт: HOLD_DAYS = 5
- RVI: >= 30
- MAX_POSITIONS: 10
- Тикеры: 10 акций (GAZP, GMKN, HYDR, IRAO, LKOH, PLZL, ROSN, SBER, TATN, VTBR)
- БД: tradestats_stocks_robot.db
- VK: 🤖Робот_акций
- Ожидаемый Sharpe: 1.73 (честный)

---

## 6. МОДУЛИ СИГНАЛОВ

### FinLabPy/My_Indicators/algopack_signals.py
- get_combined_signal — для фьючерсов (5 TS + 3 FutOI)
- get_tradestats_signal — 5 сигналов TS
- get_futoi_signal — 3 сигнала FutOI

### FinLabPy/My_Indicators/tradestats_signals.py (НОВЫЙ, 01.10)
- get_tradestats_signal — 5 сигналов TS, только LONG, score >= 4
- Используется в tradestats_stocks_robot

---

## 7. СКРИПТЫ (в /root/finlab/scripts/)

### Тестеры
- signal_tester.py — единый шаблон
- megaalerts_*.py — 8 скриптов
- test_tradestats_extra.py
- test_futoi_extra.py

### Утилиты
- check_contract_changes.py — VK-уведомления при смене контрактов
- update_last_tradedate.py
- build_contract_points.py

### Агрегаторы (FinLabPy/DataCollectors/)
- candles_h4_aggregator.py — H4 из M10 (акции)
- tradestats_collector.py — расширен до 49 акций

---

## 8. ТЕХБЭКЛОГ

### Срочно
- MegaAlerts — 16 типов на акциях (проверить честно)
- WORK_LOG — запись за 02-03.10

### Средний приоритет
- Расширение tradestats — тест на 49 акциях (через 1-2 недели)
- ML — Logistic Regression на 5 сигналах
- HI2 + TradeStats комбинация

### Низкий приоритет
- push_supercandles — токен в remote URL → credential.helper
- HHRU_D1.parquet отсутствует (masked)
- FinLabPy/Utils/Logger.py:1 — SyntaxWarning: invalid escape
- Кнопки Pause/Stop в дашборде — tech debt

### Уроки (важные)
- keyring_pass.cfg — только Python-скриптом, не nano/sed
- H4 для акций — был баг, починен
- Валидация обязательна: +6.7% были артефактом дублей
- Walk-forward обязателен: rolling quantile 60д + вход по open
- Схемы БД роботов разные
- systemctl stop НЕ закрывает позиции
- disabled ≠ masked — робот только masked
- Комиссия 0.28% (0.14% × 2)
- Бенчмарк D1 — LQDT (~16-17% годовых)
- После каждого WORK_LOG — commit + push в 2 remote
- WORK_LOG.md в .gitignore → git add -f обязателен
- Запись в WORK_LOG — В КОНЕЦ через cat >>
- Не патчить Python через sed — только text.replace или nano

---

## 9. КЛЮЧЕВЫЕ КОМАНДЫ

### Роботы
systemctl status finlab-futures-algopack.service finlab-futures-algopack-v2.service finlab-stocks-tradestats.service --no-pager

### Позиции
sqlite3 robots/futures_algopack_robot.db "SELECT status, COUNT(*) FROM algopack_positions GROUP BY status;"
sqlite3 robots/futures_algopack_robot_v2.db "SELECT status, COUNT(*) FROM algopack_positions GROUP BY status;"
sqlite3 robots/tradestats_stocks_robot.db "SELECT status, COUNT(*) FROM algopack_positions GROUP BY status;"

### Дашборд
systemctl restart finlab-dashboard.service
systemctl status finlab-dashboard.service --no-pager | head -5

### Git
git log --oneline -10
git status

### Свежесть
/root/finlab/venv/bin/python /root/finlab/FinLabPy/DataCollectors/check_data_freshness.py

---

## 10. СЛЕДУЮЩИЕ ШАГИ

1. **MegaAlerts** — проверить 16 типов честно (rolling + open).
2. **WORK_LOG** — запись за 02-03.10.
3. **Дашборд — Обзор** — все 3 робота.
4. **Расширение** — тест на 49 акциях (через 1-2 недели).
5. **ML** — Logistic Regression.
6. **HI2** — честно.

---

## 11. ФОРМАТ ОТВЕТА

Строго так:
1. Проблема/Выяснение — что случилось.
2. Рекомендация — что делать.
3. Команды для терминала — готовые для копирования.
4. Дальнейший план — следующий шаг.
5. Ожидаемый результат — что должно быть.

Обращение: «Напарник».
