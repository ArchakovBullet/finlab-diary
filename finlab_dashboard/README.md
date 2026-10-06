# FinLab Dashboard

**Streamlit-дашборд для мониторинга торговых роботов FinLabPy.**

## Доступ

- URL: http://159.194.219.117:8501
- Systemd: `finlab-dashboard.service`
- Порт: 8501

## Структура (5 табов)

1. **📊 Обзор** — сводка по всем активным роботам:
   - Общий PnL (realized + unrealized).
   - Общий Win Rate.
   - Открытых позиций.
   - Активных роботов (3).
   - График PnL по дням.

2. **📊 Парная торговля** — DEAD (masked).

3. **📈 Робот акций (TradeStats)** — 10 акций (LONG, SCORE_MIN=4, HOLD_DAYS=5, RVI>=30).

4. **📊 Робот фьючерсов** — v1 (Algopack + FutOI).

5. **📊 Робот фьючерсов (v2)** — v2 (TradeStats + RVI>=30).

## Ключевые фичи

- **Unrealized PnL** — по OPEN-позициям (по M10 close), добавлен 06.10.2026.
- **Управление роботами** — PAUSE/STOP/RESUME (через command-файлы).
- **Метрики:** PnL, WR, Sharpe, beat LQDT.
- **Агрегация** — только по активным роботам (v1, v2, stocks).

## Файлы

- `app_v2.py` — основной файл дашборда (~320 КБ).
- Бэкапы: `app_v2.py.bak_*`.

## БД роботов

- `robots/futures_algopack_robot.db` — v1 (algopack_positions).
- `robots/futures_algopack_robot_v2.db` — v2 (algopack_positions).
- `robots/tradestats_stocks_robot.db` — stocks (algopack_positions).
- `robots/pairs_robot.db` — DEAD (positions).

## Обновления

- **06.10.2026** — Unrealized PnL в «Обзор».
- **03.10.2026** — таб «Обзор» — только активные роботы.

## Актуально на

06.10.2026, commit `1b47bdf`.
