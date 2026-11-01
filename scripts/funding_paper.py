#!/usr/bin/env python3
"""
funding_paper.py — paper-пилот funding rate arbitrage (BTCUSDT, Bybit).
Read-only. Не торгует. Симулирует дельта-нейтральную позицию (лонг спот + шорт перп).
Пишет CSV в logs/.
"""
import os
import requests
import numpy as np
import pandas as pd
from datetime import datetime

ROOT = "/root/finlab"
OUT_DIR = os.path.join(ROOT, "logs")
SYMBOL = "BTCUSDT"
FEE_PCT = 0.13  # Bybit taker+slip (вход+выход)
MIN_CONSECUTIVE_POSITIVE = 3  # 3 funding подряд положительных — вход
EXIT_ON_NEGATIVE = True  # выходить при отрицательном funding

def fetch_current_funding(symbol):
    """Текущий funding rate (последние 3 записи)."""
    r = requests.get("https://api.bybit.com/v5/market/funding/history",
                     params={"category": "linear", "symbol": symbol, "limit": 3}, timeout=10)
    j = r.json()
    if j.get("retCode") != 0:
        return None
    lst = j.get("result", {}).get("list", [])
    if not lst:
        return None
    return [{"ts": pd.to_datetime(int(x["fundingRateTimestamp"]), unit="ms", utc=True).tz_convert(None),
             "rate": float(x["fundingRate"])} for x in lst]

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    hist = fetch_current_funding(SYMBOL)
    if not hist:
        print("Нет данных funding"); return
    # последние 3 (по убыванию — перевернуть)
    hist = sorted(hist, key=lambda x: x["ts"])
    print(f"=== {SYMBOL} funding (последние 3) ===")
    for h in hist:
        print(f"  {h['ts']}: {h['rate']*100:.4f}%")
    # проверка: 3 подряд положительных?
    positive_count = sum(1 for h in hist if h["rate"] > 0)
    mean_rate = np.mean([h["rate"] for h in hist])
    print(f"\nПоложительных: {positive_count}/3, средний: {mean_rate*100:.4f}%")
    if positive_count >= MIN_CONSECUTIVE_POSITIVE:
        daily = mean_rate * 3 * 100  # 3 funding/день, в %
        payback = FEE_PCT / daily if daily > 0 else 999
        print(f"\n✅ СИГНАЛ: 3 положительных funding подряд")
        print(f"   daily funding: {daily:.4f}%/день")
        print(f"   окупаемость fee (0.13%): {payback:.1f} дней")
        print(f"   РЕКОМЕНДАЦИЯ: открыть дельта-нейтральную позицию (лонг спот + шорт перп)")
    else:
        print(f"\n❌ НЕТ СИГНАЛА: {positive_count}/3 положительных (нужно 3)")
    # запись в CSV
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    path = os.path.join(OUT_DIR, f"funding_paper_{ts}.csv")
    pd.DataFrame(hist).to_csv(path, index=False)
    print(f"\nСохранено: {path}")

if __name__ == "__main__":
    main()
