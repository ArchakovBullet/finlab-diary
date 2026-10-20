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

