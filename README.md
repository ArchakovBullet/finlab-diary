## 06.08.2026 (среда) — дополнение

### ✅ Доделано

**GARCH → RVI:**
- Единый источник RVI (sector_indices/RVI_D1.parquet) на всех вкладках
- Порог CRISIS: 40 пунктов (вместо 30%)
- Пункты вместо процентов (38.0 п.)
- Исправлены: сводка, сканер фьючерсов, скринер акций, zweig_filter, market_regime

**Сборщики:**
- hi2_collector: TICKERS вынесен за класс
- hi2_daily: dir() → globals()
- futures_h4: dt.date/dt.time вместо cast
- futoi_daily: shift().over(ticker)
