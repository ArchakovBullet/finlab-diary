## 06.08.2026 (среда)

### ✅ Сделано

**TradeStats для срочных фьючерсов:**
- Найдена и исправлена проблема: API требует полные коды (BRU6, SiU6...)
- Исправлен get_tradestats в MOEXPy — поддержка нового формата data.data
- Исправлен tradestats_collector.py — добавлен _resolve_full_code, убрано жёсткое len()
- Результат: +149 896 записей, все срочные фьючерсы собираются

**Чистка:**
- Удалены неактуальные сборщики: tinkoff, backup, m10_to_d1, check_health

**futoi_1h_aggregator.py:**
- Защита от деления на ноль (fillna)
- Заполнение NaN после outer merge
- diff() с группировкой по ticker

**futoi_4h_aggregator.py:**
- Убрана перезапись hour
- Добавлен drop_duplicates, проверка колонок

**futoi_collector.py:**
- Проверка MOEX_TOKEN, обработчики исключений, валидация дат

**Переписка с Algopack:**
- Отправлен ответ — данные найдены, проблема в MOEXPy исправлена

### 📝 На будущее

- GARCH/CRISIS: заменить на RVI
- HMM тесты на свежих данных
