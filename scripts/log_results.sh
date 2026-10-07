#!/bin/bash
LOG=/root/finlab/WORK_LOG.md
cat >> "$LOG" << 'EOF_MD'

## 07.10.2026 (ночная сессия — итог: сигналов на фьючерсах нет)

### Что проверено (10+ тестов)

| Сигнал | Sharpe | n | Работает? |
|--------|--------|---|-----------|
| Baseline D1 (V_close) | +0.095 | 466 | ❌ close недостижим |
| Baseline D1 (V_morning) | −0.062 | 466 | ❌ |
| Baseline M10 (HOLD=30) | −0.215 | 93963 | ❌ |
| Baseline H1 (HOLD=30) | −0.105 | 14125 | ❌ |
| DMI-cross (на ценах) | 0.078 | 145 | ❌ |
| Force-cross (на ценах) | 0.054 | 179 | ❌ |
| SuperTrend (стратегия, D1) | −0.043 | 126 | ❌ |
| MegaAlerts direction | ~0 | 55 | ❌ мало данных |
| Filter gap V4 (close) | +0.120 | 87 | ⚠️ n мало |

### Единственные с Sharpe > 0.15 (но нестабильны)

- **DMI+ST+WillR+Force (Algopack)** — Sharpe 0.557, n=26. **Переобучение** (train/test 0.739→0.139).
- **FutOI** — Sharpe 0.251, n=98. **Нестабилен** (fold 4-5 в минусе).
- **FutOI+SuperTrend** — Sharpe 0.242, n=67.
- **C (DMI-cross + Force-state на Algopack)** — Sharpe 0.163, n=96. **Один фолд в минусе.**

### Выводы

1. **Baseline — артефакт close.** Работает ТОЛЬКО на V_close. Не торгуемый.
2. **SuperTrend, DMI, Force, MegaAlerts, M10/H1** — не работают.
3. **FutOI, C (DMI-cross+Force на Algopack)** — единственные с Sharpe >0.15, но **нестабильны**.
4. **На фьючерсах — сигнала нет.**

### Что дальше

- **Переключиться на акции** (там данных в 6 раз больше).
- **MegaAlerts** — 1603 события, в основном акции.
- **HI2** — 216 тикеров, в основном акции.
- **Не форсировать** фьючерсы.
- **v1/v2/stocks** — остановлены + disabled (07.10.2026 03:50).

### Технические фиксы

- **sshd:** добавлен `/etc/ssh/sshd_config.d/99-keepalive.conf` (ClientAliveInterval 60).
- **SuperTrend:** исправлен NaN-баг (start с первого не-NaN ATR).
- **v3-копия:** удалена (была на невалидном сигнале).

### На следующий раз

- [ ] Переключиться на акции: MegaAlerts direction на stocks.
- [ ] HI2 в комбинации на stocks.
- [ ] TradeStats stocks — расширить с 10 до 49 акций.
- [ ] Проверить sshd (ClientAliveInterval 60 применился?).
- [ ] Накопить данные за 3-6 месяцев.
EOF_MD
echo "Записано в WORK_LOG"
wc -l "$LOG"
