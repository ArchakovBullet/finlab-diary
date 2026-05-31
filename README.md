# ?? ДНЕВНИК РАЗРАБОТКИ FinLabPy

## ?? Последнее обновление: 29.05.2026

---


## ?? ТЕКУЩИЙ СТАТУС ПРОЕКТА

### Что работает:

* ? **FutOI сборщик** — 5 фьючерсов, cron каждый час
* ? **HI2 сборщик** — 10 тикеров, cron раз в день
* ? **FutOI стратегия** — сигналы BUY/SELL на основе позиций физиков
* ? **Данные OsEngine** — 10 инструментов, до 943 дней истории
* ? **Дашборд v0.2** — веб-интерфейс для мониторинга
* ? **VK-бот** — уведомления о смене тренда, ежедневные отчёты
* ? **TradeStats** — расчёт статистики сделок
* ? **Volume Profile** — POC, Value Area, уровни поддержки/сопротивления
* ? **Вердикт v3.2** — система оценки рыночной ситуации

### Что в процессе:

* ? **ML на FutOI** — ждём 60+ дней данных (конец июня 2026)
* ? **HI2 накопление** — начато 10.05, нужно 60+ дней
* ? **FMFS-скоринг** — спроектирован, реализация зависит от накопления данных (GARCH, фандинг)
* ? **Уровни из Volume Profile** — замена high_20/low_20 на POC/VA, спроектировано
* ? **Индикатор дисбаланса на Super Candles** — спроектировано
* ? **Zweig Filter** — предохранители для блокировки входа, спроектировано
* ? **Фандинг на FutOI** — сбор данных, спроектировано
* ? **Панель корреляций (акции - фьючерсы)** — спроектировано

### Что отложено:

* ? **HMM на дневках** — не даёт контрастных режимов
* ? **SuperTrend/HMM комбо** — не оправдало себя

### Новые инструменты (интегрированы):

* ?? **Continue** — AI-ассистент в VS Code (установлен, API DeepSeek получен)
* ?? **GARCH** — модель волатильности (спроектирована для дашборда и Zweig Filter)
* ?? **FMFS (FinLab Microstructure Factor Scoring)** — единый скоринговый механизм, аналог Validea (спроектирован)

---

## ?? КЛЮЧЕВЫЕ ССЫЛКИ

### Репозитории:

* **Код стратегий:** [finlab-strategies-local](https://github.com/ArchakovBullet/finlab-strategies-local)
* **Данные FutOI:** [futoi-data](https://github.com/ArchakovBullet/futoi-data)
* **Данные HI2:** [hi2-data](https://github.com/ArchakovBullet/hi2-data)
* **Данные Super Candles (H4):** [supercandles-h4-data](https://github.com/ArchakovBullet/supercandles-h4-data)
* **Дневник разработки:** [finlab-diary](https://github.com/ArchakovBullet/finlab-diary)

### Инфраструктура:

* **Сервер:** 
oot@159.194.219.117`n* **VS Code Server:** [http://159.194.219.117:8080](http://159.194.219.117:8080)








---

### ?? Стратегия развития проекта

**Дашборд — лаборатория сигналов.**  
Все сигналы (вердикт, шорт-анализ, GARCH, FMFS-скоринг, ML-модели) сначала обкатываются и тестируются в дашборде на реальных данных.

**Поэтапное расширение:**
1. Базовые сигналы (FutOI + Volume Profile) ?
2. Шорт-анализ ?
3. GARCH (волатильность)
4. FMFS-скоринг (аналог Validea)
5. ML-модели (после накопления 60+ дней FutOI)

**Интеграция в роботов — финальный этап.**  
Только после подтверждения эффективности на истории и в дашборде сигналы переносятся в алгоритмических роботов для реальной биржевой торговли.

> ?? *Дашборд = тестовая среда. Стратегии = production. Никакой преждевременной интеграции.*





### ?? Структура проекта

FinLabProject/
- FinLabPy/ — код стратегий (синхронизирован локально + сервер)
  - My_Indicators/ — short_signal.py, futoi_indicator.py, futoi_ml_filter.py
  - Strategies/ — 5 стратегий (SBERF, GAZPF, GLDRUBF, IMOEXF, CNYRUBF)
  - DataCollectors/ — сборщики данных
- finlab_dashboard/ — дашборд (ТОЛЬКО на сервере)
  - в отдельном репозитории: finlab-dashboard
  - app_v2.py — актуальная версия с шорт-анализом
- finlab-diary/ — дневник (подмодуль Git)

Репозитории GitHub:
- finlab-strategies-local (код)
- futoi-data, hi2-data, funding-data, candles-data, supercandles-data, supercandles-h4-data, tradestats-data (данные)
- finlab-infrastructure (конфиги)
- finlab-diary (дневник)

Сервер (159.194.219.117):
- /root/finlab/FinLabPy/ — код
- /root/finlab/finlab_dashboard/ — дашборд
- /root/finlab/data/ — данные
- /root/finlab/logs/ — логи
- :8501 — Streamlit, :8080 — VS Code Server



---






---

## ?? Контекст для AI-ассистента (DeepSeek / Continue)

### Источники данных
Проект использует **Algopack** (API MOEX) как основной источник рыночных данных:
- **Super Candles (D1)** — дневные свечи с агрегированной статистикой сделок (pr_open/high/low/close, vol_b, vol_s, count_b, count_s, hi2_score)
- **Super Candles H4** — 4-часовые свечи (агрегируются из минутных)
- **HI2** — индикатор институциональной активности (Herfindahl-Hirschman Index)
- **TradeStats** — статистика сделок (объёмы покупок/продаж, количество сделок)
- **FutOI** — открытый интерес по фьючерсам (физики/юрики)
- **Funding** — ставки фандинга

Пути к данным (сервер): /root/finlab/data/{tradestats,hi2,futoi,funding,supercandles,supercandles_h4}/

### Ключевые пути (сервер)
| Компонент | Путь |
|-----------|------|
| Код FinLabPy | /root/finlab/FinLabPy/ |
| Дашборд | /root/finlab/finlab_dashboard/app_v2.py |
| Данные | /root/finlab/data/ |
| Логи | /root/finlab/logs/ |
| Виртуальное окружение | /root/finlab/venv/ |
| VK-бот | /root/finlab/vk_bot.py |

### Ключевые пути (локально)
| Компонент | Путь |
|-----------|------|
| Корень проекта | E:\Python\FinLabProject\ |
| Код FinLabPy | E:\Python\FinLabProject\FinLabPy\ |
| Дашборд (локальная копия) | E:\Python\FinLabProject\finlab_dashboard\ |
| Дневник | E:\Python\FinLabProject\finlab-diary\ |

### Алгопак-модули (My_Indicators/)
- garch_indicator.py — GARCH(1,1): годовая волатильность, тренд, прогноз на 5 дней
- market_aggression.py — коэффициент агрессивности рынка (0–100) на основе TradeStats
- robot_classifier.py — классификация алгоритмов (HFT/VWAP/Iceberg/Институциональные) на основе HI2
- cross_market.py — кросс-рыночный анализ: корреляция, Z-score спреда, сигналы (подтверждает/противоречит)
- short_signal.py — сигналы для шорта
- futoi_indicator.py — индикатор на основе позиций физиков/юриков

### Дашборд (вкладки)
FutOI -> Trade Stats -> Объёмы -> Super Candles -> Super Candles H4 -> Funding -> Вердикт -> Корреляции -> Алгопак (GARCH, агрессивность, классификация, кросс-рынок)

### Соглашения
- Правка дашборда: только на сервере -> git push -> локально git pull
- Правка модулей: локально -> git push -> сервер git pull
- Логирование: loguru во всех модулях
- Cron: ежедневная агрегация в 17:35-17:45 МСК
- Данные: parquet-файлы, partitioned по датам

### Частые команды для диагностики (сервер)
- Активация окружения: cd /root/finlab && source venv/bin/activate
- Логи Super Candles: ls -la /root/finlab/logs/ | grep supercandle
- Cron: crontab -l
- Статус дашборда: ps aux | grep streamlit

### Быстрые ссылки
- Дашборд: http://159.194.219.117:8501
- VS Code Server: http://159.194.219.117:8080
- Дневник (актуальный): https://github.com/ArchakovBullet/finlab-diary/blob/main/README.md

---
*Последнее обновление: 31.05.2026*

## 31.05.2026 — FUTOI 1H, Super Candles fixes, дашборд

### Реализовано
- ? **FUTOI 1H сборщик** — агрегация 5-минутных FutOI в 1-часовые свечи
  - Модуль: FinLabPy/DataCollectors/futoi_1h_aggregator.py
  - Данные: /root/finlab/data/futoi_1h/futoi_1h.parquet
  - 5 тикеров (CNYRUBF, GAZPF, GLDRUBF, IMOEXF, SBERF)
  - Период: 28.04.2026 — 31.05.2026, 2120 строк
  - Cron: каждый час в :05
  - Репозиторий: utoi-1h-data
- ? **Вкладка FUTOI_1H в дашборде** — часовая аналитика позиций физиков/юриков
  - График ratio (физ/юр % покупателей)
  - График дельты за 1 час
  - Таблица последних записей
  - Выбор тикера
- ? **Super Candles fix** — исправлен missing return в load_supercandles_data()
- ? **Super Candles H4 fix** — показывает последний файл вместо первого (files[-1])
- ? **Дневник** — добавлен блок "Контекст для AI-ассистента" (Algopack, пути, модули, соглашения)

### Исправлено
- load_supercandles_data() не возвращала данные > TypeError на вкладке Super Candles
- Super Candles H4 показывал старый файл (11 мая) вместо актуального

### Git / инфраструктура
- Исправлен remote в корне проекта (указывал на finlab-dashboard вместо finlab-strategies-local)
- Подмодуль finlab-diary обновлён
- Настроен git credentials на сервере

### Следующие шаги
- Бэктест шорт-сигнала на истории
- Доработка рисков (ГО)
- Улучшение макета дашборда (вердикт наверх, "что делать")

---
