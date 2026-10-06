# FinLabPy — Паспорт для AI-ассистента

**Актуально на:** 06.10.2026
**Commit:** `cc8b4b5`
**Сервер:** 159.194.219.117, `/root/finlab`
**Python:** `/root/finlab/venv/bin/python`

---

## ВАЖНО: Как читать контекст

**Этот README — стабильный «паспорт» проекта.** Меняется редко.

**Живая история — в WORK_LOG.md:**
- Текущее состояние роботов.
- Тесты (walk-forward, Sharpe, WR).
- Что не сделано.
- Фиксы и изменения.
- Ежедневные отчёты.

**Что читать первым:**
1. **README (этот файл)** — что такое FinLabPy, правила, доступы, ссылки.
2. **WORK_LOG.md** — что происходит сейчас (роботы, тесты, задачи).

**Ссылки (raw с commit hash — без кэша):**
- README: `https://raw.githubusercontent.com/ArchakovBullet/supercandles-data/cc8b4b5/README.md`
- WORK_LOG: `https://raw.githubusercontent.com/ArchakovBullet/supercandles-data/cc8b4b5/WORK_LOG.md`
- MIGRATION_SUMMARY: `https://raw.githubusercontent.com/ArchakovBullet/supercandles-data/cc8b4b5/MIGRATION_SUMMARY.md`

**Альтернативные URL (наш сервер, без CDN-кэша):**
- http://159.194.219.117:8888/README.md
- http://159.194.219.117:8888/WORK_LOG.md

**Где взять COMMIT_HASH:** `https://raw.githubusercontent.com/ArchakovBullet/supercandles-data/master/COMMIT_HASH.txt`

**Автогенерация шаблона для нового чата:** `scripts/update_new_chat_template.sh`

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

## 2. Архитектура

### Роботы (3 активных + DEAD)

**Активные:**
- `finlab-futures-algopack` — v1 (фьючерсы, Algopack + FutOI).
- `finlab-futures-algopack-v2` — v2 (фьючерсы, TradeStats + RVI).
- `finlab-stocks-tradestats` — stocks (10 акций, LONG, RVI).

**DEAD (masked):**
- `finlab-robot` — pairs_robot (DEAD).
- `finlab-stocks-robot` — старый stocks (DEAD).
- `finlab-futures-robot` — старый futures (DEAD).
- `finlab-futures-baseline` — baseline (DEAD).

**Детали (параметры, Sharpe, состояние) — в WORK_LOG.**

### Дашборд

- **Файл:** `finlab_dashboard/app_v2.py`.
- **Systemd:** `finlab-dashboard.service`.
- **Порт:** 8501.
- **Табы:** Обзор, Парная (DEAD), Робот акций, Робот фьючерсов (v1), Робот фьючерсов (v2).
- **Описание:** `finlab_dashboard/README.md`.

### Инфраструктура

- `finlab-http.service` — HTTP-сервер (порт 8888, раздача WORK_LOG/README).
- Cron — сборщики данных (TradeStats, FutOI, MegaAlerts, HI2, SuperCandles, Candles, Funding, RVI, Sector indices).

---

## 3. Данные

**Источники (Parquet):**
- **TradeStats** (`data/tradestats/*.parquet`).
- **FutOI** (`data/futoi_1h/futoi_1h.parquet`).
- **MegaAlerts** (`data/mega_alerts/*.parquet`).
- **HI2** (`data/hi2/hi2_daily.parquet`).
- **SuperCandles** (`data/supercandles/*.parquet`).
- **Candles** (`data/candles/*_{D1,H1,M10,H4}.parquet`).
- **Funding** (`data/funding/funding.parquet`).
- **Sector indices** (`data/sector_indices/*.parquet`).
- **LQDT** — бенчмарк (~16–17% годовых).

**Детали (cron, объём, свежесть) — в WORK_LOG.**

---

## 4. Правила (для AI)

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
14. **README — стабильный. WORK_LOG — живой.**

---

## 5. Ключевые файлы

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
- `scripts/update_new_chat_template.sh`

**Документация:**
- `README.md` (этот файл).
- `WORK_LOG.md` (живая история).
- `MIGRATION_SUMMARY.md` (архив).
- `finlab-diary/README.md` (дневник).
- `finlab_dashboard/README.md` (дашборд).

---

## 6. Ссылки

- **GitHub (supercandles-data):** https://github.com/ArchakovBullet/supercandles-data
- **GitHub (finlab-diary):** https://github.com/ArchakovBullet/finlab-diary
- **WORK_LOG (raw):** `https://raw.githubusercontent.com/ArchakovBullet/supercandles-data/cc8b4b5/WORK_LOG.md`
- **MIGRATION_SUMMARY (raw):** `https://raw.githubusercontent.com/ArchakovBullet/supercandles-data/cc8b4b5/MIGRATION_SUMMARY.md`

---

**Конец паспорта. Живая история — в WORK_LOG.md.**
