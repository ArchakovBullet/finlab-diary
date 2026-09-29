# MIGRATION SUMMARY — FinLabPy

**Дата миграции:** 28–29.09.2026
**Commit:** 2fa7226 (или 5ac7bf3)
**Статус:** роботы masked, сигналы подтверждены, готовы к внедрению

## Что мигрировано

### Роботы (все masked)
- pairs_robot — оставлен, работает позже
- stocks_robot — заменяется на megaalerts_robot
- futures_robot — заменяется на futures_algopack_robot
- futures_robot_baseline — удалён (masked)

### Сигналы — подтверждены
**MegaAlerts (акции, 5д, комиссия 0.28%) — ПОСЛЕ ДЕДУПА:**
- vol_b_99_9_pctl → ЛОНГ, n=122 (тикеры: AFLT, ALRS, BANE, BELU, CHMF, GAZP, GMKN, HYDR, IRAO, ...)
- net_vol_99_9_pctl− → ШОРТ, n=73 (тикеры: ABIO, AFLT, AKRN, BANEP, BELU, GAZP, HYDR, LKOH, ...)
- ⚠️ oi_low_min — ИСКЛЮЧЁН: только фьючерсы (AS, BB, CI, DD, FE, I2, IN, IS, MA, ND, PI, PS), n=12 после дедупа. В акциях не использовать.

**MegaAlerts — критично:**
- 86% строк в данных — дубли (9765 → 1395).
- Правильный ключ дедупа: (ticker, tradedate, alert_type).
- Коллектор дописывает (append без дедупа) — баг, чинить.

**FutOI (фьючерсы, 5д):**
- yur_buy_ratio > 0.8q → ЛОНГ, +0.92%, n=470
- fiz_buy_ratio < 0.2q → ЛОНГ, +1.08%, n=470
- yur_buy_ratio < 0.2q → ШОРТ, −0.53%, n=470

**TradeStats (фьючерсы, 5д, n=607):**
- val_net > 0.8q → ЛОНГ, +0.87%
- val_net < 0.2q → ШОРТ, −1.00%
- trades_net > 0.8q → ЛОНГ, +0.62%
- trades_net < 0.2q → ШОРТ, −0.96%

### Сигналы — отмечены
- HI2 — walk-forward провал (42 дня данных)
- SuperCandles — направления нет, только vol
- MegaAlerts pr_high_max — выбросы
- Синергия MegaAlerts + FutOI — артефакт дублей

### Данные (в /root/finlab/data/)
- HI2: hi2_daily.parquet (7414 строк, 216 тикеров)
- MegaAlerts: mega_alerts/*.parquet (303 файла, 1395 событий)
- SuperCandles: supercandles/*.parquet (134 файла, акции)
- TradeStats: tradestats/*.parquet (32 файла, фьючерсы)
- FutOI: futoi_1h/futoi_1h.parquet (51953 строк, 63 тикера)
- Candles: candles/*_{D1,H1,M10,H4}.parquet (299 тикеров × 4 ТФ)
- Funding: funding/funding.parquet (973)
- Sector: sector_indices/*.parquet (IMOEX, MOEXCH, MOEXCN)
- LQDT: candles/LQDT_D1.parquet (~93, benchmark ~16-17% годовых)

## Что не сделано
- Код megaalerts_robot.py
- Код futures_algopack_robot.py
- Обновление дашборда (beat_lqdt_rate)
- LQDT-сравнение в новых роботах
- Финализация pairs_config.json

## Следующие шаги
1. Написать megaalerts_robot.py (акции, 5д)
2. Написать futures_algopack_robot.py (фьючерсы, FutOI + TradeStats)
3. Обновить дашборд
4. Перепрогнать оптимизатор пар (H4 данные появились 29.09)
