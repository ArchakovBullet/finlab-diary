# FinLab — контекст для AI-диагноста

## Робот (pairs_robot.py)
- Парная торговля, mean reversion (стиль Саймонса).
- 11 enabled-пар: 3 M10 + 8 H4.
- 3 ML-модели (Logistic Regression): GD-PT_H4 (AUC 0.678), BELU-NB_M10 (0.639), SFIN-SH_M10 (0.618).
- 8 пар без ML (AUC < 0.6) — торгуют по z-score.
- Комиссия 0.28% (0.14% × 2). MAX_POSITIONS=10, COOLDOWN_HOURS=4, MAX_HOLD_HOURS=120.
- state: robots/robot_state.json. Логи: robots/robot.log. БД: robots/pairs_robot.db. Config: FinLabPy/My_Indicators/pairs_config.json.

## Данные (свежие)
- Candles: M10/H1/H4/D1, 299 тикеров.
- TradeStats: 5-мин, 09:05–23:50.
- FutOI 1h/4h, HI2, Funding, MegaAlerts (304 файла), SuperCandles, Sector indices (13, MOEXTL делистингован).
- Сборщики: cron ~25 заданий, все работают. Логи: logs/*_cron.log.

## Инфраструктура
- VK-бот: алерты (freshness, memory, contracts, collector logs). check_* в cron.
- DeepSeek (VseGPT): анализ логов, гипотезы. scripts/ai_diagnostic.py.
- HTTP: http://159.194.219.117:8888 — только README.md + WORK_LOG.md.
- Email: Yandex SMTP — для отчётов.

## ИЗВЕСТНЫЕ ФАКТЫ — НЕ СЧИТАТЬ АНОМАЛИЯМИ
- last_check_m10/last_check_h1 = null в robot_state.json — РУДИМЕНТ с 2026-09-02.
  Код их не пишет/не читает, дашборд не читает. Влияние: ноль.
- Робот перезапускается вручную при патчах (systemctl stop/start) — это норма, не крэш.
- H4 проверяется, хотя в шапке робота только M10/H1 — шапка устарела, логика верна.
- БД чистая после 09.10: open_positions=0, total_pnl=0 — норма.
- `total_pnl` в state = 0 — робот его не пишет (локальная переменная при закрытии сделки).
- MOEXTL — делистинг, удалён из сборщика.
- Оптимизация пар (weekly_pairs_optimization.py) — ОТКЛЮЧЕНА. Старая логика, 6 пар, w=30/rw=60. Не включать.
- update_config_coint.sh — устарел (6 пар). Не запускать.

## Правила
- Не патчить Python через sed — только text.replace через Python.
- `.env` — только nano или Python. НЕ sed (ломает UTF-8).
- WORK_LOG — через cat >>, потом git add -f, commit, push в 2 remote.
- Перед патчем — бэкап.
- Walk-forward 5 фолдов — обязателен.

## Приоритеты
- Прод: парный робот (наблюдение, ML-фильтр).
- Приоритет 2: ML-фильтр — ✅ завершён.
- Разведка: купонная лестница + парковщик, дивидендный календарь, lead-lag A/B.
