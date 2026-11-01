#!/usr/bin/env python3
"""
funding_paper_sim.py — симуляция funding-арбитража (BTCUSDT, Bybit, paper).
Read-only. Не торгует. Вход при 3 положительных подряд, выход при отрицательном.
Считает PnL: накопленный funding - fee (0.13%).
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
FEE_PCT = 0.13
MIN_CONSECUTIVE_POSITIVE = 3

def fetch_funding(symbol, limit=200):
    r = requests.get("https://api.bybit.com/v5/market/funding/history",
                     params={"category": "linear", "symbol": symbol, "limit": limit}, timeout=20)
    j = r.json()
    if j.get("retCode") != 0:
        return None
    lst = j.get("result", {}).get("list", [])
    if not lst:
        return None
    df = pd.DataFrame(lst)
    df["ts"] = pd.to_datetime(df["fundingRateTimestamp"].astype("int64"), unit="ms", utc=True).dt.tz_convert(None)
    df["rate"] = pd.to_numeric(df["fundingRate"], errors="coerce")
    df = df[["ts", "rate"]].dropna().sort_values("ts").reset_index(drop=True)
    return df

def simulate(df):
    """Вход при 3 положительных подряд, выход при отрицательном. PnL = sum(rate) - fee."""
    trades = []
    pos = 0
    entry_i = 0
    funding_sum = 0.0
    for i in range(MIN_CONSECUTIVE_POSITIVE, len(df)):
        if pos == 0:
            last3 = df["rate"].iloc[i-MIN_CONSECUTIVE_POSITIVE:i+1]
            if (last3 > 0).all():
                pos = 1; entry_i = i; funding_sum = 0.0
        else:
            funding_sum += df["rate"].iloc[i]
            if df["rate"].iloc[i] < 0:
                pnl_pct = funding_sum * 100.0 - FEE_PCT
                trades.append({"entry_ts": df["ts"].iloc[entry_i], "exit_ts": df["ts"].iloc[i],
                               "funding_pct": funding_sum * 100.0, "pnl_pct": pnl_pct,
                               "held_bars": i - entry_i})
                pos = 0
    return trades

def stats(trades):
    if not trades:
        return {"n": 0, "pnl_pct": 0.0, "wr": 0.0, "avg_hold": 0.0}
    t = np.array([tr["pnl_pct"] for tr in trades])
    return {"n": len(t), "pnl_pct": float(t.sum()), "wr": float((t > 0).mean()),
            "avg_hold": float(np.mean([tr["held_bars"] for tr in trades]))}

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    df = fetch_funding(SYMBOL, limit=200)
    if df is None or len(df) == 0:
        print("Нет данных"); return
    print(f"=== {SYMBOL} funding (200 записей, {df['ts'].iloc[0]} -> {df['ts'].iloc[-1]}) ===")
    trades = simulate(df)
    s = stats(trades)
    print(f"\nСимуляция: n={s['n']} pnl_pct={s['pnl_pct']:+.4f}% wr={s['wr']:.3f} avg_hold={s['avg_hold']:.1f} bars")
    for tr in trades:
        print(f"  {tr['entry_ts']} -> {tr['exit_ts']}: funding={tr['funding_pct']:+.4f}% pnl={tr['pnl_pct']:+.4f}% held={tr['held_bars']} bars")
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    path = os.path.join(OUT_DIR, f"funding_paper_sim_{ts}.csv")
    pd.DataFrame(trades).to_csv(path, index=False)
    print(f"\nСохранено: {path}")

if __name__ == "__main__":
    main()
