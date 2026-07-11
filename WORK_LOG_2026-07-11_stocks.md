### 11.07: SuperTrend и HI2 для акций в сводке

- SuperTrend теперь отображается (calculate_supertrend возвращает кортеж)
- HI2 для акций загружается из hi2/*_hi2.parquet
- 1D сигнал через get_stock_scanner_verdict
- Рекомендация на основе decision
- 9 акций с сигналом на вход (все кроме LKOH, AFKS, ROSN)

### 11.07: 4H/1H сигналы для фьючерсов в сводке
- Загрузка futoi_4h.parquet и futoi_1h.parquet
- get_unified_scanner_verdict для расчёта сигналов
