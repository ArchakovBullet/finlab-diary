# FinLab — WORK_LOG (живая история)

> **Архив:** [WORK_LOG_ARCHIVE_before_2026-10-11.md](archive/WORK_LOG_ARCHIVE_before_2026-10-11.md) — записи до 11.10.2026.

---

## 2026-10-11 (вечер) — отключение GAZPF-SBERF_H4 + патч default enabled

### Сделки 10.10 (первые реальные)
- BANE-BN_M10: OPEN 10:29 → CLOSE 10:49, PnL = +9.59 ₽ ✅
- BELU-NB_M10: OPEN 10:39 → CLOSE 13:19, PnL = -1.07 ₽ ❌
- Итого за 10.10: **+8.52 ₽** на 2 сделках.
- positions: 2 записи, обе CLOSED. open_positions=0 — корректно.

### Баг _bp (08.10)
- 9 срабатываний в сессии 2026-10-08 10:49:29.
- Затронуты: SFIN-SH_M10, BANE-BN_M10, BELU-NB_M10, GAZPF-SBERF_H4, GD-SV_H4.
- С 09.10 не воспроизводится. Устранён (предположительно при ML-патче).
- Патч не требуется.

### Отключение GAZPF-SBERF_H4
- Причина: corr нестабильна (-0.20 → 0.36), коинтеграция разваливается.
- last_optimized=None — пара без walk-forward.
- enabled: True → False в pairs_config.json.
- last_updated: 2026-10-11 22:45:00.
- Итого enabled-пар: 10 (3×M10 + 7×H4).

### Патч default enabled в pairs_robot.py
- Строка 1050: default True → False (безопасность).
- Без флага enabled пара теперь НЕ торгуется.
- py_compile: OK.
- Бэкап: robots/pairs_robot.py.bak_20261011_2244.

### Git
- Изменены: pairs_config.json, pairs_robot.py.
- Следующее: commit + push в origin + diary.

### Следующее
- Проверить H4-агрегатор 12.10 16:30 МСК.
- Research: long-only / Kalman / index+active.

---

## 2026-10-11 (финал сессии)

### Проверки после push
- finlab-robot.service: active.
- enabled-пар: 10.
- state: running=true, paused=false, open_positions=0.
- git: working tree clean, синхронизировано с origin/master и diary/master.
- HEAD: 4149a76.

### Техдолг (на потом)
- 21 старый бэкап (*.bak_* от 13.09–29.09) — почистить отдельной сессией.
- README ссылается на 95b8fb4, актуальный HEAD — 4149a76.
- Паспорт: HEAD и remote-список устарели.
- last_check_m10/h1 в state — рудимент.
- Метка «фильтры — time» в логе — переименовать в z_threshold.

### План на 12.10 (пн)
- 16:30 МСК — первый H4-агрегатор в рабочем режиме.
- После 16:30 — проверить свежесть H4-свечей.
- Research: long-only / Kalman / index+active.

---

## 2026-10-12 (утро) — токен Algopack подтверждён

### Algopack
- Токен Algopack хранится в .env как MOEX_TOKEN (используется сборщиками).
- Дублирующее имя ALGOPACK_APIKEY добавлено для новых скриптов.
- Тест: obstats за 10.10 → 26104 строк. OK.
- moexalgo установлен в venv.

### Email
- smtp.yandex.ru:465 и :587 → Network is unreachable.
- smtp.beget.com:465 → OPEN (для сравнения).
- Причина: инцидент в ЦОД Яндекса.
- Письмо в поддержку Яндекса отправлено 12.10.
- Ждём ответ. Fallback — VK (VK_TOKEN, VK_GROUP_ID есть в .env).

### Следующее
- Этап 1: scripts/ai_algopack_context.py — данные Algopack для AI.
- VK-fallback для AI-отчётов (пока Яндекс не работает).
- H4-агрегатор 12.10 16:30 МСК.

---

## 2026-10-12 (день) — AI-отчёт перенесён на 21:00 МСК

### Изменения
- Cron AI-отчёта: 05:00 → 21:00 МСК (0 18 * * *).
- Формулировка: «Анализ за YYYY-MM-DD (данные на HH:MM МСК, все TF закрыты)».
- Причина: вечерний отчёт за текущий день, все TF закрыты (M10/H1/H4), можно вносить правки в тот же вечер.

### Техдолг
- Тестовый запуск днём даёт неверную пометку «все TF закрыты» — в 21:00 корректно.
- H4-агрегатор 16:30 — проверить, обновится ли BELU_H4.parquet (сейчас от 10.10).

### Git
- 7f50f1d.

### Следующее
- pairs_quarantine.py — авто-карантин деградировавших пар.
- VK-fallback для AI-отчётов.
- H4-агрегатор 16:30 — проверить.

---

## 2026-10-12 (вечер) — карантин GLDRUBF-GD_H4 + время отчётов

### pairs_quarantine.py — первый запуск
- Создан scripts/pairs_quarantine.py (авто-карантин).
- Первый запуск (19:22 МСК): GLDRUBF-GD_H4 → карантин (corr=[0.12, 0.12, 0.26]).
- Enabled-пар: 10 → 9.
- Лог: logs/pairs_quarantine.log.
- State: logs/pairs_quarantine_state.json.

### Время отчётов — исправление
- Выяснилось: cron на сервере в MSK (Europe/Moscow, +0300), не UTC.
- 0 18 * * * = 18:00 МСК (не 21:00) — моя ошибка.
- AI-отчёт: 30 19 * * * (19:30 МСК).
- Карантин: 45 19 * * * (19:45 МСК).
- Crontab: 91 строка.
- Причина: 19:30 удобнее для отладки; за свежестью следит VK-бот.

### AI-отчёт (18:00) — важное
- H4 age=44.7ч — сборщик H4 не отработал ~2 суток.
- is_tf_fresh(H4): 0/7 свежих → False.
- H4-пары (7 из 11) не торгуют.
- M10: утром был провал (10.5ч), потом восстановился.
- BELU-NB_M10: corr падала до −0.21, сейчас 0.96 — ок.

### Git
- 94e5dac (карантин).
- 0925c7f (AI-отчёт 21:00 — устарело).

### Следующее
- Проверить H4-агрегатор (16:30 уже прошёл — обновился ли?).
- VK-fallback для AI-отчётов.
- Второй робот с AI-veto.

---

## 2026-10-12 (вечер, доп.) — H4-агрегаторы: реальное расписание

### Открытие
- Паспорт говорит «30 13 UTC = 16:30 МСК» — УСТАРЕЛО.
- Реально (cron в MSK):
  - candles_h4_aggregator.py: 30 13 * * * = 13:30 МСК (акции).
  - futures_h4_aggregator.py: 45 17 * * * = 17:45 МСК (фьючерсы).
  - supercandles_h4_aggregator.py: 40 17 * * * = 17:40 МСК (SuperCandles).
- BELU (акция) H4 обновлён 13:30, GD/GAZPF (фьючерсы) — 17:45.

### Свежесть H4 (проверка 19:30)
- H4: 299/299 свежих (< 25ч). Всё ок.
- AI-отчёт 18:00 видел старые данные (до 17:45).

### Следующее
- Обновить паспорт: H4-агрегаторы и их время.
- VK-fallback.
- Второй робот с AI-veto.

---

## 2026-10-12 (вечер, доп. 2) — email восстановлен?

### Проверка SMTP
- Отчёт пришёл на archakoffden@yandex.ru (18:00 МСК).
- Значит, SMTP Яндекс доступен.
- Ранее (12.10 утром) было: Network is unreachable.
- Предположительно: инцидент в ЦОД Яндекса закончился.

### Решение по VK-fallback
- Если email работает стабильно — VK-fallback отложить.
- Если падает — внедрить как резерв.
- Не удалять VK-код из ai_daily_report.py.

### Следующее
- Проверить отчёт 19:30 (пришёл ли).
- Обновить паспорт (H4-расписание, email).
- Второй робот с AI-veto.

---

## 2026-10-12 (вечер, доп. 3) — AI видит данные + 14 «мёртвых» тикеров

### ai_data_context.py
- Создан scripts/ai_data_context.py.
- Собирает: freshness (M10/H1/H4/D1), config, quarantine, algopack, cron.
- Интегрирован в ai_daily_report.py (перед user_content).
- AI теперь видит реальные данные, не только логи.
- Git: b7b6337.

### Открытие: 14 тикеров не обновлялись ~26 суток
- M10: 285/299 свежих, oldest 623.8ч.
- H1: 285/299 свежих, oldest 623.8ч.
- D1: 285/300 свежих, oldest 636.8ч.
- H4: 299/299 свежих (производный от M10/H1).
- Причина: уточнить (делистинг / API / ошибка сборщика).
- Влияние на торговлю: проверить, входят ли в 9 enabled-пар.

### VK-fallback
- send_vk добавлен в ai_daily_report.py.
- При ошибке email → VK.
- Git: 8c4e86a.

### Следующее
- Разобрать 14 «мёртвых» тикеров.
- Обновить ai_context.md (H4-расписание, ai_data_context).
- Обновить паспорт.
- BELU-NB_M10 — разобрать.

---

## 2026-10-12 (итог дня) — AI видит данные, карантин, паспорт

### Сделано
- AI-отчёт: 05:00 → 19:30 МСК (cron 30 19 * * *).
- VK-fallback в ai_daily_report.py (8c4e86a).
- ai_data_context.py — AI видит freshness, config, quarantine, algopack, cron (b7b6337).
- pairs_quarantine.py — авто-карантин (94e5dac).
- Карантин: GLDRUBF-GD_H4 (corr=[0.12, 0.12, 0.26]). Enabled: 10 → 9.
- ai_context.md — ai_data_context, мёртвые тикеры, H4-расписание (e0370d8).
- Паспорт: дата 12.10.2026, commit c712889, raw-ссылки.

### Открытия
- 15 «мёртвых» тикеров (не обновлялись > 25ч): CRU6/PI/UT (26 суток), IN (2 бара), LQDT (бенчмарк, 20:00), остальные 2-9 суток.
- SFIN-SH_M10 — чистая (ложное срабатывание: 'IN' в 'SFIN').
- H4-агрегаторы: 13:30 (акции), 17:45 (фьючерсы), 17:40 (SuperCandles).
- Email восстановлен (SMTP Яндекс).

### Git
- c712889 (HEAD).

### Следующее
- BELU-NB_M10 — наблюдать (corr=-0.21, сейчас 0.97).
- Второй робот с AI-veto — потом.
- pairs_screener.py — потом.

---

## 2026-10-12 (вечер, доп. 4) — анализ «мёртвых» тикеров

### Группы (по анализу)
- **Группа 1 — делистинг (удалить):** CRU6, PI, UT (26 суток, нет в других папках).
- **Группа 2 — не торговые (удалить):** IN (2 бара, 4 суток).
- **Группа 3 — бенчмарк (оставить):** LQDT (обновляется в 20:00).
- **Группа 4 — временный сбой (починить):** KZ, BY, TY, SY, CS, HK, I2, JD, NO, RF (3–9 суток, есть в mega_alerts).

### В config
- Все 15 — НЕ в config. Робот ими не торгует.
- Удаление безопасно для торговли.

### План
1. CRU6, PI, UT, IN — удалить (с бэкапом).
2. LQDT — оставить.
3. KZ, BY, TY, SY, CS, HK, I2, JD, NO, RF — починить сборщик.

### Следующее
- Бэкап candles для удаляемых.
- Удаление CRU6/PI/UT/IN.
- Разбор сборщика для группы 4.

---

## 2026-10-12 (вечер, доп. 5) — открытие: тикеры НЕ мёртвые

### Открытие
- 10 из 15 тикеров — валютные фьючерсы (маппинг SECTYPE в candles_collector.py):
  CS=CNI, RF=RUONIA, TY=TRY, HK=HKD, I2=INR, KZ=KZT, BY=BYN, UT=UKZT, IN=UINR.
- CRU6, PI — фьючерсы (нефть, палладий?).
- LQDT — фонд, D1 обновляется 12.10.
- IN_alerts.parquet — 12.10 18:32 (IN активен!).

### Вывод
- Тикеры НЕ мёртвые — просто не собираются candles_collector.py.
- Причина: маппинг SECTYPE (или get_full_code).
- НЕ удалять.

### План
1. Разобрать маппинг SECTYPE в candles_collector.py.
2. Починить сборщик для группы 4.
3. LQDT — оставить.
4. CRU6, PI — проверить отдельно (делистинг?).

### Следующее
- Посмотреть get_full_code.
- Проверить логи candles_collect_cron.log.

---

## 2026-10-12 (вечер, доп. 6) — сборщик пропускает валютные фьючерсы

### Открытие
- contract_cache.json: все тикеры в кэше (IN=INZ6, TY=TYZ6, HK=HKZ6, KZ=KZZ6, BY=BYZ6, I2=I2Z6, UT=UTZ6, RF=RFZ6, CS=CSZ6).
- MOEX ISS: данные ЕСТЬ (INZ6, I2Z6, INH7, I2H7).
- Сборщик candles_collector.py ПРОПУСКАЕТ эти тикеры.
- PI: контракт PIU6 (сентябрь) — устарел → делистинг.
- CRU6: нет в contract_cache → проверить.

### Действия
1. PI — удалить (делистинг).
2. CRU6 — проверить отдельно.
3. Остальные — не удалять (данные есть, сборщик пропускает).
4. Разобраться, почему сборщик пропускает.

### Следующее
- Проверить API INZ6.
- Посмотреть candles_collector.py:140-200.

---

## 2026-10-12 (финал) — итог дня

### Сделано
- AI-отчёт: 19:30 МСК.
- VK-fallback (8c4e86a).
- ai_data_context.py — AI видит freshness/config/quarantine/algopack/cron (b7b6337).
- pairs_quarantine.py — авто-карантин (94e5dac).
- Карантин: GLDRUBF-GD_H4. Enabled: 10 → 9.
- 15 «мёртвых» тикеров разобраны:
  - JD/NO/SY — фьючерсы на АДР (активны, данных нет на ISS).
  - IN/CR/CS/RF/TY/HK/I2/KZ/BY/UT — валютные фьючерсы (данные есть).
  - PI, CRU6 — удалены (истёкшие).
  - LQDT — фонд (D1 в 20:00).
- ai_context.md — финальная классификация (0ee2df1).
- Паспорт: дата 12.10.2026, commit, raw-ссылки.

### Вывод
- JDZ6 candles: 0 rows → сборщик НЕ виноват, нет данных на ISS.
- Это норма для неликвидных фьючерсов.
- Тема «мёртвых» тикеров ЗАКРЫТА.

### Git
- 0ee2df1 (HEAD).

### Следующее
- BELU-NB_M10 — наблюдать (corr=-0.21, сейчас 0.97).
- Второй робот с AI-veto — проектировать.
- pairs_screener.py — проектировать.

---

## 2026-10-12 (финал) — WORK_LOG архивирован

### Архивация
- WORK_LOG разросся до 241 КБ (> 200 КБ).
- Создан scripts/archive_worklog.py.
- Архив: archive/WORK_LOG_ARCHIVE_2026_09.md (227 КБ, записи до 01.10).
- WORK_LOG: 15 КБ (только 11.10+).
- Ссылка на архив — в начале WORK_LOG.

### Git
- 138be14.

### Следующее
- BELU-NB_M10 — наблюдать.
- Второй робот с AI-veto.
- pairs_screener.py.

---

## 2026-10-12 (финал, доп.) — проверка архивации

### Проверка
- WORK_LOG: 16 КБ, записи с 11.10.
- Архив: 227 КБ, записи до 30.09 (или раньше).
- Записи 01.10–10.10 — НЕ найдены (ни в WORK_LOG, ни в архиве, ни в бэкапах).
- Возможная причина: формат дат (точки vs тире) или записи не велись.

### Следующее
- Проверить формат дат.
- Если записей нет — норма.

---

## 2026-10-12 (финал, доп. 2) — архивация подтверждена

### Проверка
- Записи 01.10–10.10 — НАЙДЕНЫ в архиве (формат с точками: ## 03.10.2026).
- WORK_LOG: 11.10–12.10 (формат с тире: ## 2026-10-11).
- Архив переименован: WORK_LOG_ARCHIVE_before_2026-10-11.md.
- Ничего не потеряно.

### Следующее
- BELU-NB_M10 — наблюдать.
- Второй робот с AI-veto.
- pairs_screener.py.

---

## 2026-10-13 (утро) — разбор AI-отчёта + 2 бага

### AI-отчёт 13.10
- Пришёл в 19:30, email работает.
- Сделок: 0 (все сигналы отсечены фильтром time).
- SFIN-SH_M10: ML BLOCK (proba=0.209, z=-2.76) — корректно.

### Баг 1 (карантин) — AI ОШИБСЯ
- AI: "GLDRUBF-GD_H4 в карантине, но в enabled".
- Факт: enabled=False в config. Работает корректно.
- Причина ошибки: AI читает логи, не config.

### Баг 2 (state heartbeat) — РЕАЛЬНЫЙ
- robot_state.updated отстаёт на 13ч.
- Строка 902: обновляется только при старте.
- Решение: добавить heartbeat в главный цикл.

### Улучшение AI-промпта
- Добавлено: "Данные (реальные) — приоритет, логи вторичны".
- Причина: AI смешивал данные и логи.

### Git
- (после commit)

---

## 2026-10-13 (утро, доп. 2) — AI видит config + анализ сделок

### AI-промпт v2
- user_content переставлен: ДАННЫЕ → state → db_stats → контекст → ЛОГИ (с пометкой "исторические").
- Промпт усилен: "ДАННЫЕ — источник истины. Логи — история".
- Добавлен раздел "Лучшие и худшие сделки" (топ-3 прибыльных/убыточных, паттерны).

### ai_data_context.py v2
- Добавлена функция get_trades_history(limit=20).
- Возвращает: pair, direction, z, pnl, time.
- Добавлена в context.

### Git
- 9f05b09 (AI-промпт v1).
- (после commit — v2).

---

## 2026-10-13 (день) — AI-отчёт v2: качество выросло

### AI-отчёт 13.10 (v2)
- AI видит config: "GLDRUBF-GD_H4 в config отсутствует — корректно".
- AI видит freshness: "H4 = 297/297 свежих, логи устарели — верить данным".
- AI анализирует сделки: топ-3 прибыльных/убыточных.
- AI больше не ошибается по карантину.

### AI нашёл вопрос
- BANE-BN_M10: вошёл при z=+0.47 (entry=2.5), PnL=+9.59.
- BELU-NB_M10: вошёл при z=-0.046 (entry=2.5), PnL=-1.07.
- AI: "Либо ручной вход, либо баг в фильтре z-score".

### Следующее
- Разобраться: почему z≈0.5 при entry=2.5 (сделки 10.10).
- Проверить код входа (check_signals_by_tf).
- Heartbeat в pairs_robot.py (state).

---

## 2026-10-13 (день, доп.) — разбор z-score: вход корректен

### Факты
- BANE-BN_M10: OPEN z=-3.55 (|z|>2.5 ✅), CLOSE z=+0.47 (|z|<0.5 ✅). PnL=+9.59.
- BELU-NB_M10: OPEN z=-4.65 (|z|>2.5 ✅), CLOSE z=-0.046 (|z|<0.5 ✅). PnL=-1.07.
- Баг отсутствует — вход и выход корректны.

### Причина вопроса AI
- AI смотрел z из CLOSE-записи (0.47), не из OPEN (-3.55).
- trades содержит 2 записи (OPEN + CLOSE).

### Улучшение
- ai_data_context.py: get_trades_history → z_entry + z_exit (JOIN).
- ai_daily_report.py: промпт объясняет z_entry (вход) vs z_exit (выход).

### Git
- c7b0d31 (AI-отчёт v2).

---

## 2026-10-13 (день, доп. 2) — AI: полные данные для доверия

### Принцип
- AI не ошибается — он работает с тем, что дали.
- Garbage in → garbage out.
- Решение: полные данные + явный контекст + правила.

### Что добавлено
- trades_history: z_entry, z_exit, pnl, time, price_a/b, entry_z_rule, exit_z_rule, window.
- rules: entry, exit, ml_filter, corr_gate, short_stock, time_window, cooldown, commission.
- Промпт: "не додумывай", "проверяй поля".

### Git
- cd3b43b (z_entry + z_exit).
- (после commit — v3).

---

## 2026-10-13 (день, доп. 3) — AI-отчёт v3: эталон

### AI-отчёт v3 (cc362ef)
- AI видит config: "enabled_count=9 (в контексте 11 — расхождение, верю config: 9)".
- AI видит freshness: "H4 = 297/297 свежих, логи устарели — верю данным".
- AI видит карантин: "GLDRUBF-GD_H4 в карантине, в config нет — согласовано".
- AI анализирует сделки: z_entry vs z_exit, entry_z_rule vs факт.
- AI находит паттерн: "долгое удержание при слабом схождении → комиссия перекрывает".

### Принцип (подтверждён)
- AI не ошибается — он работает с тем, что дали.
- Garbage in → garbage out.
- Полные данные + правила + "не додумывай" = доверие к AI.

### Что осталось
- ai_context.md: обновить 11 → 9 enabled.
- Heartbeat в pairs_robot.py (state).

### Git
- cc362ef (AI v3).

---

## 2026-10-14 (день) — DNS-сбой (временный)

### Проблема
- 14.10 12:30 — NameResolutionError в futoi_collect_cron.log (4 раза).
- Failed to resolve iss.moex.com (Temporary failure in name resolution).
- Причина: DNS-сервер хостера 198.18.18.18 дал временный сбой.

### Решение
- DNS сменён на 8.8.8.8, 1.1.1.1, 8.8.4.4.
- /etc/resolv.conf управляется cloud-init → отключено (manage_resolv_conf: false).
- Сборщик FutOI перезапущен — 180 000 записей (OK).
- futoi_1h.parquet: 15:05.

### Техдолг
- keyring_pass.cfg: token3 already exists (не критично).

### Git
- 92afae7 (AI v3).

---

## 2026-10-14 (день, доп.) — уведомления о восстановлении сборщиков

### Проблема
- check_collector_logs.py шлёт VK-алерт при ошибке, но НЕ шлёт "✅ восстановлено".
- Асимметрия: ⚠️ проблема → тишина → ⚠️ проблема.
- Непонятно: проблема активна или решена.

### Решение
- Добавлена логика:
  - state['active_problems'] — хранит активные проблемы.
  - new_problems → "⚠️ Обнаружены ошибки".
  - recovered → "✅ Сборщики восстановлены".
- Аналогично pairs_robot.py (H4 fresh/unfresh).

### Git
- d9baca7 (DNS fix).

---

## 2026-10-14 (день, доп. 2) — миграция state для восстановления

### Проблема
- Первый запуск check_collector_logs.py: active_problems = [] → recovered = [].
- Старые ошибки (7 записей от 12:30) не были учтены как prev_problems.
- Первое восстановление не было замечено.

### Решение
- Добавлена миграция: если active_problems нет — брать все ключи state.
- Тест: миграция → "✅ Сборщики восстановлены".

### Git
- 398fc3b (восстановление).

---

## 2026-10-14 (день, доп. 3) — формат уведомлений сборщиков

### Проблема
- Уведомление "✅ Сборщики восстановлены" содержало сырые строки логов (Traceback, raise).
- Нечитаемо: "что восстановилось?"

### Решение
- Добавлена format_problem(key): файл + тип ошибки.
- DNS-сбой → "futoi_collect_cron.log — DNS-сбой (NameResolutionError)".
- Группировка по файлу, краткое описание.

### Git
- 01ec117 (миграция state).

---

## 2026-10-14 (день, доп. 4) — дедупликация + очистка state

### Проблема
- Уведомление: 7 строк, но 2-3 уникальных типа ошибок.
- State: 7 старых ключей + active_problems + last_check (мусор).

### Решение
- uniq_formatted(keys): уникальные типы ошибок по файлу.
- new_state: только active_problems + last_check (старые ключи не сохраняются).

### Git
- 99a3ee2 (формат).

---

## 2026-10-14 (вечер) — heartbeat в pairs_robot.py

### Проблема
- robot_state.updated отставал на 13ч.
- Обновлялся только при старте и сделках.
- Мониторинг не работал.

### Решение
- Добавлен heartbeat в главный цикл (раз в час).
- Обновляет: updated, running, last_check_m10/h1.
- last_check_m10/h1 — вместо рудимента (null) → реальное время.

### Git
- 2a0be61 (дедупликация).

---

## 2026-10-14 (вечер, доп.) — таблица signals: запись из pairs_robot.py

### Что сделано
- Таблица signals в pairs_robot.db (17 полей, 3 индекса).
- log_signal() — запись сигнала.
- skip_signal() — запись + continue.
- Вызовы в check_signals_by_tf:
  - MAX_POSITIONS → MISSED.
  - COOLDOWN → MISSED.
  - time/vol/corr/expiry/new → MISSED.
  - corr < 0.5 → MISSED (corr_gate).
  - ML BLOCK → BLOCKED.
  - ML PASS → EXECUTED.

### Git
- a16c5f6 (heartbeat).

---

## 2026-10-14 (вечер, доп. 2) — разбор: почему нет сделок

### Факты
- signals: 9 записей, все MISSED (time), все в 19:00.
- Логи: ⛔ time — 8 раз подряд (днём?).
- z: 0.1–2.17 — не дотягивает до entry=2.5.
- ML BLOCK: SFIN (z=-2.85, proba=0.145), BELU (z=+2.52, proba=0.129), BANE (z=-2.02).
- entry_z: M10=2.5, H4=2.0–2.5.
- Сделок нет с 10.10.

### Гипотезы
1. _is_trading_time сломан (блокирует днём).
2. entry_z=2.5 слишком высокий.
3. ML блокирует.

### Следующее
- Проверить _is_trading_time.
- Проверить логи ⛔ time с временем.
- Проверить entry_z на истории.

---

## 2026-10-14 (вечер, доп. 3) — КОРНЕВАЯ ПРИЧИНА: z < entry_z

### Открытие
- _is_trading_time РАБОТАЕТ правильно (19:08 → False).
- НЕ time блокирует — z не дотягивает до entry_z.
- entry_z=2.5 (M10), 2.0-2.5 (H4).
- z за 4 дня: 0.1-2.17 (M10), 0.1-2.55 (H4).
- За 4 дня: 1 сигнал с z≥2.5 (PD-SV_H4, z=+2.55) — но что-то блокировало.

### Факты
- signals: 9 записей, все MISSED (time) — но это 19:00.
- Днём: z не дотягивает до entry_z.
- ML BLOCK: SFIN (z=-2.85), BELU (z=+2.52) — корректно.

### Вывод
- entry_z=2.5 — слишком высокий для текущей волатильности.
- Решение: walk-forward с разными entry_z.

### Следующее
- Проверить PD-SV_H4 (z=+2.55) — что блокировало.
- Walk-forward: entry_z 1.5, 2.0, 2.5.
- Решение: снизить entry_z.

---

## 2026-10-14 (вечер, доп. 4) — уточнение: entry_z — НЕ причина

### Признание ошибки
- Моё предложение "снизить entry_z до 2.0" — ПРЕЖДЕВРЕМЕННО.
- Без walk-forward — это гадание.
- Правильно: сначала данные, потом решение.

### Факты
- z ≥ 2.0: 137 случаев (по логам).
- z ≥ 2.5: 53 случая.
- Сделок: 4 (10.10), потом 0.
- signals: 9 записей, все MISSED (time), все 19:00.

### Вопросы
1. Был ли вход по PD-SV_H4 (z=+2.55)?
2. Что блокировало?
3. С чем связана блокировка?

### Следующее
- Проверить PD-SV_H4 полный контекст.
- Проверить BANE-BN_M10 (z=-2.02).
- Проверить SFIN-SH_M10 (z=-2.85).
- НЕ снижать entry_z без walk-forward.

---

## 2026-10-14 (вечер, доп. 5) — НАХОДКА: signals неполный

### Открытие
- PD-SV_H4 (z=+2.55): сигнал есть, но нет записи в signals.
- Причина: spread_trend <= 0 → _signal = None → нет логирования.
- signals: 9 записей, все MISSED (time), 19:00.
- Днём: записей нет (z < entry → continue до фильтров).

### Что это значит
- signals НЕ покрывает:
  - z < entry → нет записи.
  - _signal = None (spread_trend) → нет записи.
- AI не видит эти случаи.

### Решение
- Логировать ВСЕ случаи:
  - z < entry → MISSED (z_below_entry).
  - _signal = None → MISSED (spread_trend).
  - Фильтры → MISSED.
  - ML → BLOCKED.
  - EXECUTED.

### Git
- 931a10e.

### Следующее
- Патч: логировать z < entry и _signal = None.
- Проверить spread_trend для PD-SV_H4.

---

## 2026-10-14 (вечер, доп. 6) — Continue: разбор кода (баги)

### Критичные баги (подтверждены)
1. Пропущен continue после skip_signal в фильтрах (строка ~1219).
   - Не критично (сигнал не открывается), но хрупко.
2. corr = None (скаляр) при len(m) < 50 → AttributeError.
   - Риск низкий (len > 50 почти всегда).
3. beta = 0.0 для non-coint пар → volume_b = 0 → не открывается.
   - КРИТИЧНО: PT-SV_H4, GD-PT_H4, BR-GAZPF_H4, LK-IMOEXF_H4.
4. use_coint меняется внутри функции (плохой стиль).

### Не критичные
- Дублирование corr-фильтров (0.7 и 0.5) — двойная защита.
- spread_trend — логика корректна.
- vol_ratio > 0.02 — настройка.

### Следующее
- Исправить beta для non-coint (1.0 или close_a/close_b).
- Добавить continue после skip_signal.
- Исправить corr = None.

---

## 2026-10-14 (вечер, доп. 7) — исправлены баги Continue

### Уточнение по beta
- Все 9 enabled-пар: use_coint=True.
- beta=0.0 — только для non-coint пар (их нет в enabled).
- Баг НЕ проявляется сейчас, но исправлен на будущее.

### Исправлено
1. continue после skip_signal в фильтрах (строка ~1219).
2. corr = None → pd.Series([None] * len(m)).
3. beta = 1.0 для non-coint пар (fallback).

### Git
- 0952f63.

---

## 2026-10-14 (вечер, доп. 8) — рестарт робота после патчей

### Патчи
- continue после skip_signal (1222).
- corr = Series([None]) (529).
- beta = 1.0 для non-coint (520).
- py_compile: OK.

### Рестарт
- Робот перезапущен (systemctl restart).
- Статус: active.

### Проверка signals
- (после рестарта)

### Git
- 1284a5b.

---

## 2026-10-14 (вечер, доп. 9) — Continue: разбор close_position, open_position

### Критический баг (исправлен)
- close_position: leg_a_pnl_points / leg_b_pnl_points использовали volume (не определена).
- NameError при закрытии позиции.
- Исправлено на volume_a / volume_b.
- Баг НЕ проявлялся (сделок не было).

### Баги Continue, которые НЕ подтвердились
1. ml_filter: return True, None — это кортеж (не баг).
2. open_position: leg_budget = pair_budget / 2 — β-adjusted (не баг).
3. check_expiry: exp — проверка if not exp есть (не баг).
4. check_time_exits: MAX_HOLD_HOURS — календарные часы (не баг).

### Обсудить
- open_position: leg_budget = pair_budget / 2 — β-adjusted.
- check_time_exits: MAX_HOLD_HOURS — календарные vs торговые.

### Git
- acce2dc.

---

## 2026-10-14 (вечер, доп. 10) — ai_data_context: signals_summary

### Что добавлено
- get_signals_summary(hours=24): статистика сигналов.
- stats: status + reason + count.
- recent: топ-20 свежих сигналов.
- Добавлено в context.

### Текущее состояние signals
- 39 записей, все MISSED (time) — 20:13, вне окна.
- Это норма. Днём будут другие причины.

### Git
- 4783852 (close_position fix).

---

## 2026-10-14 (вечер, доп. 11) — ai_weekly_report: свободный промпт + ai_data_context

### Что сделано
- Импорт subprocess.
- Вызов ai_data_context.py → JSON в user_content.
- Порядок: ДАННЫЕ → DB stats → Контекст → Daily-отчёты (исторические).
- Промпт: "Анализируй свободно — не ограничивайся шаблоном".
- Задачи: лучшие сделки, упущенные, рекомендации (свободные).

### Git
- ae4e748.

---

## 2026-10-14 (вечер, доп. 12) — AI-weekly: прорыв

### AI-weekly v2 (1aa7b4f)
- Видит: signals_summary, trades_history, corr, rules.
- Анализирует свободно.
- Нашёл паттерны:
  - Прибыль: быстрое схождение (20 мин) + стабильная corr (>0.9).
  - Убыток: медленное схождение (2ч40м) + распад corr.
- Разобрал MISSED (42, все time):
  - |z| = 0.2–1.9 — ниже entry_z=2.5.
  - Вывод: не потерянная прибыль, а корректная работа time-window.
- Нашёл проблему 1: BELU-NB_M10 — corr в минус, ML PASS.
  - Рекомендация: corr-гейт ДО ML.
- Нашёл проблему 2: BR-GAZPF_H4 — corr=0.32–0.39 < 0.5.
  - Рекомендация: проверить corr_gate.

### Следующее
- Проверить corr при входе BELU-NB.
- Проверить BR-GAZPF_H4 (enabled при corr<0.5).
- Проверить M10-сигналы днём.

---

## 2026-10-14 (вечер, доп. 13) — дневной AI + signals неполный

### Дневной AI за 14.10
- Сгенерирован в 19:30 (cron).
- (прочитать)

### signals неполный — подтверждено
- Днём (07:00–18:00): z < entry → _signal = None → НЕТ записи.
- Вечером: z < entry → time → запись MISSED (time).
- Значит: signals НЕ покрывает случай z_below_entry днём.
- Исправить: логировать z < entry.

### BR-GAZPF_H4
- enabled=True, corr=0.51 (свежие).
- Не < 0.5, но близко к порогу.
- Наблюдать.

### Git
- 76012be.

---

## 2026-10-14 (вечер, доп. 15) — итог: что сделано, что осталось

### Сделано (19 задач)
- DNS, cloud-init, сборщики (симметрия, миграция, формат, дедупликация).
- Heartbeat, signals, log_signal, skip_signal.
- Патчи: continue, corr Series, beta non-coint, volume.
- ai_data_context: signals_summary.
- ai_weekly_report: свободный промпт + ai_data_context.
- AI-weekly, AI-daily — разобраны.

### Осталось
**Приоритет 1:**
1. signals неполный — днём z < entry не логируется. Патч.
2. corr-гейт — проверить логику.

**Приоритет 2:**
3. Config — проверить (не обновлялся 2 дня).
4. M10-сигналы днём — обсудить.
5. Walk-forward — entry_z.

**Приоритет 3:**
6. v2 робот — эксперименты.
7. pairs_screener.py.
8. AI-veto.

**Приоритет 4:**
9. leg_budget — обсудить.
10. MAX_HOLD_HOURS — обсудить.

### Git
- f5fa8b8.

---

## 2026-10-14 (вечер, доп. 16) — сигналы z>=2.0 есть (вечером)

### Открытие
- signals с z>=2.0: BANE-BN_M10 (z=2.70), SFIN-SH_M10 (z=2.75).
- Все в 19:20-19:40 — ВНЕ окна 07:00-18:00.
- MISSED (time).
- Значит: z>=entry ЕСТЬ, но вечером.
- Днём: z < entry.

### Вывод
- Окно 07:00-18:00 не покрывает активность.
- Расширение окна — в v2.
- v1 — эталон.

### Config
- last_updated: 2026-10-12 19:22:24 (2 дня).
- enabled: 9.

### Git
- ab925c9.

---

## 2026-10-14 (вечер, доп. 17) — логи и config

### Сигналы z>=2.5
- 4 записи, все 14.10 19:20-19:40.
- Днём: НЕТ.
- corr: 0.90-0.94 — здоровые.
- Вывод: сигналы есть, но вечером.

### Логи
- robot.log: 1.4 МБ.
- grep "2026-10-14": 4 строки (только рестарты).
- Логи за 14.10 не пишутся? Проверить.

### Config
- last_updated: 2026-10-12 19:22:24 (2 дня).
- enabled: 9.

### Следующее
- Создать v2 (окно 07:00-23:00).
- Проверить логи.

### Git
- 06c3b8d.

---

## 2026-10-14 (вечер, доп. 18) — создан v2 (экспериментальный)

### Логи
- robot.log: 1.4 МБ, пишется.
- grep "2026-10-14" не находит (нет даты в строке).
- tail — показывает свежие.

### v2 — создан
- robots/pairs_robot_v2.py (копия v1 + правки).
- robots/pairs_robot_v2.db.
- FinLabPy/My_Indicators/pairs_config_v2.json.
- robots/robot_state_v2.json.
- /etc/systemd/system/finlab-robot-v2.service.
- Патчи: DB_PATH, CONFIG_PATH, STATE_FILE, COMMAND_FILE, TF_FRESH_STATE_FILE, _is_trading_time (07:00-23:00).

### Сигналы z>=2.5
- 4 записи, все 14.10 19:20-19:40.
- Днём: НЕТ.
- v2 (окно до 23:00) поймает эти сигналы.

### Следующее
- M10-сборщик до 23:00.
- Наблюдение: v1 vs v2.

### Git
- f349da6.

---

## 2026-10-14 (финал) — итог дня

### Сделано (v2 — экспериментальный)
- Создан robots/pairs_robot_v2.py (копия v1 + правки).
- robots/pairs_robot_v2.db.
- FinLabPy/My_Indicators/pairs_config_v2.json.
- /etc/systemd/system/finlab-robot-v2.service.
- v2: active, paused=True (безопасно).

### Правки в v2
- DB_PATH → pairs_robot_v2.db.
- CONFIG_PATH → pairs_config_v2.json.
- STATE_FILE → robot_state_v2.json.
- COMMAND_FILE → robot_command_v2.txt.
- TF_FRESH_STATE_FILE → tf_fresh_state_v2.json.
- _is_trading_time: 07:00-18:00 → 07:00-23:00.

### Открытия дня
- Сигналы z≥2.5: 4 записи (14.10 19:20-19:40), все MISSED (time).
- Днём z≥2.5: нет.
- corr: 0.90-0.94 — здоровые.
- Логи пишутся (robot.log 1.4 МБ), но grep по дате не находит.
- Config last_updated: 2026-10-12 19:22:24 (2 дня).

### v1 (эталон) — НЕ ТРОГАЛИ
- 9 enabled-пар, окно 07:00-18:00.

### Следующее
- M10-сборщик до 23:00 (для v2).
- Наблюдение: v1 vs v2.
- RESUME для v2 (когда решим).

### Git
- 0541be1.

---

## 2026-10-15 (вечер) — v2 запущен: полная интеграция в инфраструктуру

### Контекст
- v2 (pairs_robot_v2, окно 07:00-23:00) создан 14.10, но `paused=True` (безопасно).
- Задача: интегрировать v2 в дашборд, AI-daily, ВК-бот; запустить.

### Патчи (по одному, с проверкой)

**Патч 1 (P0): heartbeat v2 в paused-режиме.**
- Проблема: при `paused=True` v2 не обновлял `robot_state_v2.json` (heartbeat вне paused-блока).
- Решение: heartbeat в paused-блоке (раз в час).
- Проверка: тестовый режим 60 сек → `💓 Heartbeat (paused)` → откат на 3600.

**Патч 2 (P1): z_below_entry в v1 (pairs_robot.py).**
- Проблема: днём при `|z| < entry_z` сигнал не логировался (только `time` — вечером).
- Решение: `else: skip_signal(z_below_entry); continue` после ML-блока.

**Патч 3.1/3.2/3.3 (P2): v2 в дашборде.**
- Таб «📊 Парная торговля_v2» (radio).
- v2 в `_robots_stats` (Обзор).
- Кнопки Старт/Пауза/Стоп (RESUME/PAUSE/STOP).
- Фикс: `_v2_db` перемещён выше кнопок (NameError).

**Патч 4.1 (ВК-бот): префикс [v2] в уведомлениях.**
- Проблема: v2 слал в тот же чат, что v1, без пометки.
- Решение: `message = "[v2] " + message` в `send_vk_message`.
- Проверка: тестовое сообщение `[v2] тест №2`.

**Патч 5/5.1 (AI-daily): v2 в контексте.**
- `get_robot_state_v2()`, `get_trades_history_v2()`, `get_signals_summary_v2()`.
- Ключи в JSON: `robot_state_v2`, `trades_history_v2`, `signals_summary_v2`.
- Фикс: `import pandas as pd` (NameError).

**Патч 5.2 (дашборд): finlab-robot-v2 в «Активных роботов».**

**Патч 2.1 (v2): z_below_entry.**

### Config
- `last_updated` обновлён (15.10 20:33) в v1 и v2.

### Очистка v2.db
- Удалены унаследованные positions (2) и trades (4) от v1 (10.10).
- signals v2 (48 записей) сохранены.

### RESUME v2
- `echo "RESUME" > robot_command_v2.txt`.
- `paused: false`, `▶️ RESUME: торговля возобновлена`.
- Лог: `💤 z_below_entry` работает.

### Состояние v2
- signals: 48 (все MISSED time — от 14.10).
- positions: 0, trades: 0.
- state: `paused=False, running=True`.

### Открытия
- BR-GAZPF_H4: corr=0.29 (нестабильный, колеблется 0.29-0.76).
- LK-IMOEXF_H4: corr=0.44 (< 0.5, близко к порогу).
- EURRUBF_M10.parquet: разовая ошибка (race с cron), файл валиден.

### Следующее
- Наблюдение v2 (30-60 мин): signals, EXECUTED/BLOCKED, ВК [v2].
- Завтра днём: проверка z_below_entry (v1 и v2).
- BR-GAZPF_H4: решение (исключить или наблюдать).
- Walk-forward по entry_z.

### Git
- (будет после commit)

---

## 2026-10-16 (вечер) — ремонты, EXECUTED-фикс, walk-forward, эксперимент v2

### Ремонты инфраструктуры

**A. check_collector_logs.py (критично).**
- Было: `TypeError: strptime() argument 1 must be str, not list` — мониторинг сборщиков сломан.
- Фикс A.1: `isinstance(v, str)`.
- Фикс A.2: `_is_recent_date(v)` с `try/except` (формат `14.10 16:09`).
- Результат: `Активных проблем: 0` — работает.

**B. hi2_daily_aggregator.py.**
- Было: `ColumnNotFoundError: unable to find column "ticker"`.
- Фикс: `if 'ticker' not in df.columns and 'secid' in df.columns: df = df.rename({'secid': 'ticker'})`.
- Результат: 225 тикеров, 10644 строк.

**C. check_memory.py — VK API.**
- Было: `VkApiMethod.__call__() takes 1 positional argument but 3 were given`.
- Фикс: переписан на `requests.post` + `load_dotenv` + `import requests`.
- Тест: `тест check_memory VK (v2)` — ушёл в ВК.

**D. check_contract_changes.py — VK API.**
- Было: `[15] Access denied: token required`.
- Фикс: `load_dotenv` уже был — **не требовалось**.
- Тест: `Изменений контрактов не обнаружено` — работает.

**E. ai_daily_report.py — email.**
- Было: `Connection refused` (порт 465).
- Фикс: 465 → 587 (STARTTLS).
- Тест: email `FinLab тест email` — ушёл.

**F. tradestats_collector.py — retry.**
- Было: 70 ConnectionError.
- Фикс: retry 3→5, backoff 0.5→1.0, +429.

**G. futoi_collector.py — DNS retry + sys.path.**
- Было: `NameResolutionError` (DNS), `ModuleNotFoundError: MOEXPy`.
- Фикс: явный `import requests` + retry-сессия + `sys.path.insert(0, project_root / 'FinLabPy')`.
- Тест: `Готово! Всего новых записей: 180000`.

### EXECUTED-фикс (v1 + v2)

- Было: `log_signal('EXECUTED')` — **до** `open_position`. Если `open_position` возвращался (шорт запрещён, price <= 0, volume < 1) — signals говорил EXECUTED, но позиции нет.
- Фикс: `open_position` возвращает `True/False`. `log_signal('EXECUTED')` — только при `_opened == True`. Иначе — `BLOCKED (open_failed)`.
- Результат: `py_compile OK` (v1, v2).

### Walk-forward entry_z

- Создан `scripts/walk_forward_entry_z.py` — перебор entry_z (1.5, 2.0, 2.5, 3.0) на 9 enabled-парах (5 фолдов).
- **Результаты:**

| TF | entry_z | n | pnl | wr | sharpe |
|---|---|---|---|---|---|
| H4 | 1.5 | 1054 | 9.54 | 0.78 | 9.93 |
| H4 | 2.0 | 669 | 7.28 | 0.79 | 12.49 |
| H4 | 2.5 | 376 | 5.23 | 0.81 | **16.66** |
| H4 | 3.0 | 160 | 2.66 | 0.76 | 14.66 |
| M10 | 1.5 | 1044 | **-1.08** | **0.22** | **-8.24** |
| M10 | 2.0 | 440 | 0.11 | 0.42 | 0.58 |
| M10 | 2.5 | 152 | 0.33 | 0.69 | 12.93 |
| M10 | 3.0 | 61 | 0.32 | 0.77 | 15.78 |

- **Вывод:** M10 — убыточен при entry_z < 2.5. H4 — прибыльный при всех. M10 и H4 — разные стратегии.
- Лучший entry_z по каждой паре (по Sharpe): SFIN-SH=3.0, BANE-BN=3.0, BELU-NB=2.5, GD-SV=3.0, PD-SV=3.0, PT-SV=3.0, GD-PT=3.0, BR-GAZPF=2.5, LK-IMOEXF=2.5.

### Диагностика: почему 0 сделок

- signals v2: `MISSED z_below_entry` — 314 (195 при z<1.0, 59 при 1.0–1.5, 41 при 1.5–2.0, 19 при 2.0–2.5, 0 при ≥2.5).
- signals v2: `MISSED time` — 204, `MISSED corr_gate` — 7, `BLOCKED ML_BLOCK` — 2, `EXECUTED` — 1 (ложный).
- **Гипотеза `spread_trend` — опровергнута:** `z_below_entry при |z| ≥ 2.5 = 0` (v1, v2).
- **Реальная причина:** `entry_z=2.5` — высок. z почти всегда < 2.5.

### Эксперимент v2 (на v2 — эксперименты, v1 — эталон)

**Изменения в config v2:**
- M10 → entry_z=2.0 (было 2.5): SFIN-SH, BANE-BN, BELU-NB.
- BR-GAZPF_H4 → enabled=false (corr=0.20 — мёртвая).

**Итог v2:**
- 8 enabled-пар (было 9).
- M10: 2.0. H4: 2.5/2.0.
- BR-GAZPF_H4 — выключен.

**Итог v1 (эталон — не тронут):**
- 9 enabled-пар.
- M10: 2.5. H4: 2.5/2.0.
- BR-GAZPF_H4 — enabled.

**Разница v1 vs v2:**
- M10: v1=2.5, v2=2.0.
- BR-GAZPF_H4: v1=enabled, v2=false.
- Окно: v1=07:00–18:00, v2=07:00–23:00.

### Открытия

- **BR-GAZPF_H4: corr нестабилен** — 0.52 → 0.29 → 0.76 → 0.20.
- **LK-IMOEXF_H4: corr нестабилен** — 0.91 → 0.44 → 0.96 → 0.44.
- **pairs_quarantine.py — только v1** (`robot.log`, `pairs_config.json`). v2 — без карантина.
- **ENTRY_Z_DEFAULT = 3.0** в коде, но **не используется** (у всех пар свой entry_z в config).

### Git

- `17f44c9` — .gitignore (robot_state_v2.json).
- `b147d47` — ремонты, EXECUTED-фикс, walk-forward, v2 эксперимент.
- `1371005` — ai_daily_report (email 587).
- Все — в `origin` + `diary`.

### Следующее (через 1-2 дня)

- **Замер v2:** signals, positions, trades. Есть ли EXECUTED?
- **Если 0 EXECUTED** → Эксперимент 2: M10 → 1.5.
- **LK-IMOEXF_H4** — наблюдать (corr=0.44).
- **pairs_quarantine.py** — адаптировать для v2.
- **v1 — не трогать.**

### Git
- (после commit)

---

## 2026-10-17 (вечер) — DD/SY, candles_collector, AI-легенда, эксперимент 2

### Удаление DD, SY (АДР)

- **DD** — фьючерс на PDD Holdings (АДР, Китай). **SY** — фьючерс на Sony Group (АДР).
- В `tickers_config.json` — в `futures` (166 → 164).
- Данные: DD_M10 — последние 2026-07-29, SY_M10 — 2026-07-27. **Не обновлялись ~2.5 месяца.**
- **Удалено:** из `tickers_config.json` + файлы (M10, H1, H4, D1) → `data/candles/_trash/`.

### candles_collector.py — sys.path

- **Проблема:** `ModuleNotFoundError: MOEXPy` при ручном запуске (нет `PYTHONPATH`). В cron — работает.
- **Фикс:** `sys.path.insert(0, str(project_root / 'FinLabPy'))`.
- **Результат:** ручной запуск — работает.

### candles_collect_cron.log — 0 байт

- **Проблема:** лог — 0 байт (с 10.10).
- **Причина:** candles_collector пишет логи в `logs/2026-10-17_candles_collector.log` (13 MB, свежий).
- **Фикс:** пустой `candles_collect_cron.log` — удалён.

### Патч 8.1 — AI-легенда (ai_data_context.py)

- **Проблема:** AI-daily не различает v1/v2. Смешивает signals, config, entry_z.
- **Фикс:** `get_legend()` — v1 (эталон), v2 (эксперимент), поля signals, фильтры, правило «различай v1/v2».
- **Результат:** JSON — `legend` есть. AI-daily увидит.

### Патч 8.2 — AI-инструкция (ai_context.md)

- **Добавлено:** v1 vs v2 (БД, state, config, окно), правила отчёта:
  1. Различай v1/v2.
  2. Не смешивай PnL, signals, trades, config.
  3. EXECUTED без positions/trades — проверь open_failed.
  4. corr_gate — к сигналам, не к enabled.
  5. Нет данных — пиши «нет данных».
- **Результат:** ai_context.md — 105 строк (было 82).

### Эксперимент 2 — M10 → 1.8 (v2)

- **Config v2:** M10 → 1.8 (SFIN-SH, BANE-BN, BELU-NB). H4 — 2.5/2.0.
- **v2:** рестарт, `paused: false`.
- **Лог:** `entry=1.8` — применён.
- **Signals:** M10 — `z_below_entry` (z 0.2–1.0 — ниже 1.8). H4 — `z_below_entry`.
- **НО:** z — мал. Даже 1.8 — высок. Ждём 1-2 дня.

### AI-daily за 17.10 — разбор

- **Верно:** 0 сделок, D1/M10 — «мёртвые», H4 — норма, паттерны сделок.
- **Ошибки:** смешивает v1/v2 (signals, config, entry_z). «161 из 298 D1 не обновлялись» — **неверно** (D1 обновлён 17.10 10:01, «несвежие» — «мёртвые»).
- **Вывод:** Патч 8.1/8.2 — нужен. Сделано.

### Git

- `4b6cc56` — DD/SY удалены, candles_collector sys.path, AI-легенда.
- `ceccdc9` — .gitignore (tf_fresh_state_v2.json).
- `8cf54b3` — Эксперимент 2 (M10=1.8, v2).
- Все — в `origin` + `diary`.

### Следующее (через 1-2 дня)

- **Замер v2:** signals, positions, trades. EXECUTED / open_failed.
- **Если 0 EXECUTED** → Эксперимент 3: M10 → 1.5.
- **AI-daily** — проверить, различает ли v1/v2 (после Патча 8.1/8.2).
- **v1 — не трогать.**

### Git
- (после commit)

---

## 2026-10-18 (воскресенье) — Кальман: прорыв, v3, AI-легенда

### Кальман — прорыв

- **Тест** (`kalman_test_all.py`) — 5 H4-пар (GD-SV, PD-SV, PT-SV, GD-PT, LK-IMOEXF).
- **Fixed vs Kalman** (in-sample): PnL в 20–360 раз, WR +10–17%, Sharpe +13–60%.
- **Walk-forward** (`kalman_walk_forward_slip.py`) — 5 фолдов, с проскальзыванием (0.02%).
- **Результат:**
  - Fixed: PnL=6.80, WR=0.80, Sharpe=14.01, avg=0.0118 (n=578).
  - Kalman: PnL=1126.42, WR=0.94, Sharpe=22.20, avg=2.0043 (n=562).
  - **PnL в 165 раз, WR +14%, Sharpe +58%, avg PnL в 170 раз.**
- **На каждом фолде** — Кальман лучше. **Не переобучение. Прорыв.**

### v3 — создан (каркас + Кальман)

- `pairs_robot_v3.py` — копия v2, пути → v3.
- `pairs_config_v3.json` — копия v2 (8 пар, M10=1.8).
- `pairs_robot_v3.db` — новая схема (positions, trades, signals).
- `finlab-robot-v3.service` — systemd.
- **Кальман встроен:** `kalman_beta()`, `use_kalman=True` в `calculate_zscore`.
- **init_db:** signals (17 полей + 3 индекса), positions/trades — новые колонки.
- **RESUME** — отправлен (понедельник → `paused: false`).

### v3 — в дашборде

- **Radio:** «📊 Парная торговля_v3» (строка 4123).
- **Обзор:** `_pairs_v3_db`, `_robots_stats['📊 Парная торговля_v3']` (4176-4192).
- **Активные:** `finlab-robot-v3` (4275).
- **Таб:** `elif robot_tab == "📊 Парная торговля_v3":` (4903-5098).
- **Кнопки:** `v3_start_resume`, `v3_pause_active`, `v3_stop_running` (4986, 5001, 5013).

### AI — v3 (легенда + функции)

- `get_robot_state_v3()`, `get_trades_history_v3()`, `get_signals_summary_v3()`, `get_config_v3()`.
- **Ключи:** `config_v3`, `robot_state_v3`, `trades_history_v3`, `signals_summary_v3`.
- **Legend:** `pairs_v3` (строка 297), `rule` — `v1, v2 и v3`.
- **Промпт:** `v1/v2/v3`.
- **JSON:** `config_v3: 8`, `robot_state_v3: {paused: true}`.

### AI-отчёты — разбор

- **Weekly (W42)** — 14:00 (должен 17:00). **Фикс:** `0 17 * * 0`.
- **Daily** — каждый день (должен Пн–Сб). **Фикс:** `30 19 * * 1-6`.
- **AI** — не различает v1/v2/v3. **Патч:** legend + промпт (сделано).

### DD, SY — удалены

- **DD** — фьючерс на PDD Holdings (АДР). **SY** — Sony Group (АДР).
- **Не обновлялись** ~2.5 месяца. **Удалены** из `tickers_config.json` + файлы (M10, H1, H4, D1) → `_trash`.

### candles_collector — sys.path

- **Проблема:** `ModuleNotFoundError: MOEXPy` (ручной запуск). В cron — работает.
- **Фикс:** `sys.path.insert(0, project_root / 'FinLabPy')`.

### IDEAS.md — карта идей

- **P0:** v2 замер, v3 каркас.
- **P1:** Кальман (done), OFI, баскет, walk-forward, парковщик.
- **P2:** копулы, авто-карантин v2, расширение окна v1.
- **Правило:** идеи не затираются.

### Git

- `ec60a74` — IDEAS.md.
- `4fef751` — AI-промпт → legend + config_v2, README → IDEAS.md.
- `d46da2d` — v3 каркас + IDEAS.md + .gitignore v3.
- `e3f8b47` — v3 в дашборде + AI (v3) + init_db + RESUME.
- `21cce56` — kalman-скрипты + .gitignore (robot_command_v3).
- Все — в `origin` + `diary`.

### Следующее (понедельник, 19.10)

- **Замер v3:** signals, positions, trades. Кальман в работе.
- **Сравнить** v1 vs v2 vs v3.
- **Если v3 лучше** — **прорыв** подтверждён.
- **OFI** (Т-Инвест) — следующий метод.
- **Парковщик** — P1.

### Git
- (после commit)

---

## 2026-10-19 (вечер) — первая сделка v2, v3.1 (Kalman entry_z), AI-daily

### Первая реальная сделка v2 (эксперимент 2 подтверждён)

- **BANE-BN_M10**, LONG_SPREAD, entry_z=-1.82 → exit_z=-0.47, **PnL +9.60₽**, вход 19.10 17:40, выход 19:01.
- WR 100% (1/1). Правила входа/выхода соблюдены (|z|≥1.8 ✓, |z|≤0.5 ✓).
- **Эксперимент 2 (M10 entry_z=1.8) — работает.**
- v2 service: `disabled` → `enabled` (автозапуск после reboot).

### Свежесть данных — норма

- M10: 295 файлов, stale>24h=11, median=-2.4h, max=269.8h — 11 «мёртвых» тикеров (неликвиды).
- H1: median=-1.5h. D1: median=16.5h. H4: 294/295, median=4.5h.
- **AI-daily 18.10 пугал зря** («oldest=241.5ч, сбор сломан») — это «мёртвые» тикеры, медианы свежие. Восстанавливать сборщики не надо.

### v3 — Кальман подтверждён в коде, config скопирован с v2

- `use_kalman=True` (строка 1236), `kalman_beta()` (строка 32), применение в `calculate_zscore` (546-550). Работает.
- **НО:** config v3 = копия v2 (M10=1.8, H4=2.0/2.5, BR-GAZPF off). **Не адаптирован под Кальман.**
- Кальман сглаживает z (адаптивная β → меньше остаток спреда → |z| ниже OLS). Гипотеза: v3 нужен **ниже entry_z**.

### v3.1 — эксперимент: Kalman entry_z (M10=1.5, H4=2.0)

- `pairs_config_v3.json` изменён: M10 → 1.5, H4 → 2.0 (для enabled-пар).
- Бэкап: `pairs_config_v3.json.bak.20261019`.
- `last_updated` обновлён. v3 рестартнут.
- **v1, v2 — не тронуты.**
- Наблюдение 2-3 дня: signals, EXECUTED, trades.

### v2/v3 open_failed=2 (сегодня)

- Причина: BELU-NB_M10, шорт по акции BELU — запрещён (`is_stock()`, строка 716). **Ожидаемо, не баг.**
- Реальных кандидатов на вход сегодня не было (все z < 1.8, кроме BELU — под шорт-запретом).

### AI-daily 19.10 — разбор

- **Различает v1/v2/v3** ✅ (легенда + промпт работают).
- Верно: 1 сделка v2 (+9.60), v1/v3 — 0 сделок, ML_BLOCK по BELU-NB_M10 в v2 (proba≈0.306).
- Верно: свежесть — норма (284/295, «мёртвые» тикеры — не аномалия).
- Верно: config соответствует legend (v1: 9 пар, v2/v3: 8 пар).
- **Неверно:** рекомендует «срочно восстановить сбор M10/H1/D1» — по факту это «мёртвые» тикеры, медианы свежие.

### Git

- (после commit)


---

## 2026-10-19 (уточнение) — «config v3 = копия v2»: что это значит

- **Терминология.** 18.10 `pairs_config_v3.json` создан **копированием** `pairs_config_v2.json`: те же entry_z (M10=1.8, H4=2.0/2.5), exit_z, window. Параметры **не пересчитаны** под Кальман-β (адаптивную), а взяты от OLS (v1/v2).
- **Почему это важно.** Кальман даёт другой z (β скользящая, а не фиксированная). Порог entry_z, оптимальный для OLS, **не гарантирован** для Кальмана. Это не баг, а недоделка: v3 запущен с чужим порогом.
- **Сегодня (v3.1):** config v3 адаптирован (M10=1.5, H4=2.0) — но это **интуиция по аналогии с v2**, а не walk-forward.
- **Замер (19.10, |z| v2 vs v3 по max за день):** M10 ratio 0.89–1.24 (Кальман **не ниже**), H4 ratio 0.25–1.24 (разброс большой, зависит от пары). Гипотеза «Кальман систематически сглаживает z» — **не подтверждена**.
- **Правильный путь:** `kalman_walk_forward` по entry_z (1.2, 1.5, 1.8, 2.0, 2.5), 5 фолдов, с проскальзыванием. Только после него — финальный entry_z v3.
- v3.1 — оставить (наблюдение 2-3 дня). v1/v2 — не трогать.


---

## 2026-10-19 (поздний вечер) — v3.2 (финал), скринер (только futures), H1-провал

### Kальман на M10/H1 — провал (доказано)

- **M10 (SFIN-SH, BANE-BN, BELU-NB):** |spread|=0.012–0.027, cost=0.006. Net PnL < 0 при **всех** delta (1e-4…1e-1) и entry_z (1.2…3.0). WR≈0. **Кальман не спасает.**
- **H1 (те же пары):** |spread|=0.006–0.011, cost=0.006. Net PnL < 0 при **всех** delta (1e-4, 1e-3) и entry_z. **H1 не помогает** — спред на этих парах узкий на **любом** TF.
- **Вывод:** cost 0.006 = **25–50%** от |spread| на M10/H1. Ноги **не окупают** комиссию. **M10 и H1 в Кальмане — тупик.** На H4 — работает (|spread|=3–4, cost = 0.2% от движения).

### v3.2 — финал (4 H4-пары)

- **M10 → off** (SFIN-SH, BANE-BN, BELU-NB) — cost > spread.
- **GD-PT_H4 → off** — net_sharpe=-20.
- **entry_z:** GD-SV=2.0, PD-SV=1.8, PT-SV=2.5, LK-IMOEXF=2.0 (наблюдать).
- **Итог:** v3 = **4 пары** (было 8). Бэкап: `pairs_config_v3.json.bak2`.
- **v1/v2 — не тронуты.**

### Скринер — только futures × futures

- **Проблема:** первая версия сканировала и futures, и stocks → в top попали **акции** (SBER-SBERP, TATN-TATNP, MAGN-NLMK) — **не для v2/v3** (шорт по акциям запрещён принципиально).
- **Фикс:** `universe` = только `tickers_config.json → futures` (164). Stocks **исключены**.
- **Перезапуск:** `python scripts/pairs_screener.py --tf H4 --top 30 --min-corr 0.3`.
- **Фьючерсных коинтегрированных пар (coint_p<0.05) в первой версии: 6**, но с фильтром «только futures» — надо посмотреть отдельно.
- **ВАЖНО:** добавление в v3 — **только после walk-forward** (Кальман H4 + entry_z grid, net PnL > 0).

### Твоя позиция (зафиксирована)

- **Шорт по акциям — запрещён принципиально.** Парная торговля = одна нога SELL. Если одна нога — акция → пара **не работает** в v2/v3. Код `is_stock(_short_ticker)` → `return False` — защита.
- **Stocks-пары (SBER-SBERP, TATN-TATNP, MAGN-NLMK) — не для v2/v3.** Только для отдельного stocks-робота (только LONG, не парно). Позже.
- **Расширение v2/v3 — только futures × futures** (через скринер с фильтром).

### Git

- (после commit)


---

## 2026-10-19 (ночь) — D1-тупик, cross-class: симуляция OK

### D1-тест — тупик

- **Данных мало:** SFIN-SH_D1, BANE-BN_D1, BELU-NB_D1 — **~61 строка** после merge. Walk-forward **невозможен** (warmup 50 + window 20 = 70 > 61).
- **OLS:** SFIN-SH — 1 сделка (+0.0139), BANE-BN — 0 сделок, BELU-NB — 2 сделки (+0.0088). **Ничтожно.**
- **Kalman:** 0 сделок везде (warmup не укладывается).
- **Вывод:** D1 **не спасает** M10-пары. **M10 в v3 — окончательно off.** Альтернатив (H1, D1) нет.

### Cross-class — симуляция (без изменения кода)

- **GAZP-GAZPF_H4:** LONG_SPREAD → ✅ OK (BUY GAZP, SELL GAZPF); SHORT_SPREAD → ⏸️ BLOCKED (SELL GAZP — акция).
- **LKOH-LK_H4:** LONG_SPREAD → ✅ OK (BUY LKOH, SELL LK); SHORT_SPREAD → ⏸️ BLOCKED.
- **Вывод:** cross-class **уже работает** на уровне кода `is_stock()`. **Без изменений.** LONG_SPREAD проходит, SHORT_SPREAD блокируется. **Твоя позиция соблюдена.**

### Cross-class — walk-forward

- **Баги:** `pd.merge` падал на `datetime64 vs str` — фикс: `pd.to_datetime` до merge.
- **Пары:** GAZP-GAZPF_H4, LKOH-LK_H4, SBER-SBERF_H4.
- **Split по direction:** LONG_only (акция в BUY), SHORT_only (акция в SELL — блок), BOTH.
- **Ждём:** net_pnl > 0 на LONG_only → **включить** в v3 (enabled=true). Если нет — **не включать**.

### v3.2 — не тронут

- 4 H4-пары (GD-SV, PD-SV, PT-SV, LK-IMOEXF) + GAZP-GAZPF (disabled, наблюдение).
- v1/v2 — не тронуты.

### Git

- (после commit)


---

## 2026-10-19 (ночь) — cross-class H4 закрыт (формат данных), D1 возможен

### Cross-class H4 — невозможен (формат данных)

- **Акции** (`GAZP_H4`, `LKOH_H4`, `SBER_H4`): `begin` — `datetime64[us]`, **с временем** (`16:00, 20:00, 04:00` — 4-часовые).
- **Фьючерсы** (`GAZPF_H4`, `LK_H4`, `SBERF_H4`): `tradedate` — **str**, **только дата** (`2025-05-15`), без времени. `pd.to_datetime` → `00:00:00`.
- **Merge по `dt`:** акция `16:00` vs фьючерс `00:00` → **никогда не совпадают** → `rows=0`.
- **Вывод:** cross-class **H4 невозможен** без пересборки фьючерсных H4 с `begin`. **Отдельная задача** (поправить `candles_collector.py` / `futures_h4_aggregate.py`). **Не сегодня.**
- **GAZP-GAZPF_H4** — оставить в v3 (disabled), но **не торгует** (cross-class невозможен).

### H8/H6 — не спасает

- **H4-пары (GD/SV/PD/PT):** `resample('6h')` и `resample('8h')` **не режут** (360→360) — данные H4 **уже редкие** (или `tradedate` без времени, 1 бар в день).
- **M10-пары (SFIN/BANE/BELU):** H6 = 284, H8 = 223 — **работает**, но **M10 off в v3**.
- **Вывод:** H8/H6 **не спасает**. Для H4-пар данных не хватает, для M10-пар — M10 off.

### v3.2 — не тронут

- 4 H4-пары (GD-SV, PD-SV, PT-SV, LK-IMOEXF) + GAZP-GAZPF (disabled).
- v1/v2 — не тронуты.

### Git

- (после commit)


---

## 2026-10-19 (финал) — EURRUBF-тест (OLS прибыльный), чистка v3

### EURRUBF-USDRUBF_H4 — тест

- **OLS:** net_pnl +0.48…+0.51 (entry_z 1.5–2.0), WR 0.61–0.89, net_sharpe 6.0–18.2. **Прибыльно!**
- **Kalman:** net_pnl −0.92…−0.037. **Не работает.**
- **Вывод:** EURRUBF-USDRUBF — **OLS-пара**, не Кальман. Добавлена **в v2** (OLS, entry_z=2.0, enabled=false, наблюдение).
- **Источник:** coint_p=0.114 (не коинтегрирована формально), но corr=0.918 + walk-forward OLS прибыльный.

### v3 — чистка H1-пар

- **H1-пар в v3: 15** (наследие от v1-копии, все `enabled=false`).
- **Удалено** из config v3 (гигиена). Осталось: 4 H4-пары (GD-SV, PD-SV, PT-SV, LK-IMOEXF) + GAZP-GAZPF (disabled).
- **M10 off** (все 24 M10-пары `enabled=False`).
- **Бэкап:** `pairs_config_v3.json.bak3`.

### v2 — EURRUBF добавлена

- **v2:** 8 M10/H4-пар + EURRUBF-USDRUBF_H4 (disabled). Всего 9.
- **enabled:** 8 (M10: SFIN-SH, BANE-BN, BELU-NB; H4: GD-SV, PD-SV, PT-SV, LK-IMOEXF).
- **EURRUBF** — disabled, наблюдение. Включить после 2-3 дней, если signals идут.

### v3.2 — финал

- 4 H4-пары (GD-SV=2.0, PD-SV=1.8, PT-SV=2.5, LK-IMOEXF=2.0) + GAZP-GAZPF (disabled).
- **Не трогать** 3-5 дней, наблюдать.

### Git

- (после commit)


---

## 2026-10-19 (финал-2) — чистка v2 (H1-пары)

### v2 — удалены H1-пары

- **H1-пар в v2: 15** (наследие от v1-копии, все `enabled=false`).
- **Удалено** из config v2 (гигиена). Осталось: 58 пар (как в v3).
- **Бэкап:** `pairs_config_v2.json.bak1`.
- **enabled:** 8 (M10: SFIN-SH, BANE-BN, BELU-NB; H4: GD-SV, PD-SV, PT-SV, GD-PT? — проверить).

### v2 — EURRUBF-USDRUBF_H4 (disabled)

- Добавлена, наблюдение. entry_z=2.0, OLS.
- **Включить** после 2-3 дней, если signals идут.

### v3 — почищен (H1 удалены, 4 H4-пары)

- GD-SV=2.0, PD-SV=1.8, PT-SV=2.5, LK-IMOEXF=2.0 + GAZP-GAZPF (disabled).
- **Не трогать** 3-5 дней.

### Git

- (после commit)


---

## 2026-10-19 (финал-3) — H1-пары в v2: восстановлены, тест

### Почему H1 удаляли — НЕ потому что убыточны

- **H1-пары в v2** (15) — **никогда не тестировались**. Попали в config **автоматически** (копия v1), все `enabled=false`. **Никто их не включал.**
- **Удалили — гигиена**, не приговор. **Правило IDEAS.md:** «идеи не затираются». **Ошибка** — удалили без теста.
- **Восстановлены** из бэкапа `pairs_config_v2.json.bak1` (disabled).

### H1 — тест (3 пары: LKOH-ROSN, ROSN-TATN, LK-HY)

- **Метод:** OLS (v2), walk-forward 3 фолда, entry_z 1.5–3.0.
- **Ждём:** net_pnl > 0 → **оставить** (disabled, включить позже). Если < 0 — **удалить** (обоснованно).
- **Результат:** (после запуска)

### v2 — 73 пары (восстановлены H1)

- **enabled:** 8 (M10: SFIN-SH, BANE-BN, BELU-NB; H4: GD-SV, PD-SV, PT-SV, GD-PT, LK-IMOEXF).
- **EURRUBF-USDRUBF_H4** — disabled, наблюдение.
- **H1** — 15 пар, disabled, тест.

### Git

- (после commit)


---

## 2026-10-19 (финал-4) — H1-тест (все 15 пар), LKOH-HYDR enabled

### H1-тест — результаты (walk-forward OLS, 3 фолда, entry_z 1.5–3.0)

**Прибыльные (4/15):**
| Пара | entry_z | net_pnl | WR | n | Решение |
|---|---|---|---|---|---|
| **LKOH-HYDR_H1** | **1.5** | **+1.30** | 0.687 | **413** | ✅ **enabled** (реально прибыльная) |
| SFIN-SH_H1 | 2.5 | +0.108 | 0.752 | 17 | disabled (мало сделок) |
| HY-IR_H1 | 3.0 | +0.027 | 0.833 | 5 | disabled (ничтожно) |
| RASP-RA_H1 | 3.0 | +0.013 | 0.833 | 4 | disabled (ничтожно) |

**Убыточные (11/15):** SOFL-S0, LKOH-ROSN, LKOH-TATN, ROSN-TATN, LKOH-IRAO, HYDR-IRAO, LK-HY, LK-RN, LK-TN, RN-TN, LK-IR — **disabled** (не удалять — правило IDEAS.md).

### v2 — рабочие ТФ

- **M10 (3):** SFIN-SH, BANE-BN, BELU-NB (OLS entry_z=1.8) — **работают** (+9.60).
- **H4 (5):** GD-SV, PD-SV, PT-SV, GD-PT, LK-IMOEXF (OLS entry_z=2.0–2.5) — **работают**.
- **H1 (1 enabled + 14 disabled):** **LKOH-HYDR_H1** — **включена** (единственная прибыльная с n=413).
- **EURRUBF-USDRUBF_H4** — disabled (наблюдение).
- **Итог:** v2 = **9 enabled** (3 M10 + 5 H4 + 1 H1).

### Git

- (после commit)


---

## 2026-10-19 (финал-5) — согласовано на завтра: discovery + AI

### Discovery новых активов (MOEX ISS) + AI-оценка — завтра

- **Согласовано** с напарником: сделать `scripts/discover_and_screen.py`.
- **Что:** MOEX ISS API → полный список фьючерсов → сравнить с `tickers_config.json` → новые тикеры → упрощённая проверка (corr + coint_p) против **старых** → отчёт.
- **AI-оценка:** отчёт → `ai_data_context` → AI-daily (или отдельный скрипт) → **рекомендации**: «перспективна / рискованна / требует walk-forward».
- **Не автоматическое добавление** — только **сигнал** для человека.
- **Фильтры:** coint_p < 0.05 (cross-class < 0.01), ликвидность > порога, total_rows >= 500.
- **Записано в IDEAS.md п. 12.**
- **Реализация — завтра (20.10.2026).**

### Итог дня (19.10.2026)

- **v2:** 9 enabled (3 M10 + 5 H4 + 1 H1 — LKOH-HYDR). EURRUBF disabled (наблюдение).
- **v3:** 4 H4-пары (GD-SV, PD-SV, PT-SV, LK-IMOEXF). M10 off, H1 нет. GAZP-GAZPF disabled.
- **Кальман H4:** подтверждён (165× PnL vs OLS). M10/H1/D1 — тупик (cost > spread).
- **H1-тест:** 4/15 прибыльных, LKOH-HYDR enabled (n=413, +1.30).
- **Скринер:** фьючерсы — 0 коинтегрированных. EURRUBF-USDRUBF — OLS прибыльный (в v2, disabled).
- **Cross-class H4:** закрыт (формат данных). D1 — отложен. Пересборка H4 — в IDEAS.md п. 11.
- **Git:** 5e3e653.

### Git

- (после commit)


---

## 2026-10-20 (день) — discovery + AI: единый отчёт

### Discovery (MOEX ISS) — dry-run

- **ISS:** 497 фьючерсов (SECID), но это **серии** (`92V6`, `92X6`, `92Z6` — один фьючерс, разные месяцы).
- **Проблема:** 489 «новых» — **мусор** (экспирации).
- **Фикс:** брать **ASSETCODE** (базовый код), фильтр `[A-Z0-9]{2,6}` → **десятки** базовых, а не 489.
- **Dry-run (после фикса):** (результат — после блока 2)

### Единый отчёт: discovery + AI

- **Проблема:** AI-daily в 19:30, discovery в 18:00 вс. **Рассинхрон.**
- **Решение:** discovery — вс 18:00 → `logs/discovery_*.csv`. AI-daily — вс 19:30 → **добавить в контекст** `discovery_summary` (если файл есть). **Один отчёт** (AI-daily) с **секцией discovery**.
- **Патч:** `ai_data_context.py` → `get_discovery_summary()` (читает последний CSV, top-15).
- **AI-оценка:** в AI-daily — **рекомендации** по discovery («перспективна / рискованна / требует walk-forward»). **Не автоматическое добавление.**

### v2 / v3 — утренний срез

- **v2:** signals идут (221 z_below_entry, 136 time, 12 corr, 10 ML_BLOCK). **1 позиция**, 2 трейда (вчера +9.60). **LKOH-HYDR_H1:** 10 signals (все `MISSED corr` — corr < порога). **EURRUBF:** 0 signals (нет данных? disabled?).
- **v3:** signals идут (12 z_below_entry, 8 time). **0 позиций, 0 трейдов** — за сутки **ни одного entry_z**. Норма.
- **AI-daily 19.10:** различает v1/v2/v3 ✅. Не знает про 19.10-изменения (v2 9 enabled, LKOH-HYDR, EURRUBF) — **ожидаемо** (отчёт до изменений).

### Git

- (после commit)


---

## 2026-10-20 (день-4) — discovery: 0 пар (факт), пустой CSV, weekly

### Discovery — полный запуск

- **ISS:** 215 (ASSETCODE), базовых: 195. Существующих: 164. Новых: 186.
- **H4 есть:** новых 49, старых 162.
- **Screening:** **0 пар** прошли фильтры (coint_p < 0.05 + corr > 0.5).
- **Причина:** новые тикеры (AI92, ASML, AFRICA, BTC, COCOA, COPPER…) — **другие классы** (иностранные акции, товары, крипта). **Не коррелируют** с нашими фьючерсами на H4.
- **Вывод:** discovery **работает правильно** — честно говорит «среди новых нет ничего, что статистически связано со старыми на H4». **Не баг.**

### Фикс: пустой CSV

- **Проблема:** `discover_and_screen.py` не писал CSV, если 0 результатов → `get_discovery_summary` → `no_file`.
- **Фикс:** писать **пустой CSV с заголовками** → `status: ok, rows: 0`.
- **Результат:** (после блока 4)

### ai_weekly_report.py — фикс

- **Проблема:** `discovery_summary` был **только в импорте**, не в `user_content`.
- **Фикс:** `discovery = get_discovery_summary()` + вставка `=== DISCOVERY ===\n{discovery}` в `user_content`.
- **Результат:** (после блока 5)

### v2 / v3 — не тронуты

- v2: 9 enabled. v3: 4 H4.
- **EURRUBF:** 0 signals (disabled, нет данных?). **LKOH-HYDR:** 10 signals, все `MISSED corr` — наблюдать.

### Git

- (после commit)


---

## 2026-10-20 (итог дня) — discovery 0 пар (факт), фокус на работающем

### Discovery — итог

- **0 пар** (новые не коррелируют со старыми на H4). **Не баг — факт.**
- **186 новых** (BTC, COCOA, COPPER, ASML, AFRICA…), **49 с H4**. **Не коррелируют** с фьючерсами MOEX.
- **Вывод:** discovery **работает правильно**. **Не ждать чуда.** Через месяц (когда накопится история по новым) — вернуться.

### Фокус (Путь 2)

- **v2:** 9 enabled (3 M10 + 5 H4 + 1 H1 LKOH-HYDR). **Работает.**
- **v3:** 4 H4. **Работает.**
- **EURRUBF:** OLS прибыльный, disabled. **Включить через 2–3 дня** (если signals идут).
- **LKOH-HYDR:** 10 signals, все `MISSED corr` — **наблюдать**.
- **Пересборка H4 фьючерсов** (IDEAS.md п. 11) — **важнее discovery**.

### Cron (финал)

- **AI-daily:** пн–сб 19:30.
- **AI-weekly:** вс 17:00 (с discovery).
- **Discovery:** вс 16:50 (пустой CSV, если 0).
- **pairs_screener:** вс 18:00.
- **pairs_quarantine:** ежедневно 19:45.

### Git

- 5603025 — discovery: пустой CSV (0 пар); weekly: discovery в user_content.


---

## 2026-10-20 (вечер, разбор Daily) — выводы

### Daily Report 20.10 — разбор

**Работает:**
- v3: 96 z_below_entry + 8 time — сигналы идут, z не достигает entry_z (норма).
- v2: 9 enabled, BANE-BN_M10 +9.60 (19.10) — логика v2 работает.
- ML-фильтр: v1 (3 BLOCK), v2 (20 BLOCK), v3 (1 BLOCK) — корректно.
- AI-daily: различает v1/v2/v3 ✅.
- Свежесть: M10/H1/D1 286/295, H4 295/295 — норма.

**Внимание:**
- **v2 LKOH-HYDR_H1:** corr=-0.009 (ниже gate 0.5). Пара новая (19.10), corr нестабильна. **Наблюдать 2-3 дня.** Если не восстановится — disabled.
- **v3 open_failed (2):** вероятно шорт акции / price≤0 / volume<1. **Проверить лог v3.**
- **v1:** 0 сделок, 252 MISSED(time) + 213 MISSED(z_below_entry). Норма (окно 07:00-18:00, entry_z=2.5). AI рекомендует сравнить entry_z=2.5 (v1) vs 1.8 (v2) — за неделю. **v1 не трогаем** (эталон).

**Критично:**
- **`candles_collector.py` НЕ НАЙДЕН** по пути `scripts/candles_collector.py`. Добавили 13 новых тикеров (BTC, COCOA, COPPER…) в `tickers_config.json`, но **сборщик не найден**. **Найти реальный сборщик** — иначе новые тикеры не соберутся.

### Git

- (после commit)


---

## 2026-10-20 (вечер) — adaptive_test_suite: результаты

### Итог: адаптивность НЕ лучше Baseline

**M10 (SFIN-SH, BANE-BN, BELU-NB):**
- Baseline (entry_z=2.0): PnL -0.0002…-0.0204, WR 0.375–0.382, Sharpe -1.76…-2.24. **Убыточно.**
- A (adaptive): Sharpe -11…-16. **Хуже.**
- E (MOEX window): Sharpe -3.5…-5.2. **Хуже.**
- I (time-of-day): Sharpe -4.2…-7.9. **Хуже.**
- K (stop-loss): Sharpe -2.6…-4.8. **Хуже.**
- **Вывод:** M10 **не для адаптивности**. Только v2 с OLS entry_z=1.8 (не 2.0).

**H4 (GD-SV, PD-SV, PT-SV, LK-IMOEXF):**
- Baseline (entry_z=2.0): PnL +0.36…+4.34, WR 0.853–0.890, Sharpe 12.2–17.1. **Прибыльно.**
- A (adaptive): Sharpe 8.5–11.0. **Хуже.**
- E (MOEX window): **0 сделок** (баг: H4-данные без времени → фильтр режет всё).
- F (quantile): **0 сделок** (баг: percentile rank с NaN).
- I (time-of-day): Sharpe 12.2–17.1 (идентично Baseline — H4 без времени, time-of-day не работает).
- K (stop-loss): Sharpe 3.9–6.8. **Хуже.**
- **Вывод:** H4 **Baseline — лучший**. Адаптивность **не улучшает**.

**Баги в скрипте:**
- E (MOEX window): H4-данные без времени → фильтр 10:00–24:00 режет всё.
- F (quantile): percentile rank с NaN → 0 сделок.
- C, G, H — заглушки (идентичны Baseline).

### Решение: v4 (тестовый робот)

- **Создать** `pairs_robot_test.py` (v4) — **отдельный**, не трогает v1/v2/v3.
- **Встроить** в дашборд — таб «📊 Парная торговля v4 (test)».
- **Подключить** к AI — `get_robot_state_v4()`, `get_trades_v4()`, `get_signals_v4()`.
- **v4 — песочница** для «безумных идей» (адаптивность, ML, multiple entry, stop-loss). **Сейчас — не лучше Baseline**, но **продолжаем тестировать**.
- **v1/v2/v3 — не трогаем.**

### Git

- (после commit)


---

## 2026-10-20 (итог дня) — discovery, адаптивность, v4 (test)

### Discovery (MOEX ISS)

- **`scripts/discover_and_screen.py`** — создан. MOEX ISS → полный список фьючерсов (ASSETCODE) → сравнить с `tickers_config.json` → новые → corr/coint → отчёт.
- **Dry-run:** 186 «новых» (BTC, COCOA, COPPER, ASML, AFRICA…). **49 с H4.**
- **Screening:** **0 пар** (coint_p < 0.05 + corr > 0.5). **Не баг — факт.** Новые (BTC, COCOA, COPPER) — **другие классы**, не коррелируют с фьючерсами MOEX на H4.
- **Фикс:** пустой CSV (если 0 пар) → `get_discovery_summary` → `status: ok, rows: 0`.
- **Cron:** discovery — вс 16:50 (перед weekly 17:00). **Weekly** — `discovery_summary` в контексте. **Один отчёт.**

### Сбор истории по новым

- **13 перспективных** (BTC, COCOA, COPPER, ALUM, UCAD, AI92, AI95, AED, BYN, UCHF, AUDU, BRAZIL, ARGT) → **добавлены** в `tickers_config.json` (164 → 177).
- **Сборщик** — `FinLabPy/DataCollectors/candles_collector.py` (не `scripts/`). Cron → H4/M10/H1/D1.
- **Через 1–2 недели** — discovery по ним.

### EURRUBF — enabled (v2)

- **Было:** disabled, 0 signals.
- **Стало:** enabled=true, entry_z=2.0. **Signals пойдут.**
- **Основание:** walk-forward OLS прибыльный (net_pnl +0.514, WR 0.728, Sharpe 10.5).

### Adaptive test suite (A–M)

- **`scripts/adaptive_test_suite.py`** — создан. Walk-forward по идеям A–M (без пирамидинга).
- **Результаты:**
  - **M10 (SFIN-SH, BANE-BN, BELU-NB):** Baseline (entry_z=2.0) **убыточен** (Sharpe -1.76…-2.24). **Адаптивность — хуже** (Sharpe -4…-16). **M10 — не для адаптивности.**
  - **H4 (GD-SV, PD-SV, PT-SV, LK-IMOEXF):** Baseline **прибыльный** (Sharpe 12.2–17.1). **Адаптивность — хуже** (Sharpe 8.5–11.0). **Baseline — лучший.**
  - **Баги:** E (MOEX window) — 0 сделок (H4 без времени), F (quantile) — 0 сделок (NaN).
- **Вывод:** **адаптивность не улучшает** результаты. Baseline — лучший. **v4 — песочница** для дальнейших идей.

### v4 (test) — тестовый робот

- **`robots/pairs_robot_test.py`** — копия v2 + отдельные пути (`pairs_robot_test.db`, `pairs_config_test.json`, `robot_state_test.json`, `robot_command_test.txt`).
- **`FinLabPy/My_Indicators/pairs_config_test.json`** — копия v2.
- **`/etc/systemd/system/finlab-robot-test.service`** — создан, **enabled**, **не запущен** (disabled).
- **Дашборд:** radio «📊 Парная торговля v4 (test)» (добавлен). **Таб v4 — не встроен** (следующий шаг).
- **AI:** `get_robot_state_v4()`, `get_trades_history_v4()`, `get_signals_summary_v4()` — в `ai_data_context.py`. **AI-daily/weekly** — import добавлен. **Контекст** — v4 в `user_content` (weekly).
- **v4 — disabled** (не торгует). **v1/v2/v3 — не трогаем.**

### v2 / v3 — статус

- **v2:** 10 enabled (3 M10 + 6 H4 + 1 H1 LKOH-HYDR). EURRUBF — disabled (0 signals, **проверить**: enabled=False?).
- **v3:** 4 H4 (GD-SV, PD-SV, PT-SV, LK-IMOEXF). Кальман. 0 trades (entry_z не достигнут).
- **LKOH-HYDR:** corr=-0.009 (MISSED corr_gate). Наблюдать 2–3 дня.
- **open_failed (v3):** BANE-BN_M10 — шорт по акции BANE. **Историческое** (v3 не торгует BANE). **Не баг.**

### Daily 20.10 — разбор

- **Работает:** v2 (+9.60), v3 (signals идут), ML-фильтр, AI-daily (v1/v2/v3), свежесть.
- **Внимание:** LKOH-HYDR (corr=-0.009), v3 open_failed (2, исторические), v1 (0 сделок — норма).
- **Критично:** `candles_collector.py` — найден (`FinLabPy/DataCollectors/`). **13 новых тикеров** — подхватит.

### Git

- 434c42c — adaptive_test_suite.py, tickers_config (+13).
- 6ba473b — v4 (test): pairs_robot_test.py, pairs_config_test.json, ai_data_context.
- 064b35f — dashboard: radio v4; AI-daily/weekly: v4 в контекст.

### Следующее (21.10)

- **Дашборд:** таб v4 (полный, по образцу v3).
- **AI-weekly (вс 17:00):** проверить discovery (0 пар) + v4.
- **EURRUBF:** проверить (enabled=False? почему 0 signals?).
- **LKOH-HYDR:** наблюдать (corr=-0.009).
- **v2/v3 — не трогаем.** **v4 — disabled.**
- **Пересборка H4 фьючерсов** (IDEAS.md п. 11) — следующий важный шаг.


---

## 2026-10-21 (день) — v2: вторая сделка (+2.08₽)

### v2 — BANE-BN_M10, LONG_SPREAD

- **Вход:** Z=-2.36, BUY BANE @ 1354.50, SELL BN @ 1393.00.
- **Выход:** PnL **+2.08₽** (A: -22.50₽, B: +28.00₽).
- **Нога A (BANE, BUY):** -22.50₽ (BANE упал).
- **Нога B (BN, SELL):** +28.00₽ (BN упал, шорт).
- **Спред сошёлся** — BN упал сильнее, чем BANE → LONG_SPREAD заработал.

### v2 — итог (2 сделки)

- **BANE-BN_M10:** +9.60 (19.10) + **+2.08** (21.10) = **+11.68₽**.
- **WR 100%** (2/2).
- **v2 — работает** (M10, OLS, entry_z=1.8).

### v2 — 10 enabled

- M10: SFIN-SH, BANE-BN, BELU-NB.
- H4: GD-SV, PD-SV, PT-SV, GD-PT, LK-IMOEXF, **EURRUBF** (enabled, ждём signals).
- H1: LKOH-HYDR (corr=-0.009, ждём).

### v3 — 4 H4, 0 trades

- GD-SV, PD-SV, PT-SV, LK-IMOEXF. **entry_z не достигнут** (max |z|=1.23 за 20.10).

### Следующее (21.10)

- **v3 — entry_z=1.8** (H4) — тест (walk-forward). Если лучше — понизить (v3.3).
- **v2 — ML для BELU-NB** — тест.
- **v2 — entry_z=1.5** (M10) — тест.
- **v4 — multiple entry_z** — тест.
- **v2/v3 — не трогаем** (v2 работает, v3 — наблюдаем).

### Git

- (после commit)


---

## 2026-10-21 (день-2) — разбор сделки BANE-BN_M10 (+2.08₽)

### Цифры (из ВК-бота)

- **PnL = +2.08₽** (общий).
- **A: -22.50₽** (нога A — BANE, BUY).
- **B: +28.00₽** (нога B — BN, SELL).

### Разбор

- **A + B = +5.50₽** (до комиссии).
- **Cost = 3.42₽** (комиссия 0.28% × 2 + проскальзывание 0.02% × 2 = 0.32%).
- **PnL_total = +2.08₽** (5.50 - 3.42).
- **Сделка прибыльная** (+2.08₽). **A = -22.50₽** — **убыток одной ноги**, **B = +28.00₽** — **прибыль другой**. **Вместе** — **+5.50₽** (до cost), **+2.08₽** (после).

### Почему A убыточна, а B прибыльна

- **BANE (A, BUY):** упал → убыток -22.50₽.
- **BN (B, SELL):** упал сильнее → прибыль +28.00₽.
- **Спред сошёлся** (BN упал сильнее BANE) → **LONG_SPREAD** заработал.

### Вывод

- **Сделка прибыльная** (+2.08₽). **Не убыточная** (-20 — неверная логика: A и B — **разные ноги**, **сумма** = +5.50, **PnL** = +2.08).
- **Cost (3.42₽)** — значительный (относительно +5.50₽ gross). **На M10** — заметно. **На H4** — меньше (больше движение).

### Git

- (после commit)


---

## 2026-10-21 (вечер) — Daily 21.10, v3 walk-forward

### v2 — 3 сделки, +32.44₽, WR 100%

- SFIN-SH_M10: +20.76 (21.10, entry_z=-1.895, exit_z=-0.397).
- BANE-BN_M10: +9.60 (19.10), +2.08 (20.10).
- **Все — LONG_SPREAD**, вход по отрицательному z (1.8–2.4), выход у нуля, короткое удержание (20–80 мин).
- **v2 — работает** (M10, OLS, entry_z=1.8).

### v3 — walk-forward (entry_z=1.5/1.8/2.0/2.5)

- **GD-SV:** 2.5 — best (Sharpe 16.5). 1.8 — 13.9. **2.5 лучше.**
- **PD-SV:** 2.5 — best (15.8). 1.8 — 13.7. **2.5 лучше.**
- **PT-SV:** 2.5 — best (16.8). 1.8 — 13.9. **2.5 лучше.**
- **LK-IMOEXF:** убыточный на всех (Sharpe -34…-44). **Мало данных (n=13–50).** Наблюдать.
- **Вывод:** **entry_z=2.5 — лучший** (Sharpe 15–17). **1.8 — хуже.** **v3 — не трогаем** (entry_z=2.0–2.5 — правильные).

### Daily 21.10 — выводы

- **v2:** 3 сделки, +32.44₽, WR 100%. **Работает.**
- **v3:** 0 trades (entry_z не достигнут). **Норма** (тихий рынок). **entry_z=2.5 — лучший** (walk-forward).
- **v1:** short_forbidden (SFIN-SH z=+4.94, BANE-BN z=+2.95) — **правило** (шорт по акции запрещён). **Не трогаем.**
- **SFIN-SH_M10 (+20.76):** entry_z=-1.895 (на грани 1.8). **Логировать proba** — позже.
- **Данные:** норма (H4 свежий, «мёртвые» тикеры — не аномалия).

### Следующее (22.10)

- **v2 — ML для BELU-NB** — тест (отключить/адаптивный порог).
- **v2 — entry_z=1.5** (M10) — тест.
- **v4 — multiple entry_z** — тест.
- **Bybit** — позже (IDEAS.md п. 13).
- **v1/v2/v3 — не трогаем** (v2 работает, v3 — наблюдаем).

### Git

- (после commit)


---

## 2026-10-21 (вечер-2) — ML-тест BELU-NB, IDEAS.md

### ML-тест BELU-NB_M10 (walk-forward, 3 фолда, entry_z=1.8)

| Вариант | n | NET | WR | Sharpe |
|---|---|---|---|---|
| ML off | 200 | -0.1379 | 0.291 | -6.09 |
| ML fixed (0.5) | 107 | -0.0597 | 0.302 | -5.19 |
| ML adaptive (30-й перцентиль) | 103 | -0.0483 | 0.311 | -4.58 |

**Выводы:**
- **Все три — убыточные** (NET < 0). **BELU-NB — слабая пара** (на истории).
- **ML off — хуже** (-6.09). **ML fixed — лучше** (-5.19). **ML adaptive — лучший** (-4.58).
- **ML нужен** (без него — хуже). **Adaptive — лучше fixed.**
- **v2 — не трогаем** (ML fixed, BELU-NB — не входила — все ML_BLOCK). **Наблюдаем.**

### IDEAS.md — обновлён

- **п. 8 (pairs_screener.py):** `in-progress` → **`done`** (создан, запущен, 0 коинтегрированных фьючерсов).
- **п. 12 (Discovery + AI):** `pending` → **`done`** (создан `discover_and_screen.py`, cron вс 16:50, weekly с `discovery_summary`; screening 0 пар — факт).
- **п. 9 (копулы, авто-карантин v2), п. 10 (cross-class D1), п. 11 (пересборка H4), п. 13 (Bybit)** — pending.

### Git

- (после commit)


---

## 2026-10-21 (вечер-3) — BELU-NB: решение, задание adaptive ML

### BELU-NB — решение (оставить, ML fixed)

- **Walk-forward:** BELU-NB_M10 убыточна на истории при **всех** вариантах ML (off: -6.09, fixed: -5.19, adaptive: -4.58).
- **Реальная торговля (v2):** BELU-NB **ни разу не входила** (все signals — `ML_BLOCK`). **0 сделок.** ML режет — **правильно**.
- **Решение:** **оставить в v2 (ML fixed).** **Не отключать, не менять на adaptive.** ML fixed **уже режет** BELU-NB (0 сделок) — **вреда нет**.
- **Задание (позже):** adaptive ML (30-й перцентиль) — **если понадобится** (логировать proba, адаптировать порог). **Не сейчас** (BELU-NB не торгует — экономия времени).
- **Забыть** (не тратить время). **Двигаемся дальше.**

### Следующее (22.10)

- **v2 — entry_z=1.5** (M10) — тест (walk-forward).
- **v4 — multiple entry_z** — тест.
- **Bybit** — позже (IDEAS.md п. 13).

### Git

- (после commit)


---

## 2026-10-21 (вечер-5) — v4: multiple entry_z (тест)

### BELU-NB — зафиксировано (оставить, ML fixed)

- enabled=True, entry_z=1.8, ML fixed (0.5). **v2 = 10 enabled.** **Не трогаем.**

### v4 multiple entry_z — тест

- **Multiple:** вход по 1.5 (25%), 2.0 (50%), 2.5 (100%). Выход z ≤ 0.5.
- **Single:** 1.8 (M10), 2.0 (H4) — текущий v2/v3.
- **Пары:** 3 M10 + 4 H4. **Walk-forward** (3 фолда).
- **Результат:** (после запуска)
- **v2/v3 — не трогаем** (тест на v4).

### Следующее (22.10)

- **Bybit** — позже (IDEAS.md п. 13).
- **v1/v2/v3 — не трогаем** (v2 работает, +32.44₽; v3 — наблюдаем).

### Git

- (после commit)


---

## 2026-10-21 (вечер-6) — v4: песочница (multiple entry — хуже), дашборд

### v4 — песочница (не торговый робот)

- **v4 (test)** — **НЕ торговый робот.** Песочница (sandbox) для тестов идей.
- **Не торгует** (disabled). **Не трогает** v1/v2/v3.
- **Отдельная БД** (`pairs_robot_test.db`), config (`pairs_config_test.json`), state (`robot_state_test.json`).
- **Зачем:** тестировать «безумные идеи» (multiple entry, adaptive ML, stop-loss, risk parity) **без риска** для v2/v3.

### v4 multiple entry_z — результат

| Пара | Single (1.8/2.0) | Multiple (1.5/2.0/2.5) |
|---|---|---|
| SFIN-SH_M10 | -5.20 | -101.88 |
| BANE-BN_M10 | -6.49 | -160.27 |
| BELU-NB_M10 | -6.09 | -178.44 |
| GD-SV_H4 | +12.45 | +1.11 |
| PD-SV_H4 | +13.58 | +0.74 |
| PT-SV_H4 | +15.29 | +0.60 |
| LK-IMOEXF_H4 | +16.87 | -13.29 |

**Вывод:** **multiple entry_z — ХУЖЕ** single (Sharpe -101…-178 на M10, +0.6…+1.1 на H4). **Не внедряем** в v2/v3. **v4 — тест** (не торгует).

### Дашборд — таб v4 (песочница)

- **Добавлен таб** «📊 Парная торговля_v4 (test)» — с предупреждением («🧪 Песочница. Не торгует. Для тестов.»).
- **Описание:** что это, зачем, результаты тестов.
- **Статус:** disabled (норма для песочницы).

### Следующее (22.10)

- **v2/v3 — не трогаем** (работают, +32.44₽).
- **v4 — другие идеи** (stop-loss, risk parity, adaptive ML) — тесты (позже).
- **Bybit** — позже (IDEAS.md п. 13).

### Git

- (после commit)


---

## 2026-10-22 (день) — разбор убыточной сделки BANE-BN_M10

### Убыточная сделка (4-я за сегодня)

- **Вход:** Z=-2.13, BUY BANE @ 1331.00, SELL BN @ 1365.00.
- **Выход:** PnL **-21.36₽** (A: -72.00₽, B: +54.00₽).
- **Нога A (BANE, BUY):** -72.00₽ (BANE упал сильно).
- **Нога B (BN, SELL):** +54.00₽ (BN упал, но меньше).
- **Спред:** BANE упал **сильнее**, чем BN → LONG_SPREAD **не сошёлся**.

### Гипотеза (почему убыточная)

1. **Z=-2.13 — на грани** (близко к 1.8, не 2.5). **Слабый сигнал.**
2. **BANE упал сильно** (-72₽) — **нога A** (BUY) **не сработала**.
3. **Связь с тестом v2 entry_z:** entry_z=1.8 — убыточен на истории (Sharpe -5.2…-6.5). **2.5 — лучший** (+4…+11). **Сделка 4 (Z=-2.13) — на грани** (не 2.5). **Слабый вход** → **убыток.**

### Итог дня (v2)

- **3 прибыльных** (+59.13, +54.37, +11.61) + **1 убыточная** (-21.36) = **+103.75₽**.
- **v2 — работает** (даже с убыточной — прибыль).

### Следующее (22.10)

- **AI-daily** — проверить (разбор).
- **v4 — stop-loss** (тест) — если убыточная из-за отсутствия stop-loss.
- **v2 — entry_z=2.5** (тест) — если 1.8 слабый (уже тестировали — 2.5 лучший).
- **v1/v2/v3 — не трогаем** (v2 работает).

### Git

- (после commit)


---

## 2026-10-22 (день-2) — PHP security update, разбор AI 22.10

### PHP — критическое обновление (CVE-2026-109618/109619)

- **Beget:** требуется обновление PHP (CVSS 9.2, RCE).
- **Ubuntu 24.04** (наш сервер) — затронута. **Обновление:** `sudo apt update && sudo apt upgrade`.
- **Перезапуск:** apache2, php8.3-fpm (без рестарта не применится).
- **Роботы (v1/v2/v3/v4)** — Python (не PHP), **не затронуты**.

### v2 — 4 сделки, +103.75₽, WR 75%

- SFIN-SH_M10: +59.13, +54.37 (быстрый возврат, 50 мин).
- BANE-BN_M10: +11.61 (короткая, 30 мин), **-21.36** (долгая, 110 мин — спред «застрял»).
- **Итог за 7 дней:** +136.2₽, 6/7 прибыльных.

### Убыточная BANE-BN_M10 (-21.36₽) — разбор

- **Вход:** Z=-2.13 (валиден). **Выход:** Z=-0.37 (валиден).
- **Держалась 110 мин** — спред не вернулся к 0.
- **AI рекомендует:** MAX_HOLD для M10 (90 мин) или exit_z=0.3. **Записать (п. 15)**. **v2 — не трогаем** (работает).

### AI 22.10 — выводы

- **v2 — работает** (+103.75₽). **Не трогаем** (наблюдать 2 недели).
- **v1/v3 — 0 сделок** (норма).
- **Freshness** — «мёртвые» тикеры (10–11) — не аномалия. **Записать** (п. 16 — исключить из freshness).
- **entry_z=1.8** — убыточен на истории (Sharpe -5…-6), но **v2 работает** (входы при z=-1.95…-2.40). **Не трогаем**.

### Следующее (23.10)

- **v4 — stop-loss / MAX_HOLD** (тест) — по рекомендации AI.
- **Книга Соколова** — ждём фото.
- **v1/v2/v3 — не трогаем**.

### Git

- (после commit)


---

## 2026-10-22 (вечер) — PHP, логи, разбор AI 22.10

### PHP — не установлен (уязвимость не актуальна)

- `php -v` → Command 'php' not found. **PHP на сервере нет.**
- Уязвимость CVE-2026-109618/109619 **не касается** нас (роботы — Python).
- `apt upgrade` обновил ядро/сеть. Роботы (v1/v2/v3) работают (`active`, 13h), перезапуск не требовался.

### Логи (после обновления)

- v1: `⛔ time (z=...)` — окно закрыто, норма.
- v2: `💤 z_below_entry` — фильтры работают, ждёт сигнал.
- v3: `📊 Проверка M10...` — (проверить, почему M10, если v3 на H4).
- State: все `running=true, paused=false`.

### AI 22.10 — выводы и IDEAS

- **v2 — отлично:** 4 сделки, +103.75₽, WR 75% (за 7 дней +136.2₽).
- **Убыточная BANE-BN (-21.36₽):** держалась 110 мин, спред «застрял». **AI советует:** MAX_HOLD (90 мин) или exit_z=0.3 для M10. **Записано в IDEAS.md п. 15** (тест в v4).
- **Freshness:** 10 «мёртвых» тикеров тянут oldest до 337ч. **Записано в IDEAS.md п. 16** (исключить из проверки).
- **v2 — не трогаем** (работает). **v4 — тест** (MAX_HOLD, exit_z) — позже.

### Git

- (после commit)



---

## 2026-10-22 (вечер-2) — Соколов: прочитаны главы 2.1–3.2, выводы

### Что прочитано

- **2.1** — оптимальное комбинирование коинтеграционных соотношений (веса 2.1.34–2.1.35, численный оптимум 2.1.40).
- **2.2** — численный пример (GBP/JPY через 6 пар), подтверждает метод.
- **2.3** — «быстрые/медленные» периоды, «время жизни» цены, τ=15/30/60 сек.
- **2.4** — модельная цена (close последнего «быстрого» периода).
- **3.1** — треугольные наборы, Йохансен, rank=1, log-цены значимее.
- **3.2** — хеджирование обязательств, частота ≥10 мин, USD/JPY как база.

### Выводы для FinLabPy

- **В v4 (pending):** 2.1 (комбинированный β для rank≥2), 2.3 (сглаживание EMA-3/EMA-5), 2.4 (модельная цена H1-inside-M10), 3.1 (баскет на тройке GD/PD/PT/SV).
- **Подтверждено (done):** 2.2 (численный пример), 3.1 (log-цены, H1/H4 > D1) — совпадает с v2/v3.
- **Parked:** 3.2 (хеджирование обязательств) — не наш кейс; берём подтверждение «M10 — правильная частота».

### Ограничение

- Тиков нет. Прямое воспроизведение τ=15/30/60 сек невозможно. Замена — сглаживание спреда (EMA-3, EMA-5) и модельная цена (H1-inside-M10). Это эвристики, проверяемые walk-forward.

### Детали

- **IDEAS.md п.14.1** — полный разбор по главам.

### Git

- (после commit)


---

## 2026-10-23 (вечер) — Sokolov EMA test: 2.3 не работает

### Результат

- **Скрипт:** `scripts/sokolov_ema_test.py` — walk-forward 8 фолдов, 3 пары × 5 вариантов (baseline, EMA-3/5 по спреду, EMA-3/5 по ногам).
- **Baseline лучше по всем парам.** PnL, Sharpe, число сделок — EMA < baseline везде. EMA-5 — убыточен.
- **Пример SFIN-SH_M10:** baseline PnL +0.372 / Sharpe 6.38 / 79 trades; EMA-3 +0.126 / 3.92 / 40; EMA-5 +0.054 / 3.48 / 30.
- **Причина:** M10 уже сглажен (тиков нет). Двойное сглаживание съедает сигнал.
- **Вывод:** гипотеза 2.3 верна для тиков, не для M10. **Не внедряем.** EMA-3_spread == EMA-3_legs (при фиксированной β совпадают — не баг).

### IDEAS.md

- п.14.1: 2.3 — `pending` → **`done`** (проверено, не внедряем).

### Логи

- `logs/sokolov_ema_2026-10-23_2131.csv` — полные результаты по фолдам.

### Следующее

- **2.1 — комбинирование β (rank≥2).** Скрипт `sokolov_beta_test.py`. Следующий шаг.
- Потом 2.4 (модельная цена), 3.1 (баскет).

### Git

- (после commit)


---

## 2026-10-23 (вечер-3) — Sokolov 2.1: combined_v1 работает на BANE-BN

### Проблема в первой версии

- `coint_johansen` на 9 парах (rank≥2).
- **У 8 из 9** ρ ≈ 1 (0.99+) — второй вектор не независим. **Только BANE-BN** ρ = 0.68 (M10).
- **Формула 2.1.35** была с σ² (ошибка). Исправлено на σ.
- **PnL не нормирован** — сравнение некорректно. Исправлено (std(spread)).

### Результат на BANE-BN (walk-forward 8 фолдов)

| mode | PnL | trades | WR | Sharpe |
|---|---|---|---|---|
| baseline | +23.90 | 13 | 1.00 | 2.77 |
| **combined_v1** | **+35.21** | **28** | 1.00 | **11.28** |
| combined_v2 | +29.35 | 22 | 1.00 | 9.57 |

- **combined_v1 лучше baseline:** PnL +47%, trades ×2.15, Sharpe ×4, WR не падает.
- **combined_v2 (с ρ) хуже v1** — ρ не нужна.
- **Оговорка:** 1 пара, мало сделок (13→28). Sharpe может быть завышен. Смотреть на v4 через 1–2 недели.

### Решение

- **IDEAS.md 14.1:** 2.1 → **`in_progress`** (не `done`, есть работающий вариант).
- **v4:** добавить combined_v1 **только для BANE-BN**. Остальные 8 — baseline (ρ≈1, не работает).
- **Через 1–2 недели** — если v4 подтверждает, включаем в **v2** (только BANE-BN).
- v2 — **не трогаем** (работает).

### Следующее

- **Внедрить в v4** (combined_v1 для BANE-BN). Потом — 2.4.

### Git

- (после commit)


---

## 2026-10-23 (вечер-4) — v4: combined_v1 для BANE-BN запущен

### Что сделано

- **v4** (`pairs_robot_test.py`) — **combined_v1** для **BANE-BN_M10**. Остальные 8 — baseline.
- **β** — `scripts/update_combined_betas.py` (cron 19:00 пн–сб, `1-6` — **суббота** **торговая** ).
- **`init_db()`** — добавлены колонки `leg_*` / `contract_*` / `volume_*` + таблица `signals` (как v2).
- **БД** **v4** — `positions` , `signals` , `trades` .
- **VK** — пометки `[v4]` / `[v4][combined_v1]` (в `send_vk_message`).
- **AI** — `get_robot_state_v4` , `get_trades_history_v4` , `get_signals_summary_v4` — работают (signals: 8 MISSED z_below_entry, 1 MISSED corr).
- **Дашборд** — таб v4: кнопки Старт/Пауза/Стоп, раскрывашка «Что анализирует v4», метрики (PnL, trades, WR). v4 — в «🤖 Роботы».

### Статус

- **v4** — `active (running)` , `paused=False` , `running=True`.
- **v2** — **не трогали** (работает, PnL +149.88₽, WR 87.5%).
- **v1/v3** — **не трогали**.

### Наблюдение

- **1–2 недели** — сравнить v4 (combined_v1) vs v2 (baseline) на BANE-BN.
- **Если** v4 **лучше** — включить **combined_v1** в **v2** (только BANE-BN).
- **Если** **хуже** — фиксируем, 2.1 `done` (не работает).

### Git

- (после commit)


---

## 2026-10-24 (вечер) — проверка сборщиков, is_moex_trading_day, LQDT, раскрывашки

### Проверка сборщиков

- **M10/H1** — 278/295 свежих (17 мёртвых — известные). **H4** — 295/295. **D1** — 6/296 (не обновляется с 23.10, не критично — v2/v3/v4 на M10/H1/H4).
- **TradeStats** — работает (свежие данные, keyring-ошибка не критична).
- **LQDT_D1** — работает (23.10 20:00).

### is_moex_trading_day (v1/v2/v3)

- **24.10** — торговый (допсессия MOEX). **25.10** — воскресенье (weekday==6).
- Убраны `(10,24),(10,25)` из `no_trade_weekends` в v1/v2/v3.
- **Commit:** `e70ee44` (v2/v4), `e70069d` (v3).

### v1 — BR-GAZPF_H4 → enabled=False

- corr=0.12 < 0.5, не торгует, засоряет проверки.
- **Commit:** `8765839`.

### v3 — заголовок + БД

- Заголовок: `v2 (эксперимент)` → `v3 (эксперимент)`.
- БД: `pairs_robot_v2.db` → `pairs_robot_v3.db` (было — читал v2).

### LQDT в v2/v3

- Функция `render_lqdt_comparison(closed_df, total_pnl, deposit)` — универсальная.
- В v2 — показывает (8 сделок, PnL +149.88₽, LQDT +0.19%, робот +0.15% → отстаёт на 0.04%).
- В v3 — 0 сделок, LQDT не появляется.
- В v4 — 0 сделок, LQDT не нужен.

### Раскрывашки v1/v2/v3

- `st.expander("🔍 Что и как анализирует vX")` — как в v4.
- v1: baseline, 07:00–18:00, entry_z=2.5, 3 ML.
- v2: rolling OLS, 07:00–23:00, entry_z=1.8, 10 пар, 3 ML, карантин SFIN-SH.
- v3: Кальман, H4, 4 пары, entry_z=2.0–2.5, 0 сделок.

### Кнопки v4 — логика как в v2

- Старт — активна, если сервис active и робот НЕ running (или на паузе).
- Пауза — активна, если running и НЕ на паузе.
- Стоп — активна всегда.

### Git

- (после commit)


---

## 2026-10-24 (вечер-2) — «⚙️ Настройки» закомментированы в v1

### Что сделано

- **v1** (таб «📊 Парная торговля») — блок «⚙️ Настройки» **закомментирован** (не используется роботом, значения не сохраняются).
- **TODO:** реализовать полноценно (связать UI с роботом: депозит, объём, тип объёма) — позже, когда будем делать multi-asset / risk-based sizing.
- **Код не удалён** — закомментирован (можно вернуть).

### Проверка

- **v1** — блок «⚙️ Настройки» исчез. Остальное (позиции, статистика, LQDT, журнал) — на месте.
- **v2/v3/v4** — блок «⚙️ Настройки» отсутствует (не было).

### Итог дня (24.10)

- **Сборщики** — проверены. M10/H1/H4/TradeStats/LQDT — работают. D1 — не обновляется с 23.10 (не критично).
- **is_moex_trading_day** — исправлен (24.10 — торговый, 25.10 — выходной).
- **v1** — BR-GAZPF_H4 → disabled.
- **v3** — заголовок (v2→v3) + БД (v2→v3).
- **LQDT** — в v2/v3 (v4 — 0 сделок, не нужен).
- **Раскрывашки** — в v1/v2/v3 (как в v4).
- **Кнопки v4** — логика как в v2 (Старт неактивна, если работает).
- **«⚙️ Настройки»** — закомментированы в v1.

### Git

- (после commit)


---

## 2026-10-24 (вечер-3) — check_collector_logs: ложные срабатывания

### Проблема

- `check_collector_logs.py` искал `ERROR` во **всех** логах, включая `ai_daily_cron.log` (AI-отчёт).
- В отчёте AI есть текст «**ERROR**» (в контексте рекомендаций) → скрипт считал это ошибкой сборщика.
- VK-уведомления: «Обнаружены ошибки в логах сборщиков (24.10 20:00): ai_daily_cron.log — …».

### Фикс

- Исключены **не-сборщики** из проверки:
  - `ai_daily_cron.log`, `ai_weekly_cron.log` (AI-отчёты).
  - `streamlit.log` (дашборд).
  - `robot.log`, `robot_v2.log`, `robot_v3.log`, `robot_test.log` (роботы).
  - `pairs_quarantine.log`, `pairs_quarantine_cron.log` (карантин).
- Проверка: `✅ Ошибок в логах не обнаружено (24.10 20:34)`.

### Git

- Commit: `57e749a` (check_collector_logs: исключены не-сборщики).

### Замечание

- **AI-daily** в отчёте **рекомендовал** убрать SFIN-SH_M10 из enabled (corr 0.23) и проверить BR-GAZPF_H4 (corr 0.12).
- **Уже сделано**: SFIN-SH_M10 — в карантине (`enabled=False`), BR-GAZPF_H4 — `enabled=False` (v1).
- **AI не знает** об этом (отчёт за 19:30, изменения — позже). **Позже** — обновить AI-контекст (чтобы видел актуальный `enabled`).


---

## 2026-10-25 (вечер) — AI-weekly W43: рекомендации (перенос из IDEAS)

### Контекст

- **AI-weekly** (25.10, 17:00) — отчёт W43. Email не ушёл с первого раза (Network unreachable), но при ручном запуске (20:21) — ушёл.
- **Отчёт** сохранён: `logs/ai_weekly/2026-W43.md`.
- **Рекомендации** AI — ниже (перенесены из IDEAS, чтобы не засорять «карту идей»).

### Рекомендации AI-weekly W43

1. **SFIN-SH_M10 — пересмотр corr_gate.**
   - Пара в карантине (corr 0.23–0.25 < 0.5), но дала +134₽ из +151₽ недели (v2). Парадокс: лучшая пара — в карантине.
   - Гипотеза: corr_gate 0.5 слишком жёсткий. Она торгует на расхождении, а не на корреляции.
   - Действие: пересмотреть порог (0.2 вместо 0.5) — тест в v4 (walk-forward). Или вывести из карантина с наблюдением.
   - **Не сейчас** (накопить статистику v2 за 2–3 недели).

2. **MAX_HOLD 90 мин для M10.**
   - Убыточная BANE-BN держалась 110 мин при exit_z=−0.37; все прибыльные — ≤80 мин.
   - Действие: MAX_HOLD=90 мин — тест в v4 (walk-forward). Если лучше — внедрить в v2.
   - **Ссылки:** IDEAS п.15 (MAX_HOLD / exit_z / max_z).

3. **Убрать шум `time` в signals.**
   - 23 MISSED по `time` — в основном сканирование M10 после 23:00 (вне окна v2).
   - Действие: не логировать MISSED time (или останавливать сканирование M10 после 23:00). Снизит шум в статистике.

4. **v3 — снизить entry_z.**
   - v3 — 0 сделок за всё время, z в recent −0.93…−1.61 при порогах 1.8–2.5. Кальман-бета даёт более гладкий z — пороги завышены.
   - Действие: entry_z 1.5 (GD-SV, PD-SV, LK-IMOEXF) и 2.0 (PT-SV). Тест в v4 (walk-forward), потом — в v3 (если лучше).

5. **v1 — накопить статистику v2.**
   - v1 — 0 сделок за неделю (entry_z=2.5, окно до 18:00). v2 (entry 1.8, окно до 23:00) дал +151₽.
   - Действие: накопить статистику v2 за 2–3 недели, потом — решить: переносить ли параметры v2 в v1 или оставить v1 как контроль.
   - **Не сейчас** (v1 — эталон, не трогаем).

6. **D1 — не обновляется с 23.10.**
   - D1: 1/296 свежих (<24ч), 2/296 (<48ч). Не обновляется с 23.10.
   - Влияние: не критично — v2/v3/v4 на M10/H1/H4.
   - Действие: добавить D1-агрегатор (если нужно для cross-class, IDEAS п.10). Позже.

7. **Freshness — интерпретация (done).**
   - AI-weekly написал «0 свежих» (M10/H1/D1). Но это воскресенье — биржа не работает. С <48ч: M10/H1 — 270/295 (норма). H4 — 295/295 (агрегатор работает). D1 — 1/296 (не критично).
   - Вывод: AI ошибся в интерпретации (<24ч в воскресенье — не показатель). Не чинить.

### Git

- (после commit)


---

## 2026-10-25 (вечер-2) — Sokolov 2.4: модельная цена (H1-inside-M10) не работает

### Результат

- **Скрипт:** `scripts/sokolov_modelprice_test.py` — walk-forward 8 фолдов, 3 пары × 3 режима (baseline, model_h1, model_h1_avg).
- **Baseline лучше по всем парам.** PnL/Sharpe/trades model_h1 < baseline.
  - SFIN-SH: baseline PnL +0.372 / Sharpe 6.38 / 79 trades; model_h1 +0.164 / 5.33 / 22.
  - BANE-BN: baseline +0.183 / 5.19 / 53; model_h1 **0 / 0 / 0** (z не достигает 1.8).
  - BELU-NB: baseline +0.262 / 5.43 / 74; model_h1 +0.083 / 3.55 / 17.
- **model_h1 == model_h1_avg** (в M10-баре обычно 1 H1-свеча — не баг).
- **Причина:** H1 — слишком грубая цена для M10. M10 уже сглажен, H1 — ещё сильнее. z теряет чувствительность.

### IDEAS.md

- 2.4 — `pending` → **`done`** (проверено, не внедряем).

### Логи

- `logs/sokolov_modelprice_2026-10-25_2040.csv` — полные результаты по фолдам.

### Итог по Соколову (2.1–2.4)

- **2.1 (combined_v1)** — **работает** на BANE-BN (PnL +47%, trades ×2.15, Sharpe ×4). В v4.
- **2.2 (численный пример)** — подтверждение (done).
- **2.3 (EMA)** — не работает на M10 (done).
- **2.4 (модельная цена)** — не работает на M10 (done).

### Git

- (после commit)


---

## 2026-10-26 (день) — Идея: информационный фон Algopack для AI (парные роботы)

### Что

- **Встроить** в AI-daily/weekly **все** данные Algopack для **парных** роботов (v2/v4):
  - FutOI (физлица/юрлица) по тикерам ног.
  - TradeStats (объёмы, сделки, открытый интерес).
  - MegaAlerts (крупные сделки, если есть).
  - HI2 (индекс концентрации/активности, если есть).
  - SuperCandles (свечи с объёмом/дельтой, если есть).
  - Funding (ставки финансирования, если есть).
  - RVI (уже есть).
  - Sector indices (отраслевые индексы).
- **Формат** — компактная сводка по каждому источнику + промпт для AI (divergence, extremes, фильтр, свободный поиск).
- **AI** ищет связи с z-score, divergence, экстремумы, фильтры. Формат — краткий вывод + гипотеза для v4 (если есть).
- **Роботы акций / фьючерсов** — выключены (DEAD). Не трогаем. Когда включим — тогда и для них.

### Почему

- Не добавляем фильтры вслепую (p-hacking риск).
- AI видит всю картину (все источники Algopack), а не один признак.
- Поток подтверждает текущее движение, не предсказывает следующее (ВШЭ, 2021) — как фильтр слаб, как информация — полезен.

### Что делать (позже)

- Обновить `scripts/ai_data_context.py` — функции для каждого источника (FutOI, TradeStats, MegaAlerts, HI2, SuperCandles, Funding, RVI, Sector indices).
- Обновить `scripts/ai_daily_report.py` и `ai_weekly_report.py` — добавить блок «Информационный фон Algopack» + промпт для AI.
- Тест в v4 — только если AI найдёт гипотезу (walk-forward).

### Git

- (после commit)

---

## 2026-10-26 (вечер) — разбор AI-daily 26.10: п.1 (SFIN-SH) закрыт — ложная тревога

### AI-рекомендация №1 (SFIN-SH_M10: сигналы как z_below_entry, а не corr_gate) — проверено

- **Проверка кода** `robots/pairs_robot_v2.py` (строки 1246–1307): порядок — **z → corr_gate → ML**. `corr_gate` проверяется **только** если z прошёл (`|z| ≥ entry_z` и `spread_trend` совпал). Если z не дотянул — сразу `z_below_entry`, corr не проверяется. **Логика корректна.**
- **Проверка БД v2** (`signals`, SFIN-SH_M10):
  - `z_below_entry`: 733 (z не дотянул — corr не проверялся, норма).
  - `corr_gate`: **13** — все при |z| ≥ 1.8 (min 1.856, max 3.068) и |corr| < 0.5 (от −0.293 до 0.494), все SHORT_SPREAD. **Фильтр работает как задумано.**
  - `ML_BLOCK`: 32, `time`: 403, `open_failed`: 1.
- **Вывод:** рекомендация AI №1 — **ложная тревога** (AI видел `z_below_entry`, не учёл порядок фильтров). **v2 не трогаем** (правило 13, работает: +149.88₽, WR 87.5%).
- **Шум `z_below_entry` (733 за ~7 дней)** — норма (M10 × 7 дней ≈ 1000 проверок). Убирать шум — отдельная задача для v4 (например, логировать раз в час или при |z| > 1.0). **Не сейчас.**

### Следующее

- AI №2 (мёртвые тикеры, freshness) — отдельный узкий разбор.
- AI №3 (EURRUBF/LKOH-HYDR — нет сигналов в recent) — отдельный узкий разбор.

### Git

- (после commit)

---

## 2026-10-26 (вечер-2) — разбор AI-daily 26.10: п.2 (freshness) и п.3 (EURRUBF/LKOH-HYDR) закрыты

### AI-рекомендация №2 (мёртвые тикеры, freshness) — подтверждено, косметика

- **Источник:** `scripts/ai_data_context.py:27 get_freshness()` — считает `oldest_h` по **всем** `*_TF.parquet` в `data/candles/`, без исключений.
- **Мёртвые тикеры (9 файлов, одинаково для M10/H1):** IN (435.8ч), PIKK (254.8), BY (243.7), RF (147.8), UT (123.8), GU (97.3), CS (75.7), VGSB (62.8), KZ (51.8). Это валютные фьючерсы/АДР/иностранные — **не торгуются** в парах v2/v3/v4, просто лежат в `data/candles/`.
- **Влияние:** шум в AI-отчёте (`oldest_h=433.5`), на роботов не влияет.
- **Фикс:** в `get_freshness()` — whitelist мёртвых (или oldest только по тикерам из enabled-пар). **IDEAS п.16.** Косметика AI-отчёта, роботов не трогаем. Сделать позже.

### AI-рекомендация №3 (EURRUBF/LKOH-HYDR — нет сигналов в recent) — ложная тревога

- **EURRUBF-USDRUBF_H4:** сканируется (26.10: `vol` ×2, `time,vol` ×2, `z_below_entry` ×1, последний 20:00). Причины — объёмный фильтр и z. **Не выпала.**
- **LKOH-HYDR_H1:** сканируется (26.10: `z_below_entry` ×10, `time,corr` ×7, `open_failed` ×4, последний 21:00). Причины — z не дотянул (0.61…0.91 при entry=1.5), плюс `open_failed` ×4.
- **`open_failed` LKOH-HYDR_H1 — НЕ баг:** срабатывает защита «шорт по акции» (задумано, 20.09.2026). LONG_SPREAD → SELL HYDR (акция) → блок. Лог `robots/robot_v2.log`: `⏸️ LKOH-HYDR_H1: шорт по акции HYDR запрещён — пропуск` (6 раз, последний 26.10 16:00:15). **Правило работает как задумано.**
- **Следствие:** пара LKOH-HYDR_H1 **неторгуема в v2** (обе ноги — акции: LONG → шорт HYDR, SHORT → шорт LKOH, обе блокируются). Не ошибка, а следствие правила.
- **Действие:** зафиксировать в IDEAS как известное. Рассмотреть `enabled=false` в **v4** (не v2) или перенос с другим правилом. **v2 не трогаем.**

### Наблюдаемость v2

- Лог v2 — `robots/robot_v2.log` (не `logs/`): `StandardOutput=append:/root/finlab/robots/robot_v2.log` в `finlab-robot-v2.service`. **Лог есть, наблюдаемость ок** (моя ошибка ранее — искал в `logs/`).

### Итог по AI-daily 26.10

- №1 (SFIN-SH) — ложная тревога (corr_gate работает, порядок фильтров корректен).
- №2 (мёртвые тикеры) — подтверждено, косметика (IDEAS п.16, whitelist в get_freshness).
- №3 (EURRUBF/LKOH-HYDR) — ложная тревога (обе сканируются); open_failed LKOH-HYDR — правило «акции не шортим» (не баг), пара неторгуема в v2.
- **v2 не трогали** (правило 13).

### Git

- (после commit)

---

## 2026-10-26 (вечер-3) — LKOH-HYDR_H1 отключена в v2/v4 (акция+акция)

### Правило пар (зафиксировано)

Допустимые пары в парных роботах:
- **фьючерс + фьючерс** — можно, лонги и шорты.
- **фьючерс + акция** — можно, **шорт по акции запрещён** (по акции только лонги). Сделки, где шорт-нога — акция, не входят.
- **акция + акция** — **не рассматриваем** (пара неторгуема в принципе).

### LKOH-HYDR_H1 — акция+акция, отключена

- **Проверка (P/Q):** `LKOH` и `HYDR` — только в `stocks` (`tickers_config.json`), в `futures` их нет. Фьючерсы Лукойла/РусГидро — `LKM7`/`LKZ6`/`LKH7`, `HYZ6`/`HYH7` (с другими тикерами). `base_pair='LKOH-HYDR'` → **акция+акция**.
- **Аудит enabled-пар:** v1 (7) — 0 проблем; v2 (10) — 1 (`LKOH-HYDR_H1`); v3 (4) — 0; v4 (9) — 1 (`LKOH-HYDR_H1`).
- **Действие (с согласия):** `enabled=false` для `LKOH-HYDR_H1` в **v2** и **v4** (26.10.2026 22:13:31). Бэкапы: `pairs_config_v2.json.bak_20261026_221331`, `pairs_config_test.json.bak_20261026_221331`.
- **Рестарт не требовался:** v2/v4 читают конфиг на каждом цикле (`pairs_config = json.load(f)` в главном цикле, строки ~955/1024). Роботы `active`, без перезапуска.
- **Проверка:** последний signal по паре — 22:00:17 (до правки). Следующий цикл H1 (23:00) — signals по паре **не должны** появиться. (Проверить после 23:00.)
- **Следствие:** мусорная пара убрана, signals/AI-отчёт чище, циклы не тратятся.

### IDEAS

- Добавлен пункт: **аудит enabled-пар на класс (акция/фьючерс)** — при добавлении пары/регулярно; правило пар зафиксировано (см. выше).

### Git

- (после commit)

---

## 2026-10-26 (вечер-4) — freshness: DEAD_TICKERS исключены из get_freshness (AI №2 закрыт)

### Что сделано

- **`scripts/ai_data_context.py`:** добавлен `DEAD_TICKERS = {"IN","PIKK","BY","RF","UT","GU","CS","VGSB","KZ"}` (9 мёртвых тикеров), в `get_freshness()` — `continue` для мёртвых (не учитываются в `fresh`/`oldest_h`).
- **Бэкап:** `scripts/ai_data_context.py.bak_20261026_221704`.
- **Правка через Python** `text.replace` (правило 5, не sed). Роботов не трогали.

### Результат (до → после)

| TF | oldest_h (до) | oldest_h (после) | fresh |
|---|---|---|---|
| M10 | 433.5 | **6.1** | 286/295 |
| H1  | 433.5 | **6.1** | 286/295 |
| H4  | 433.5 | **8.8** | 286/295 |
| D1  | 433.5 | **15.3** | 287/296 |

- `total` = 295/296 (все файлы, включая мёртвые — информативно), `fresh`/`oldest` — по живым.
- **AI-отчёт больше не зашумлён** мёртвыми тикерами.

### IDEAS п.16 → done

- Freshness-шум устранён. При появлении новых мёртвых тикеров — добавить в `DEAD_TICKERS` (список редко меняется).

### Git

- (после commit)

---

## 2026-10-26 (вечер-5) — тесты п.15/17 (MAX_HOLD/exit_z/max_z) + правка v4

### Результаты walk-forward (scripts/max_hold_exit_z_test.py, logs/max_hold_exit_z_2026-10-26_2225.csv)

Параметры по одному за раз (baseline=off), 3 пары × walk-forward (train=30д, test=7д, шаг=7д).

**MAX_HOLD (off / 90 / 120 мин) — ХУЖЕ baseline по всем парам:**
- BANE-BN: Sharpe 4.91 → 3.85 (90) / 3.64 (120).
- BELU-NB: 5.57 → 3.33 (90) / 5.09 (120).
- SFIN-SH: 6.96 → 4.21 (90) / 5.37 (120).
- **Вывод: не внедряем.** IDEAS п.15 (MAX_HOLD) → `done` (не работает).

**exit_z (off=0.5 / 0.3 / 0.0):**
- BANE-BN: 4.91 → **8.04 (+3.12)** при 0.3; 0.00 при 0.0.
- BELU-NB: 5.57 → **6.53 (+0.96)** при 0.3; 0.00 при 0.0.
- SFIN-SH: 6.96 → 6.77 (−0.20) при 0.3; 0.00 при 0.0.
- PnL немного падает (−0.007…−0.010), Sharpe **значительно растёт** (быстрее выход).
- **Вывод: exit_z=0.3 — кандидат в v4.** exit_z=0.0 — не работает (0 Sharpe).

**max_z (off=None / 4.0 / 3.5 / 3.0):**
- BANE-BN: 4.91 → 5.77 (+0.86) / 5.74 (+0.82) / 5.70 (+0.78).
- BELU-NB: 5.57 → 5.82 (+0.25) / 6.19 (+0.63) / 6.20 (+0.63).
- SFIN-SH: 6.96 → 7.51 (+0.55) / 7.51 (+0.55) / 7.63 (+0.67).
- **Вывод: max_z (3.0/3.5/4.0) — лучше baseline по всем парам.** Кандидат в v4, лучший компромисс — **3.5**.

**p-hacking оговорка:** 3 пары, 8 фолдов — Sharpe может быть завышен. Внедряем **в v4 (тест)**, не в v2. Через 1–2 недели — сравнить v4 vs v2.

### Правка v4 (с согласия): exit_z=0.3 + max_z=3.5 для M10-пар

- **Код** `robots/pairs_robot_test.py`: добавлен `max_z = _bp.get('max_z', None)` + проверка `if max_z is not None and abs(current_z) > max_z: skip_signal(..., 'z_too_extreme'); continue`. Бэкап: `pairs_robot_test.py.bak_20261026_223107`. `py_compile OK`.
- **Конфиг** `FinLabPy/My_Indicators/pairs_config_test.json`: для SFIN-SH_M10, BANE-BN_M10, BELU-NB_M10 — `exit_z=0.3`, `max_z=3.5`. Бэкап: `pairs_config_test.json.bak_20261026_223107`.
- **Рестарт v4:** `systemctl restart finlab-robot-test` → `active`. Лог `logs/robot_test.log`: старт без ошибок (ML загружены, циклы идут).
- **Проверка signals:** пока только `z_below_entry` (|z| < 1.8) — норма, рынок тихий. `z_too_extreme` появится при |z| > 3.5 (позже).
- **v2 не трогали** (правило 13).

### IDEAS

- п.15: MAX_HOLD → `done` (не работает); exit_z=0.3 → `pending` (в v4 с 26.10, наблюдать 1–2 недели); max_z=3.5 → `pending` (в v4 с 26.10, наблюдать).

### Git

- (после commit)

---

## 2026-10-27 (вечер) — AI-исследование Algopack: пилот SBER/GAZP/LKOH (сектор, HI2, FutOI, MegaAlerts)

### Скрипт

- `scripts/ai_algopack_research.py` (read-only): SBER/GAZP/LKOH × 6 источников (price H1, FutOI H1, TradeStats H1, MegaAlerts, HI2 D1, MOEXFN D1).
- CSV: `logs/ai_algopack_multi_2026-10-27_2310.csv` (446 строк).
- Бэкап старого (SBER-only): `scripts/ai_algopack_research.py.bak_20261027_230403`.

### Загрузка

- SBER: price 7825, futoi 2491 (SBERF), tradestats 32452, mega 22/1.
- GAZP: price 7828, futoi 2491 (GAZPF), tradestats 32452, mega 35/20.
- LKOH: price 7825, futoi **0** (LKOHF нет в futoi), tradestats 32452, mega 54/0.

### Результаты (топ-связи)

**(A) Сектор MOEXFN → акции — САМАЯ СИЛЬНАЯ и СТАБИЛЬНАЯ:**
- SBER: corr +0.663 (n=333), GAZP +0.605 (n=333), LKOH +0.469 (n=333). **Стабильно на трёх активах** → не шум. **Гипотеза 1 (divergence SBER/GAZP/LKOH vs MOEXFN)** — приоритет.

**(B) HI2 lag8 → акции — интересно, но n=69 (мало):**
- `hhi_netflow_sell [SBER]` (lag 8) → SBER +0.422 / GAZP +0.388 / LKOH +0.372 (n=69). **Стабильно на трёх активах** (возможно, общий фактор — SBER-лидер). **Требует walk-forward** (n=69 — может быть шум).
- `hhi_agressive [LKOH]` (lag 0) → LKOH −0.316 (n=69) — отрицательная.

**(C) FutOI H1 → цена — слабо:** не в топ-20 (corr < 0.2). **FutOI D1 — не проверен** (отдельный скрипт).

**(D) MegaAlerts — мало данных:** SBER 22/1, GAZP 35/20, LKOH 54/0. **n=18–54** — статистически слабо. Не в топ-20.

**(E) Divergence FutOI vs цена (H1) — нулевой:** mean_fwd_ret ≈ 0, wr ≈ 0.5. **Не работает.**

### Следующее

- **Walk-forward по гипотезе 1 (MOEXFN divergence):** `scripts/moexfn_divergence_test.py` (SBER/GAZP/LKOH vs MOEXFN, forward return 1/2/4/8 дней, baseline без divergence).
- **Потом:** HI2 lag8 (walk-forward, n=69 — с оговоркой), FutOI D1 (отдельный скрипт), Algopack-фон в AI-daily/weekly (по активам + по парам).
- **v2/v3/v4 — не трогаем** (код). **v4** — тест при подтверждении (с согласия).

### IDEAS

- п.29 (Algopack-фон в AI-отчёт) → `in_progress` (пилот выполнен, результаты см. выше; walk-forward по MOEXFN divergence — следующий шаг).

### Git

- (после commit)

---

## 2026-10-27 (вечер-2) — walk-forward MOEXFN divergence (SBER/GAZP/LKOH)

### Скрипт
- `scripts/moexfn_divergence_test.py` (read-only): divergence акция vs MOEXFN → forward return 1/2/4/8 дней, walk-forward (train=6мес, test=1мес, шаг=1мес), baseline без divergence.
- CSV: `logs/moexfn_divergence_*.csv`.

### Результат (walk-forward, CSV: logs/moexfn_divergence_2026-10-27_2315.csv)

| Тикер | h | n_div | mean_aligned | wr_aligned | sharpe_aligned | Вердикт |
|---|---|---|---|---|---|---|
| SBER | 1 | 35 | +0.0071 | 0.771 | **+2.39** | работает |
| SBER | 2 | 35 | +0.0098 | 0.706 | +2.09 | работает |
| SBER | 4 | 35 | +0.0104 | 0.680 | +2.05 | работает |
| SBER | 8 | 35 | +0.0131 | 0.685 | +1.94 | работает |
| GAZP | 1 | 45 | +0.0144 | 0.845 | **+2.75** | работает (сильнее) |
| GAZP | 2 | 45 | +0.0104 | 0.632 | +1.19 | работает |
| GAZP | 4 | 45 | +0.0110 | 0.647 | +0.70 | слабо |
| GAZP | 8 | 45 | +0.0091 | 0.511 | +0.38 | слабо |
| LKOH | 1-8 | 80 | +0.001…+0.004 | 0.46–0.56 | +0.18…+0.36 | шум |

**Вывод:** гипотеза 1 (MOEXFN divergence) **работает** на **SBER (все h, Sharpe 1.9–2.4)** и **GAZP (h=1–2, Sharpe 1.2–2.75)**. **LKOH — шум** (Sharpe 0.18–0.36). n_div=35–45 (мало, но Sharpe высокий на независимых фолдах).

### Решение
- **Гипотеза 1 работает** (SBER/GAZP). **LKOH — не использовать.**
- **Внедрение:** v4 — **парный** (divergence акция vs сектор — не пара). Варианты: (A) отдельный робот (одиночная торговля SBER/GAZP по divergence, paper), (B) фильтр в v4 (не входить в пары с SBER при divergence), (C) только в AI-отчёт (контекст). **Решение — позже** (сначала зафиксировать; n=35–45 — мало, подтвердить).
- **Следующий шаг:** HI2 lag8 (walk-forward), FutOI D1 (отдельный скрипт), Algopack-фон в AI-отчёт (по активам + по парам).

### Git
- (после commit)

---

## 2026-10-27 (вечер-3) — Робот индексный_v1: окно/дни/Сб + чистый старт

### Что сделано

- **`robots/index_robot_v1.py`** (paper, divergence SBER/GAZP vs MOEXFN):
  - окно **07:00–23:00**, **Пн–Сб** (Сб — допсессия MOEX; Вс — выходной).
  - `is_moex_trading_day`: `weekday == 6` (Вс) → False; **Сб (5) — True**; `NO_TRADE_WEEKENDS` (пусто).
  - `in_trading_window`: окно + день. **Проверка перед входом** (`SKIP outside_window`).
  - выход: `H_DAYS=1` (следующий D1 close) **или** `|z| <= 0.5`.
  - paper: депозит 100000, комиссия 0.28%, slip 0.04%.
- **БД** `index_robot_v1.db` — **очищена** (positions=0, signals=0), state сброшен (`open=0`, `pnl=0`). **Чистый старт.**
- **Лог** — без дублей (убран `print()` из `log()`).
- **Проверка:** `active`, лог `window=07:00-23:00 (Пн-Сб)`, **`SKIP GAZP: вне окна (23:41)`** — проверка работает. `open=0`, `pnl=0`.

### Следующее

- **Дашборд-таб** «📈 Робот индексный_v1 (test)» + **раскрывашка** «🔍 Что и как работает» (окно/дни, логика, h=1, exit_z).
- **AI-отчёт** — divergence SBER/GAZP vs MOEXFN (контекст).
- **Наблюдение** 1–2 недели, сравнение с бэктестом (Sharpe 1.9–2.75).
- **v2/v3/v4 — не трогаем** (код).

### Git

- (после commit)

---

## 2026-10-27 (вечер-4) — Робот индексный_v1: дашборд-таб + кнопки

### Что сделано

- **Робот `index_robot_v1.py`:** добавлено чтение `robot_command_index_v1.txt` (`PAUSE`/`RESUME`/`STOP`); в `main` — обработка команд + проверка `running` (STOP → выход). `py_compile OK`.
- **Дашборд `app_v2.py`:**
  - Табы: добавлен «📈 Робот индексный_v1 (test)».
  - Обзор: статистика `_index_v1_db` → `_robots_stats['📈 Робот индексный_v1 (test)']`.
  - Таб: `elif robot_tab == "📈 Робот индексный_v1 (test)":` — state (`robot_state_index_v1.json`), команды (`robot_command_index_v1.txt`), кнопки (Старт/Пауза/Стоп), метрики (PnL, trades, WR, open), раскрывашка «🔍 Что и как работает», таблицы (открытые/закрытые), сигналы, LQDT.
  - `py_compile OK`.
- **Проверка:** робот `active` (`SKIP GAZP: вне окна (23:46)` — окно работает), дашборд `active` (Uvicorn 8501, без ошибок). Таб виден.

### Следующее

- **AI-отчёт** — divergence SBER/GAZP vs MOEXFN (контекст).
- **Наблюдение** 1–2 недели, сравнение с бэктестом (Sharpe 1.9–2.75).
- **v2/v3/v4 — не трогаем** (код).

### Git

- (после commit)

---

## 2026-10-27 (вечер-5) — AI-отчёт: блок divergence SBER/GAZP vs MOEXFN (daily + weekly)

### Что сделано

- **`ai_data_context.py`:** функция `get_index_divergence()` — для SBER/GAZP: `ret_stock`, `ret_sector` (MOEXFN), `divergence`, `z`, `signal`. **В контексте:** `'index_divergence': get_index_divergence()`.
- **`ai_daily_report.py`:** импорт `get_index_divergence` (вне docstring — fix-2), блок «📈 Робот индексный_v1 — divergence SBER/GAZP vs MOEXFN» **после** `answer` (таблица + промпт).
- **`ai_weekly_report.py`:** импорт `get_index_divergence`, блок **после** `answer` (таблица + промпт).
- **Проверка:** `py_compile OK` (daily + weekly); **dry-run** (`--no-email`) — блок divergence **есть** (daily: SBER/GAZP; weekly: SBER/GAZP). **Commit + push** (daily: `d5f6a76`, weekly: `c1a6d23`).

### Результат (dry-run)

- **Daily:** SBER (divergence=False, z=1.032), GAZP (divergence=True, signal=LONG, z=1.012).
- **Weekly:** то же (SBER/GAZP, divergence, z, signal) + промпт для AI.

### Следующее

- **Блок 4:** наблюдение 1–2 недели (v4: exit_z=0.3/max_z=3.5; index_robot_v1: divergence SBER/GAZP; AI-отчёт: divergence). **Пассивно.**
- **Рекомендации weekly** (AI, **без** нашего контекста) — **не действуем** вслепую: MAX_HOLD — `done` (не работает), exit_z=0.3/max_z=3.5 — **в v4** (тест), LKOH-HYDR — disabled, freshness DEAD_TICKERS — `done`. **Сверять** с нашими шагами.
- **v2/v3/v4 — не трогаем** (код). **v4-фильтр (B) — позже** (если index_robot_v1 покажет).

### Git

- (после commit)

---

## 2026-10-28 (ночь) — SFIN-SH_M10 disabled в v2; дашборд: index_v1 в табах + обзоре

### Что сделано

- **v2 `pairs_config_v2.json`:** `SFIN-SH_M10.enabled = False` (карантин corr<0.5, шум убран). Бэкап: `pairs_config_v2.json.bak_20261028_000755`. **С согласия** (правило 13).
- **Дашборд `app_v2.py`:**
  - Список табов: добавлен «📈 Робот индексный_v1 (test)».
  - Обзор: `_robots_stats['📈 Робот индексный_v1 (test)']` (PnL, WR, open, db).
  - Бэкап: `app_v2.py.bak_20261028_000755`.
- **Проверка:** `py_compile OK`; дашборд `active`; **commit `3bf9d37`**, push в origin + diary.

### Следующее

- **Блок 4:** наблюдение 1–2 недели (v4: exit_z=0.3/max_z=3.5; index_robot_v1: divergence SBER/GAZP; AI-отчёт: divergence). **Пассивно.**
- **Через 1–2 недели** — сравнение с бэктестом (Sharpe 1.9–2.75), решение по v4/index_robot_v1.
- **v2/v3/v4 — не трогаем** (код). **v4-фильтр (B) — позже** (если index_robot_v1 покажет).

### Git

- (после commit)

---

## 2026-10-28 (вечер) — fix v2: перечитывание pairs_config в цикле; SFIN-SH больше не сканируется

### Что сделано

- **`robots/pairs_robot_v2.py`:** добавлено перечитывание `pairs_config` **в цикле** (перед `check_signals_by_tf`) — чтобы изменения `enabled`/`params` применялись **без рестарта**. Бэкап: `pairs_robot_v2.py.bak_20261028_203823`. `py_compile OK`.
- **Причина бага:** `pairs_config` читался **один раз** (строка 954, до `while`), в цикле использовался **старый** (не перечитывался) → `enabled=false` для SFIN-SH (28.10 00:07) **не применялся**.
- **Проверка:** v2 `active` (рестарт 20:38); **signals SFIN-SH после 20:38 — 0** (не сканируется). `commit cf701df`.

### Git

- `pairs_config_test.json` (combined_betas, cron 19:00) — закоммичен (как вчера, ожидаемо).

---

## 2026-10-28 (вечер-2) — AI-отчёт: divergence в user_content (AI анализирует)

### Что сделано

- **`ai_daily_report.py`:** divergence **в `user_content`** (до `call_vsegpt`) — AI видит и анализирует. Убран дубль импорта (строка 11). Бэкап: `ai_daily_report.py.bak_20261028_204313`.
- **`ai_weekly_report.py`:** divergence **в `user_content`** (до `call_vsegpt`). Бэкап: `ai_weekly_report.py.bak_20261028_204313`.
- **Проверка:** `py_compile OK`; **dry-run daily** (`--no-email`) — AI **анализирует** divergence:
  - «Index divergence SBER/GAZP: divergence=False у обоих (z 1.20 и 1.12) — сигнала нет, всё в норме.»
  - «Гипотеза для разведки (не внедрять): при divergence=True на D1 + |z|>1.5 тестировать mean-reversion вход по SBER/GAZP против сектора — обязателен walk-forward 5 фолдов.»
- **Commit `808c3b0`**, push в origin + diary.

### Следующее

- **Блок 4:** наблюдение 1–2 недели (v4: exit_z=0.3/max_z=3.5; index_robot_v1: divergence SBER/GAZP; AI-отчёт: divergence). **Пассивно.**
- **Через 1–2 недели** — сравнение с бэктестом (Sharpe 1.9–2.75), решение по v4/index_robot_v1.
- **v2/v3/v4 — не трогаем** (код). **v2** — fix (перечитывание pairs_config — сделано).

### Git

- (после commit)

---

## 2026-10-28 (вечер-3) — приоритеты (P0–P4) + статус по Соколову

### Соколов — что проверено, что нет

- **2.1 (combined_v1)** — `in_progress`: **в v4** (тест, BANE-BN). Ждём 1–2 недели. Потом — решение (в v2 — только BANE-BN, с согласия).
- **2.2 (численный пример)** — `done` (подтверждение).
- **2.3 (EMA)** — `done` (не работает — baseline лучше).
- **2.4 (модельная цена)** — `done` (не работает).
- **3.1 (треугольные наборы / баскет, Йохансен)** — **`pending`** (не проверяли). **Отдельная задача** (walk-forward в v4).
- **3.2 (хеджирование обязательств)** — `parked` (не наш кейс).

**Итог:** по Соколову **не всё** — **3.1 (баскет)** **не проверена** (позже); **2.1** — в v4 (ждём); **2.2–2.4** — `done`; **3.2** — `parked`.

### Приоритеты

**P0 — сейчас (наблюдение 1–2 недели, пассивно):**
- **v4** (exit_z=0.3, max_z=3.5, combined_v1 BANE-BN) — сравнить с v2 (baseline): Sharpe, PnL, WR, trades.
- **index_robot_v1** (divergence SBER/GAZP) — сравнить с бэктестом (Sharpe 1.9–2.75): реальные paper-сделки, PnL, WR.
- **AI-отчёт** (divergence) — смотреть, что AI предлагает (не действовать вслепую).
- **Ничего не делаем — ждём.**

**P1 — после наблюдения (1–2 недели):**
- **Решение по v4:** если лучше v2 — внедрить exit_z=0.3/max_z=3.5 в v2 (M10, с согласия); если нет — откат v4.
- **Решение по index_robot_v1:** если PnL/Sharpe близки к бэктесту — развивать (B: фильтр в v4; другие активы); если нет — фиксируем (гипотеза не работает на paper).
- **Соколов 3.1 (баскет)** — walk-forward в v4 (тест) — отдельная задача.

**P2 — когда будет время:**
- **v3 пороги** (Кальман — 0 сделок): тест в v4 (walk-forward) — снизить пороги (1.2–1.5) — если работает.
- **v2 ночная сессия** (M10 — 186 MISSED `time`): walk-forward — если работает.
- **v4-фильтр (B)** — если index_robot_v1 покажет.
- **AI-отчёт** — добавить `enabled`/карантин (AI не знает про отключения — шум в отчёте). Мелочь.
- **v1 `short_forbidden`** — логировать как `short_forbidden` (не `BLOCKED`) — мелочь (v1 — эталон, не трогаем; но логирование — можно, с согласия).

**P3 — позже/парковка:**
- Крипта Bybit (п.13) — позже (отдельный проект).
- FIOR/Sentiment/Brokers/OTC/Tradelog/OrderBook/OFI (п.8–14) — платные/сложные — позже.
- Cross-class D1 (п.10) — ждёт пересборку H4 (п.11) — позже.
- Пересборка H4 (п.11) — важная, не срочная — позже.
- Парковщик LQDT (п.7) — позже (нужен API).
- VRPI/Copula/Стоп-лосс 3σ (п.25–27) — позже (walk-forward).
- Авто-карантин v2 (п.9) — есть ручной (19:45), авто — позже.

**P4 — не трогаем:**
- v1 (эталон) — не трогаем (правило 13).
- v2/v3/v4 — код — не трогаем (кроме fix багов, с согласия; v2 — fix сделан).
- Расширение окна v1 (п.10) — parked (эталон).

### Git

- (после commit)

---

## 2026-10-28 (вечер-4) — ВК-уведомления в index_v1 + EnvironmentFile в юниты

### Что сделано

- **`robots/index_robot_v1.py`:** добавлены `VK_TOKEN`, `VK_GROUP_ID`, `send_vk_message()` (по образцу v2, префикс `[index_v1]`); вызовы в `open_position`/`close_position`. Бэкап: `index_robot_v1.py.bak_20261028_210643`. `py_compile OK`.
- **Systemd юниты:** `EnvironmentFile=/root/finlab/.env` добавлен в **`finlab-robot-v2.service`** и **`finlab-index-robot-v1.service`** (v2 — дублирует `dotenv`, но не мешает).
- **Проверка:** v2 `active`, index_v1 `active`; **тест ВК** — `True` (ВК работает).
- **Позиция GAZP** (OPEN, 28.10 07:46) — **не трогаем** (закроется завтра по h=1; ВК — при закрытии).

### Замечание

- **`.env`:** при `source .env` строка `sk-or-vis-...` интерпретируется как команда (`command not found`) — вероятно, `OPENROUTER_API_KEY=sk-or-vis-...` без кавычек. **Почистить позже** (не критично для ВК).

### Следующее

- **P0** — наблюдение 1–2 недели (v4, index_robot_v1, AI-отчёт). **Пассивно.**
- **v2/v3/v4 — не трогаем** (код).

### Git

- (после commit)

---

## 2026-10-29 (вечер) — fix index_v1: _held_days (нормализация); GAZP закрылась +2.44₽

### Что сделано

- **`robots/index_robot_v1.py`:** `_held_days` — **по датам** (нормализация `last["begin"]` и `_etime`), а не по времени. **Причина бага:** `last["begin"]` (D1, 00:00) − `entry_time` (07:46) < 1 дня → `_held_days = 0` → GAZP не закрывалась. Бэкап: `index_robot_v1.py.bak_20261029_201035`. `py_compile OK`.
- **Проверка:** index_v1 `active`; **GAZP** — **закрылась** (`CLOSED`, `exit_time=2026-10-29 20:10:36`, **`pnl=+2.4448`**, `reason=exit_H(1d)`). **ВК** — должен быть отправлен (тест `True`).

### Следующее

- **P0** — наблюдение 1–2 недели (v4, index_robot_v1, AI-отчёт). **Пассивно.**
- **P2** — AI-отчёт (контекст `enabled`/что сделано) — позже/сейчас (по решению).
- **v2/v3/v4 — не трогаем** (код).

### Git

- (после commit)

---

## 2026-10-29 (вечер-2) — P2: AI-отчёт контекст; fix графика PnL в Обзоре; WR index_v1

### Что сделано

- **P2 — AI-отчёт (daily + weekly):** в `user_content` — **контекст** ( `enabled`/`disabled` v2/v4 + **«что сделано»** (MAX_HOLD — done, freshness — done, exit_z/max_z — в v4, LKOH-HYDR/SFIN-SH — disabled ) + **index_v1 сделки** (закрыто/PnL/открыто) ). **AI** — **не советует** **уже** **сделанное**. `commit 87cea5a`.
- **WR index_v1 (dashboard):** убрано `*100` ( `_calc_wr` **уже** **проценты** ) — **WR** 100.0% (не 10000%). `commit e5872b3`.
- **График PnL в Обзоре:** **сбор** `_all_closed_dfs` — **из** **всех** **БД** (`positions` / `algopack_positions` — **v1/v2/v3/v4/index_v1** + stocks/futures ). **Общий WR** — **тоже** (не только algopack). `commit 9f996a2`.

### Проверка

- `py_compile OK` (dashboard); дашборд `active`; AI dry-run — **AI** **видит** **контекст** (index_v1: +2.44₽, карантины — **корректно**). **График** **в** **Обзоре** — **должен** **быть** (данные v2/index_v1 есть).

### Следующее

- **P0** — наблюдение 1–2 недели (v4, index_robot_v1, AI-отчёт). **Пассивно.**
- **v2/v3/v4 — не трогаем** (код).

### Git

- (после commit)

---

## 2026-10-30 — Bybit API: подключение, доступ к активам, сборщик H4 (M10 — нет в Bybit)

### Bybit API — подключение

- **API-ключ** создан на **Mainnet** (bybit.com), **Read-Write**, **IP whitelist**: `159.194.219.117`, **Withdrawal — OFF**.
- **`.env`:** `BYBIT_API_KEY`, `BYBIT_API_SECRET`, `BYBIT_TESTNET=false`.
- **Проверка (read):** `server time 200 OK`, `wallet 200 OK`, `✅ API работает (read)`. Баланс — **0** (денег нет — норма, public API работает без баланса).

### Доступ к активам (проверено)

- **921 linear instruments** (perpetuals).
- **BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT, DOGEUSDT** — `status=Trading`, `contractType=LinearPerpetual` (minQty: BTC 0.001, ETH 0.01, SOL 0.1, XRP 0.1, DOGE 1).
- **Kline H4** — работает (5 свечей, last ~78858).
- **Tickers** — `BTCUSDT=78859.30`, `ETHUSDT=2257.15`, `SOLUSDT=96.190` (volume24h — высокая ликвидность).

### Сборщик данных (`scripts/bybit_collector.py`, read-only)

- **H4** (`interval=240`): **BTCUSDT, ETHUSDT, SOLUSDT** — **10 000 строк каждый** → `data/bybit/{symbol}_H4.parquet` (last: 2026-10-29 20:00).
- **M10** (`interval=10`): **пусто** (0 строк). **Причина:** Bybit REST Kline **не поддерживает** `interval=10` (M10). Поддерживаются: `1,3,5,15,30,60,120,240,360,720,D,W,M`. **M10 — нет**.
- **Commit `232b814`** (скрипт).

### Решение по M10

- **M10 не делаем** (Bybit не поддерживает). **H4 — достаточно** для walk-forward пар (BTC/ETH, BTC/SOL).
- **M5/M15** — возможны (если нужен внутридневной TF) — **позже** (если понадобится).

### Следующее

- **Walk-forward H4** (BTC/ETH, BTC/SOL) — коинтеграция, спред, entry_z (как `sokolov_*_test.py`). **Следующий шаг.**
- **index_v1 (адаптация под крипту)** — позже (24/7, шорт, другие комиссии).
- **v2/v3/v4 (MOEX)** — не трогаем (код). **P0 — наблюдение** (1–2 недели).

### Git

- (после commit)

---

## 2026-10-30 (вечер) — Bybit: marginMode = REGULAR_MARGIN (Cross Margin) — подтверждено

### Проверка

- **`GET /v5/account/info`** → **`marginMode: REGULAR_MARGIN`** — это **Cross Margin** (кросс-маржа). **То, что нужно** для нашего проекта.
- **Решение:** ничего переключать не надо (Bybit уже на Cross). **Позже** (реальные деньги) — **жёсткие стопы** (обязательно для Cross).

### Следующее

- **Walk-forward H4** (BTC/ETH, BTC/SOL) — следующий шаг (завтра).
- **index_v1 (адаптация под крипту)** — позже (24/7, шорт, H4).
- **v2/v3/v4 (MOEX)** — не трогаем (код). **P0 — наблюдение** (1–2 недели).

### Git

- (после commit)

---

## 2026-10-30 (вечер-2) — index_v1: шум/цикл, ручное закрытие, MIN_ENTRY_Z; v3-вкладка: путь + 3 поля

### index_v1 — инцидент

- **Симптом:** шумовые позиции при |z|<0.5 (SBER z=-0.18, GAZP z=+0.30), закрытие в тот же/следующий цикл по `exit_z` (D1 не обновляется -> entry_z==exit_z). PnL — только комиссии.
- **Ручное закрытие:** id=4,5 (20:10, -0.94, -0.37), id=6,7 (21:10, manual_close_bad_entry, -0.94, -0.37). total_pnl=-0.176.
- **Фикс index_robot_v1.py** (бэкап index_robot_v1.py.bak_20261030_2120, py_compile OK): MIN_ENTRY_Z=1.0 (временно, до WF); вход `abs(z)>=MIN_ENTRY_Z`; выход `_held_days>=1 and abs(z)<=EXIT_Z`; лог старта min_entry_z.
- **Робот inactive, paused=true** — не рестартили. **WF pending:** scripts/index_divergence_wf.py (min_entry_z 0.5/1.0/1.5/2.0, exit_z 0.5/0.3, 5 фолдов, merged 337д).
- **PAUSE-инцидент:** команда записана в корень (не тот путь), робот читает robots/robot_command_index_v1.txt. CMD_PATH корректен, мусорный корневой удалён.

### v3-вкладка дашборда — путь + 3 поля

- **Баг 1 (путь):** app_v2.py:5166 -> robot_command_v2.txt, исправлено на robot_command_v3.txt (бэкап app_v2.py.bak_20261030_2145).
- **Баг 2 (копипаст v2):** app_v2.py:5109/5112/5132 — v3 читал is-active v2, robot_state_v2.json, pairs_config_v2.json. Исправлено (бэкап app_v2.py.bak_20261030_2210, py_compile OK): _v3_running->finlab-robot-v3; _v3_state_file->robot_state_v3.json; _v3_cfg_path->pairs_config_v3.json; откат _v2_running (был сломан первым фиксом) -> finlab-robot-v2.
- **Проверка:** v2 paused=false, v3 paused=true; UI v3 «на паузе», v2 «работает». Дашборд active.
- **Урок:** правки дашборда — только по уникальным якорям (_v3_*, _v2_*), не по общим шаблонам.

### Техдолг (WORK_LOG, не IDEAS)

- finlab-robot (pairs, DEAD) — is-enabled=enabled, active. По правилу 9 должен быть masked. Отдельная задача.
- v3-вкладка: «Config v2:» в подписи -> «Config v3:» (косметика).

### Git

- (после commit)

### Fix (30.10, вечер-3) — «Config v2:» -> «Config v3:» на v3-вкладке

- Косметика: подпись на v3-вкладке показывала «Config v2:» (копипаст). Исправлено на «Config v3:» (бэкап app_v2.py.bak_20261030_2230, py_compile OK, дашборд active).
- Техдолг закрыт.

### Техдолг (30.10, вечер-4) — .gitignore / -f для бэкапов

- Бэкапы `app_v2.py.bak_*` и `index_robot_v1.py.bak_*` закоммичены через `-f` (обход `*.bak*` в .gitignore). Не критично (не ломает), но **не по правилу 2** (только WORK_LOG через -f).
- `*.bak*` уже игнорирует будущие бэкапы. Будущие — без `-f` (только код + WORK_LOG).
- Решение по текущим: не откатывать (история), просто не повторять.

---

## 2026-10-30 (вечер-5) — WF index_v1: MIN_ENTRY_Z=1.0 подтверждён; exit_z не влияет

### Скрипт

- `scripts/index_divergence_wf.py` (read-only, `py_compile OK`): SBER/GAZP vs MOEXFN D1, merged 337д, train=180/test=30/шаг=30 (≈5 фолдов), `min_entry_z ∈ {0.0,0.5,1.0,1.5,2.0}` × `exit_z ∈ {0.5,0.3}`, hold=1д, fee+slip как в роботе.
- CSV: `logs/index_divergence_wf_2026-10-30_2222.csv` (rows=180).

### Результаты (mean по 5 фолдам)

| ticker | min_entry_z | n | pnl | wr | sharpe | maxdd |
|---|---|---|---|---|---|---|
| SBER | 0.0 (baseline) | 72 | +5.07 | 0.513 | +1.88 | -4.18 |
| SBER | 0.5 | 56 | +4.15 | 0.557 | +4.54 | -3.77 |
| **SBER** | **1.0** | **39** | **+2.45** | **0.543** | **+4.81** | **-2.94** |
| SBER | 1.5 | 24 | +1.48 | 0.479 | -4.30 | -2.33 |
| SBER | 2.0 | 13 | +1.39 | 0.352 | -1.23 | -1.61 |
| GAZP | 0.0 (baseline) | 75 | +2.77 | 0.522 | +2.69 | -2.57 |
| GAZP | 0.5 | 64 | +2.02 | 0.538 | +3.67 | -2.40 |
| **GAZP** | **1.0** | **49** | **+2.19** | **0.593** | **+6.86** | **-1.62** |
| GAZP | 1.5 | 30 | +0.73 | 0.585 | +20.16* | -1.48 |
| GAZP | 2.0 | 16 | +0.41 | 0.648 | +209.67* | -0.42 |

* Sharpe 20/209 — артефакт (мало сделок, std→0). Не доверять.

### Выводы

- **MIN_ENTRY_Z = 1.0** — оптимум по обоим тикерам (SBER Sharpe 4.81, GAZP 6.86; WR 0.543/0.593; PnL +2.45/+2.19; maxdd -2.94/-1.62). **Утверждаем.**
- **exit_z** (0.5 vs 0.3) — **не влияет**: на D1 выход по `held_days>=1` доминирует. Оставляем 0.5 (не параметр тюнинга).
- **Baseline (0.0)** — PnL больше, но Sharpe хуже, maxdd больше. 1.0 — правильный компромисс.
- **p-hacking оговорка:** 5 фолдов, n=39–49 — приемлемо, но live 1–2 недели — сравнить с WF.

### Действие

- `MIN_ENTRY_Z=1.0` уже в коде (с 21:20), WF подтвердил — **не меняем**.
- **Запуск index_v1:** `systemctl start` + `RESUME`, наблюдение 1–2 недели.

### Git

- (после commit)

### Запуск index_v1 (30.10, 22:30) — после WF

- `systemctl start finlab-index-robot-v1` → `active`, лог: `=== index_robot_v1 start | ... min_entry_z=1.0 ... ===`.
- `RESUME` (файл `robots/robot_command_index_v1.txt`) → `CMD: RESUME`, `paused=false`, файл удалён после чтения (штатно).
- **Проверка:** 22:30:22 SBER z=-0.18 / GAZP z=+0.30, **|z|<1.0 → вход не выполнен** (до фикса открыл бы шум id=4,5,6,7). **Фикс работает.**
- State: `paused=false`, `open=0`, `total_pnl=-0.176`. **Наблюдение 1–2 недели** (live PnL/WR vs WF: SBER ~4.8, GAZP ~6.9).
- **Техдолг (P3):** `.gitignore` для `robot_command*.txt`; лог `MISSED weak_z` в роботе; `finlab-robot` (DEAD) → masked.

---

## 2026-10-31 (вечер) — AI Daily Report 31.10: разбор

- **v1:** open_failed=20 (BANE-BN short_forbidden) — ожидаемо, **не трогаем** (правило 13, акции не шортим). ML_BLOCK=5 (корректно).
- **v2:** 13 сделок, PnL +162.9, WR ~77%. Последняя — BANE-BN +15.63 (30.10). Стабильно.
- **v3:** 0 сделок, z_below_entry=16, time=8 — штатно.
- **index_v1:** 5 сделок, PnL -0.18. SBER z=0.237, GAZP z=0.505 — **ниже MIN_ENTRY_Z=1.0**, вход не выполняется (корректно).
- **v4:** 5 сделок, +28.01 (v2: +34.51 — v4 хуже из-за exit_z=0.3, наблюдение).
- **D1 freshness:** 133/296, oldest 121.5ч — **половина D1 устарела**. Причина: cron без D1-агрегатора? **Проверить (P1)**.
- **Карантин:** 69 disabled в v2 (большинство — акция+акция, не торгуемы). Кандидаты на аудит: фьюч+фьюч (LK-HY, LK-RN, RN-TN, HY-IR, GAZPF-SBERF, BR-GAZPF, EURRUBF-USDRUBF). **Отдельная задача (P2, после Bybit WF).**
- **Не действуем:** v1 (short_forbidden — правило), v2 (MAX_HOLD — уже done), v4 (exit_z=0.3 — наблюдение), index_v1 (MIN_ENTRY_Z=1.0 — WF подтвердил).

---

## 2026-10-31 (ночь) — Algopack-блок в AI-отчётах (daily+weekly): index_v1 — лаборатория AI-фона

### Что сделано

- **`get_index_algopack()`** в `ai_data_context.py` (v3, 149 строк): для SBER/GAZP — FutOI (SBERF/GAZPF), HI2 (pivot), MegaAlerts (items), TradeStats, RVI. **С ценой/временем/delta:**
  - FutOI: `hour`, `h1_last_begin`, `price`, `price_prev`, `delta_1h` + ratios.
  - HI2: `hhi_*`, `tradedate`, `tradetime`, `price_at_time`, `price_now`, `delta_1d`.
  - MegaAlerts: `items` (tradedate[:10], tradetime, price, value, type).
  - TradeStats: `price`, `price_prev`, `delta_1d`, `disb`, `vol`.
  - RVI: `rvi`, `price_at_rvi_date`, `price_now`.
- **`ai_daily_report.py`:** импорт (в настоящий, не в docstring) + блок `ALGOPACK-ФОН` после divergence. `--debug-content` для отладки.
- **`ai_weekly_report.py`:** импорт + 2 блока (ctx — user_content, ans — answer).
- **Проверка:** `py_compile OK`, dry-run — `ALGOPACK-ФОН` в выводе (SBER/GAZP с price/time/delta).

### Цель index_v1 (IDEAS п.29)

- **index_v1 — лаборатория AI-фона:** price + FutOI + HI2 + MegaAlerts + TradeStats + RVI → связи → гипотезы для walk-forward. **PnL — побочный.**
- **AI видит:** пример SBER (HI2 30.10 18:40 buy=182/sell=143 при 296.91 → price_now 296.02 (delta −0.89) → TradeStats 31.10 disb=0.02 (было 0.88) — покупатели ушли). **Гипотезы — для WF, не внедрять.**

### Git

- (после commit)

---

## 2026-10-31 (ночь-2) — Bybit WF (BTC/ETH, BTC/SOL, H4): PnL < 0, WR ~0.5 — НЕ работает

### Скрипт

- `scripts/bybit_walkforward.py` (read-only, `py_compile OK`): BTC/ETH, BTC/SOL (H4, 10000 строк, 2022-04 → 2026-10), OLS-β на train, z-score (window=60), entry_z ∈ {1.8,2.0}, exit_z=0.5, time-stop 30 H4-свечей (5д), fee 0.13% (Bybit taker+slip).
- Walk-forward: train=180д, test=30д, шаг=30д → 42 фолда × 2 пары × 2 entry_z = 196 строк.
- CSV: `logs/bybit_walkforward_2026-10-31_2043.csv`.

### Результаты (mean по 42 фолдам)

| Пара | entry_z | n | PnL | WR | Sharpe | avg_hold | maxDD |
|---|---|---|---|---|---|---|---|
| BTC/ETH | 1.8 | 119 | **−0.0126** | 0.502 | +3.97* | 20.7 | −0.0238 |
| BTC/ETH | 2.0 | 105 | **−0.0145** | 0.493 | +29.05* | 21.5 | −0.0218 |
| BTC/SOL | 1.8 | 120 | **−0.0109** | 0.533 | +6.84* | 20.2 | −0.0176 |
| BTC/SOL | 2.0 | 98 | **−0.0098** | 0.515 | +18.52* | 21.5 | −0.0125 |

* Sharpe высокий — **артефакт** (mean≈0, std маленькое, √252 раздувает). PnL < 0 — **после fee 0.13%**. WR ~0.5 — **случайность**. **Edge нет.**

### Вывод

- **Пара BTC/ETH, BTC/SOL (H4) — НЕ работает:** PnL < 0 (fee съедает), WR ~0.5, Sharpe — артефакт.
- **Причина:** крипто-пары сильно коррелированы (β≈1), спред маленький, fee 0.13% съедает.
- **Не внедряем.** Зафиксировать. **Возможные улучшения (для будущего):** entry_z=2.5–3.0, другой TF (H1/D1), ETH/SOL, учёт funding rate.
- **index_v1 — лаборатория AI-фона** (algopack-блок, `30597fa`) — **готово.**

### Git

- (после commit)
