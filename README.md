# 📋 ПАСПОРТ FinLabPy — ДЛЯ AI-АССИСТЕНТА

## 📅 Актуально на: 07.07.2026

---

## 🔗 ДОСТУПЫ

- Локально: E:\Python\FinLabProject (Windows, Python 3.12, venv)
- Сервер: root@159.194.219.117 (Ubuntu 24.04, Python 3.12)
- VS Code Server: http://159.194.219.117:8080
- Токены: MOEX_TOKEN, TINVEST_TOKEN, ALOR_TOKEN

---

## 🎯 ИДЕОЛОГИЯ: ДЖИМ САЙМОНС / RENAISSANCE TECHNOLOGIES

Проект следует подходу Джима Саймонса:
- **Данные превыше всего.** Сбор и очистка рыночных данных — фундамент.
- **Математика, не фундамент.** Ищем статистически значимые сигналы в шуме.
- **Скрытые закономерности.** Не очевидные паттерны, а тонкие аномалии.
- **Сначала исследование, потом роботы.** Накапливаем данные, тестируем гипотезы.
- **Портфельный подход.** Множество некоррелированных сигналов одновременно.



---

## 📚 НАСТОЛЬНАЯ КНИГА ПРОЕКТА

**Грегори Цукерман — «Человек, который разгадал рынок»**
Приватный репозиторий: [finlab-book-simons](https://github.com/ArchakovBullet/finlab-book-simons)


## 🚨 ПРАВИЛА РАБОТЫ (ИЗ RULES.MD)

- Обращение: Напарник
- Язык: весь код, комментарии, документация — строго на РУССКОМ
- Данные: polars основная библиотека, pandas только для backtrader
- Логирование: FinLabPy.Utils.setup_logger
- Новый сборщик: код + cron + check_collectors_health.py + vk_bot.py + запись в WORK_LOG
- Код: все изменения локально через PowerShell, сервер только pull и диагностика

---

## 🚨 GIT WORKFLOW

- Код (FinLabPy): локально -> git push -> сервер git pull
- Дашборд (finlab-dashboard): сервер -> git push, потом локально git pull
- Дневник (finlab-diary): локально -> git push из E:\Python\FinLabProjectinlab-diary
- ЗАПРЕЩЕНО: редактировать код на сервере
- ПОРЯДОК: сначала пушим сервер, потом локально!

---

## 📦 API MOEXPy (Algopack)

Фьючерсы:
  candles = api.get_candles('RFUD', 'GLDRUBF', dt_from, dt_till, tf)
  futoi = api.get_futoi('GLDRUBF', dt_from, dt_till)

Акции:
  candles = api.get_candles('TQBR', 'SBER', dt_from, dt_till, 'D')
  trades = api.get_trades('TQBR', 'SBER', tradeno=None)
  hi2 = api.get_hi2('stocks', 'SBER', date)

Вечные фьючерсы: GLDRUBF, IMOEXF, SBERF, GAZPF, CNYRUBF, USDRUBF, EURRUBF
Срочные фьючерсы: автоопределение полного кода через MOEX API (по SECTYPE)

---

## ⚠️ КРИТИЧЕСКИЕ ОСОБЕННОСТИ

- FutOI: pos_short с минусом -> abs(), clgroup='FIZ'/'YUR', API отдаёт 3-4 дня
- Свечи акций: MOEX отдаёт только M10, нет D1
- HI2: engine='stocks' (не 'stock'!)
- Срочные фьючерсы: коды автоопределяются через _find_active_contract()
- HI2-штраф в unified_verdict: >500 -> -15, >150 -> -10, >70 -> -5

---

## 📁 СТРУКТУРА ПРОЕКТА (сервер)

/root/finlab/
  FinLabPy/
    DataCollectors/    # Сборщики (cron)
    My_Indicators/     # Индикаторы (unified_verdict.py, garch_indicator.py)
    Strategies/        # Стратегии
    Utils/             # Утилиты
  finlab_dashboard/
    app_v2.py          # Дашборд
  data/                # Parquet-хранилище (futoi, candles, hi2, tradestats)
  RULES.md             # Правила для AI-ассистента
  vk_bot.py            # VK-бот
