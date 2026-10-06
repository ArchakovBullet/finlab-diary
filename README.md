# FinLabPy — Паспорт для AI-ассистента

**Актуально на:** 06.10.2026
**Commit:** `496b962`
**Сервер:** 159.194.219.117, `/root/finlab`
**Python:** `/root/finlab/venv/bin/python`

---

## ВАЖНО: Как читать контекст

**Главный документ — этот README.** Он содержит всё необходимое.

**Дополнительно:**
- **WORK_LOG.md** — история (что делали, когда).
- **MIGRATION_SUMMARY.md** — миграция 28–29.09 (архив).
- **finlab-diary/README.md** — дневник (зеркало).
- **finlab_dashboard/README.md** — описание дашборда.

**Ссылки (raw с commit hash — без кэша):**
- README: `https://raw.githubusercontent.com/ArchakovBullet/supercandles-data/496b962/README.md`
- WORK_LOG: `https://raw.githubusercontent.com/ArchakovBullet/supercandles-data/496b962/WORK_LOG.md`
- MIGRATION_SUMMARY: `https://raw.githubusercontent.com/ArchakovBullet/supercandles-data/496b962/MIGRATION_SUMMARY.md`

**Альтернативные URL (наш сервер, без CDN-кэша):**
- http://159.194.219.117:8888/README.md
- http://159.194.219.117:8888/WORK_LOG.md

**Где взять COMMIT_HASH:** `https://raw.githubusercontent.com/ArchakovBullet/supercandles-data/master/COMMIT_HASH.txt`

---

## 0. Идеология проекта: подход Джима Саймонса

**FinLabPy — количественная торговля в духе Renaissance Technologies.**

Принципы Джима Саймонса (Medallion Fund: ~66% годовых, 30+ лет):

1. **Данные — прежде всего.** Свежесть критична.
2. **Статистика, а не интуиция.** WR, PnL, просадка — основа решений.
3. **Системность и повторяемость.** Один алгоритм — один результат.
4. **Много маленьких ставок.** Диверсификация.
5. **Контроль риска.** Стопы, лимиты, фильтры.
6. **Постоянное улучшение.** Анализ каждой сделки.
7. **Наука, а не религия.** Гипотезы проверяются. Если не работает — отбрасываем.
8. **Walk-forward обязателен.** Без него — Sharpe завышен в 3–4 раза.
9. **Осторожно с p-hacking.** 20+ комбинаций — переобучение.

---

## 1. Доступы

- **Сервер:** root@159.194.219.117 (Ubuntu 24.04, Python 3.12).
- **Рабочая директория:** `/root/finlab`.
- **VS Code Server:** http://159.194.219.117:8080
- **Дашборд (Streamlit):** http://159.194.219.117:8501
- **HTTP-сервер (WORK_LOG, README):** http://159.194.219.117:8888
- **Токены:** `/root/finlab/.env`

---

## 2. Роботы в проде (3 активных)

### 1. finlab-futures-algopack (v1)
- **Файл:** `robots/futures_algopack_robot.py`
- **Логика:** 8 сигналов TradeStats + FutOI.
- **Параметры:** SCORE_MIN=3, HOLD_DAYS=5, **без RVI**.
- **Sharpe честный:** ~0.19.
- **Systemd:** `finlab-futures-algopack.service`
- **БД:** `robots/futures_algopack_robot.db` (`algopack_positions`)

### 2. finlab-futures-algopack-v2 (v2)
- **Файл:** `robots/futures_algopack_robot_v2.py`
- **Логика:** 5 сигналов TradeStats.
- **Параметры:** SCORE_MIN=4, HOLD_DAYS=3, **RVI>=30**.
- **Sharpe честный:** 2.17.
- **Systemd:** `finlab-futures-algopack-v2.service`
- **БД:** `robots/futures_algopack_robot_v2.db` (`algopack_positions`)

### 3. finlab-stocks-tradestats (stocks)
- **Файл:** `robots/tradestats_stocks_robot.py`
- **Логика:** 10 акций (только LONG).
- **Параметры:** SCORE_MIN=4, HOLD_DAYS=5, **RVI>=30**.
- **Sharpe честный:** 1.73.
- **Systemd:** `finlab-stocks-tradestats.service`
- **БД:** `robots/tradestats_stocks_robot.db` (`algopack_positions`)

### DEAD (masked):
- `finlab-robot.service` — pairs_robot (DEAD).
- `finlab-stocks-robot.service` — старый stocks (DEAD).
- `finlab-futures-robot.service` — старый futures (DEAD).
- `finlab-futures-baseline.service` — baseline (DEAD).

---

## 3. Дашборд (5 табов)

- **Файл:** `finlab_dashboard/app_v2.py` (~320 КБ).
- **Systemd:** `finlab-dashboard.service`.
- **Порт:** 8501.

**Табы:**
1. **📊 Обзор** — сводка по 3 активным роботам (realized + unrealized PnL).
2. **📊 Парная торговля** — DEAD (masked).
3. **📈 Робот акций (TradeStats)** — stocks.
4. **📊 Робот фьючерсов** — v1.
5. **📊 Робот фьючерсов (v2)** — v2.

---

## 4. Данные

- **TradeStats** (`data/tradestats/*.parquet`) — 69 файлов, 5.5 мес.
- **FutOI** (`data/futoi_1h/futoi_1h.parquet`) — 63 тикера, 5 мес.
- **MegaAlerts** (`data/mega_alerts/*.parquet`) — 303 файла, 19 типов.
- **HI2** (`data/hi2/hi2_daily.parquet`) — 7414 строк, 216 тикеров.
- **SuperCandles** (`data/supercandles/*.parquet`) — 134 файла (акции).
- **Candles** (`data/candles/*_{D1,H1,M10,H4}.parquet`) — 299 тикеров.
- **Funding** (`data/funding/funding.parquet`) — 973.
- **Sector indices** (`data/sector_indices/*.parquet`) — IMOEX, RVI.
- **LQDT** — бенчмарк (~16–17% годовых).

**Cron (основные):**
- TradeStats — 21:30 МСК (18:30 UTC).
- FutOI — каждый час (10:00–23:00 МСК).
- MegaAlerts — 21:30 МСК.
- HI2 — 21:00 МСК.
- SuperCandles — каждый час.
- Candles — каждые 10 мин (10:00–23:00 МСК).
- RVI — 22:00 МСК.

---

## 5. Тесты (walk-forward, rolling quantile 60д)

**Метод:** rolling quantile (60д) + вход по open (M10) + комиссия 0.28% + LQDT-бенчмарк.

**Результаты (06.10.2026):**

| Фильтр | Данные | Сделок | WR | Sharpe | Устойчивость |
|--------|--------|--------|-----|--------|--------------|
| baseline (Algopack) | — | 480 | 63.7% | 0.091 | ✅ |
| SuperTrend | Цена | 242 | 64.9% | **0.128** | ✅ |
| FutOI | FutOI | 98 | 73.5% | **0.251** | ⚠️ нестабилен |
| DMI/WillR/Force (цена) | Цена | 58–213 | 58–62% | 0.053–0.061 | ❌ |
| DMI+ST+WillR+Force (Algopack) | Algopack | 26 | 73.1% | 0.557 | ❌ переобучение |

**Выводы:**
- **Технические индикаторы (DMI, WillR, Force) — НЕ работают.**
- **SuperTrend — работает (0.128).**
- **FutOI — работает (0.251), но нестабилен.**
- **Baseline (Algopack) — устойчиво (0.091).**

---

## 6. Что не сделано

- **MegaAlerts** — 16 типов (робот не написан, edge не считан).
- **Расширение tradestats на 49 акциях** (тест).
- **ML — Logistic Regression.**
- **HI2 — честно.**
- **Парный робот + Algopack** (обсуждение).
- **v3 на FutOI + SuperTrend** (решение).
- **Unrealized PnL** — в блоках v1/v2/stocks (только в «Обзоре»).

---

## 7. Фиксы 03–06.10.2026

| # | Фикс | Commit |
|---|------|--------|
| 1 | `is_moex_trading_day` (сб/вс — 7-дневка) | `109ffd2` |
| 2 | Дашборд «Обзор» — только активные | `b859490` |
| 3 | Keyring (`token0/1/2`) | `0940a29` |
| 4 | stocks `CONTRACT_CHANGE_LOG_PATH` | `98b5418` |
| 5 | `is_tradestats_fresh` (tradedate+tradetime) | `98b5418` |
| 6 | v1 freshness + очистка БД | `98a2915` |
| 7 | Буферизация systemd (`stdbuf -oL -eL`) | `cd84631` |
| 8 | Unrealized PnL в дашборде | `7a7214f` |
| 9 | README finlab_dashboard + finlab-diary | `ded79fa`, `496b962` |

---

## 8. Правила (для AI)

1. **Обращение:** «Напарник».
2. **WORK_LOG** — в `.gitignore` → `git add -f`.
3. **Запись в WORK_LOG** — через `cat >>` (В КОНЕЦ).
4. **После WORK_LOG** — commit + push в **2 remote** (`origin` + `diary`).
5. **Не патчить Python** через sed — только `text.replace`.
6. **keyring_pass.cfg** — только Python-скриптом.
7. **Схемы БД:** `positions` / `futures_positions` / `stock_positions` / `algopack_positions`.
8. **`systemctl stop` НЕ закрывает позиции.**
9. **disabled ≠ masked** — робот только masked.
10. **Комиссия 0.28%** (0.14% × 2).
11. **Бенчмарк — LQDT** (~16–17% годовых).
12. **Формат ответа:** 1) Проблема, 2) Рекомендация, 3) Команды, 4) Дальнейший план, 5) Ожидаемый результат.
13. **Не трогать v2** (сравнительный эксперимент).

---

## 9. Ключевые файлы

**Роботы:**
- `robots/futures_algopack_robot.py` (v1)
- `robots/futures_algopack_robot_v2.py` (v2)
- `robots/tradestats_stocks_robot.py` (stocks)
- `robots/pairs_robot.py` (DEAD)

**Индикаторы:**
- `FinLabPy/My_Indicators/algopack_signals.py` (фьючерсы)
- `FinLabPy/My_Indicators/tradestats_signals.py` (акции)

**Дашборд:**
- `finlab_dashboard/app_v2.py`

**Скрипты:**
- `scripts/signal_tester.py`
- `scripts/megaalerts_tester.py`

---

## 10. Текущее состояние (06.10.2026)

- **v1:** 10 OPEN (06.10 10:03) + 3 OPEN (02.10, ждут time-exit 07.10).
- **v2:** 0 сделок.
- **stocks:** 0 сделок.
- **3 робота:** running.
- **Git:** чистый, commit `496b962`.

---

## 11. Ссылки

- **GitHub (supercandles-data):** https://github.com/ArchakovBullet/supercandles-data
- **GitHub (finlab-diary):** https://github.com/ArchakovBullet/finlab-diary
- **WORK_LOG (raw):** `https://raw.githubusercontent.com/ArchakovBullet/supercandles-data/496b962/WORK_LOG.md`
- **MIGRATION_SUMMARY (raw):** `https://raw.githubusercontent.com/ArchakovBullet/supercandles-data/496b962/MIGRATION_SUMMARY.md`

---

**Конец паспорта. При вопросах — см. WORK_LOG.**
