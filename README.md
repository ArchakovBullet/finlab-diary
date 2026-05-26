# 📋 ДНЕВНИК РАЗРАБОТКИ FinLabPy

## 📅 Последнее обновление: 26.05.2026

---


## 📊 ТЕКУЩИЙ СТАТУС ПРОЕКТА

### Что работает:

* ✅ **FutOI сборщик** — 5 фьючерсов, cron каждый час
* ✅ **HI2 сборщик** — 10 тикеров, cron раз в день
* ✅ **FutOI стратегия** — сигналы BUY/SELL на основе позиций физиков
* ✅ **Данные OsEngine** — 10 инструментов, до 943 дней истории
* ✅ **Дашборд v0.2** — веб-интерфейс для мониторинга
* ✅ **VK-бот** — уведомления о смене тренда, ежедневные отчёты
* ✅ **TradeStats** — расчёт статистики сделок
* ✅ **Volume Profile** — POC, Value Area, уровни поддержки/сопротивления
* ✅ **Вердикт v3.2** — система оценки рыночной ситуации

### Что в процессе:

* ⏳ **ML на FutOI** — ждём 60+ дней данных (конец июня 2026)
* ⏳ **HI2 накопление** — начато 10.05, нужно 60+ дней
* ⏳ **FMFS-скоринг** — спроектирован, реализация зависит от накопления данных (GARCH, фандинг)
* ⏳ **Уровни из Volume Profile** — замена high_20/low_20 на POC/VA, спроектировано
* ⏳ **Индикатор дисбаланса на Super Candles** — спроектировано
* ⏳ **Zweig Filter** — предохранители для блокировки входа, спроектировано
* ⏳ **Фандинг на FutOI** — сбор данных, спроектировано
* ⏳ **Панель корреляций (акции ↔ фьючерсы)** — спроектировано

### Что отложено:

* ❌ **HMM на дневках** — не даёт контрастных режимов
* ❌ **SuperTrend/HMM комбо** — не оправдало себя

### Новые инструменты (интегрированы):

* 🆕 **Continue** — AI-ассистент в VS Code (установлен, API DeepSeek получен)
* 🆕 **GARCH** — модель волатильности (спроектирована для дашборда и Zweig Filter)
* 🆕 **FMFS (FinLab Microstructure Factor Scoring)** — единый скоринговый механизм, аналог Validea (спроектирован)

---

## 🔗 КЛЮЧЕВЫЕ ССЫЛКИ

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

### 🎯 Стратегия развития проекта

**Дашборд — лаборатория сигналов.**  
Все сигналы (вердикт, шорт-анализ, GARCH, FMFS-скоринг, ML-модели) сначала обкатываются и тестируются в дашборде на реальных данных.

**Поэтапное расширение:**
1. Базовые сигналы (FutOI + Volume Profile) ✅
2. Шорт-анализ ✅
3. GARCH (волатильность)
4. FMFS-скоринг (аналог Validea)
5. ML-модели (после накопления 60+ дней FutOI)

**Интеграция в роботов — финальный этап.**  
Только после подтверждения эффективности на истории и в дашборде сигналы переносятся в алгоритмических роботов для реальной биржевой торговли.

> 📌 *Дашборд = тестовая среда. Стратегии = production. Никакой преждевременной интеграции.*





### 📁 Структура проекта

FinLabProject/
- FinLabPy/ — код стратегий (синхронизирован локально + сервер)
  - My_Indicators/ — short_signal.py, futoi_indicator.py, futoi_ml_filter.py
  - Strategies/ — 5 стратегий (SBERF, GAZPF, GLDRUBF, IMOEXF, CNYRUBF)
  - DataCollectors/ — сборщики данных
- finlab_dashboard/ — дашборд (ТОЛЬКО на сервере)
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



