## 05.08.2026 (четверг) — дополнение 3

### ✅ Исправлены сборщики

**futoi_1h_aggregator.py:**
- Защита от деления на ноль (fillna)
- Заполнение NaN после outer merge
- diff() с группировкой по ticker

**futoi_4h_aggregator.py:**
- Убрана перезапись hour (сохраняется в block)
- Добавлен drop_duplicates
- Проверка обязательных колонок

**futoi_collector.py:**
- Проверка MOEX_TOKEN
- Обработчики исключений
- Валидация дат в _resolve_full_code
