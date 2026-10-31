#!/usr/bin/env python3
"""
btc_atr_expansion_wf.py — walk-forward ATR Expansion (BTCUSDT H1, 2 года).
Read-only. v2/v3/v4 не трогает. Пишет CSV в logs/.

Логика (публично валидирована, out-of-sample PF 1.61, 9/9 режимов положительны):
- Long: бар > 2.5×ATR(14) + close > open (bullish) + close > H4 EMA200
- Short: бар > 2.5×ATR(14) + close < open (bearish) + close < H4 EMA200
- Exit: SL 1×ATR, TP 6×ATR, time stop 120 H1-баров
- Fee: 0.13% (Bybit taker+slip)
- Walk-forward: train=180д, test=30д, шаг=30д (18 фолдов на 2 года H1)
"""
import os
import numpy as np
import pandas as pd
from datetime import datetime

ROOT = "/root/finlab"
OUT_DIR = os.path.join(ROOT, "logs")
H1_PATH = os.path.join(ROOT, "data", "bybit", "BTCUSDT_H1.parquet")
H4_PATH = os.path.join(ROOT, "data", "bybit", "BTCUSDT_H4.parquet")
ATR_WIN = 14
ATR_MULT = 2.5
SL_ATR = 1.0
TP_ATR = 6.0
TIME_STOP = 120
FEE_PCT = 0.13  # 0.13% на сделку (taker+slip)
TRAIN_D = 180
TEST_D = 30
STEP_D = 30

def load(path):
    df = pd.read_parquet(path)[["begin","open","high","low","close","volume"]].copy()
    df["begin"] = pd.to_datetime(df["begin"], errors="coerce")
    return df.dropna().sort_values("begin").reset_index(drop=True)

def add_indicators(h1, h4):
    # H4 EMA200
    h4 = h4.copy()
    h4["ema200"] = h4["close"].ewm(span=200, adjust=False).mean()
    h1 = pd.merge_asof(h1.sort_values("begin"), h4[["begin","ema200"]].sort_values("begin"), on="begin", direction="backward")
    # ATR(14) на H1
    h1["tr"] = np.maximum(h1["high"] - h1["low"], np.maximum((h1["high"] - h1["close"].shift()).abs(), (h1["low"] - h1["close"].shift()).abs()))
    h1["atr"] = h1["tr"].ewm(alpha=1/ATR_WIN, adjust=False).mean()
    return h1

def simulate(df, fee_pct=FEE_PCT):
    pos = 0
    entry = 0.0
    entry_i = 0
    sl = 0.0
    tp = 0.0
    trades = []
    for i in range(1, len(df)):
        r = df.iloc[i]
        if any(pd.isna(r[c]) for c in ["ema200","atr"]):
            continue
        if pos == 0:
            bar_range = r["high"] - r["low"]
            atr_ok = bar_range > ATR_MULT * r["atr"]
            bullish = r["close"] > r["open"]
            bearish = r["close"] < r["open"]
            long_ok = atr_ok and bullish and (r["close"] > r["ema200"])
            short_ok = atr_ok and bearish and (r["close"] < r["ema200"])
            if long_ok:
                pos = 1; entry = r["close"]; entry_i = i
                sl = entry - SL_ATR * r["atr"]; tp = entry + TP_ATR * r["atr"]
            elif short_ok:
                pos = -1; entry = r["close"]; entry_i = i
                sl = entry + SL_ATR * r["atr"]; tp = entry - TP_ATR * r["atr"]
        else:
            held = i - entry_i
            exit_price = None
            if pos == 1:
                if r["low"] <= sl: exit_price = sl
                elif r["high"] >= tp: exit_price = tp
            else:
                if r["high"] >= sl: exit_price = sl
                elif r["low"] <= tp: exit_price = tp
            if exit_price is None and held >= TIME_STOP:
                exit_price = r["close"]
            if exit_price is not None:
                pnl_pct = ((exit_price - entry) / entry * 100.0 * pos) - fee_pct
                trades.append({"pnl_pct": pnl_pct, "held": held, "entry_i": entry_i, "exit_i": i})
                pos = 0
    return trades

def stats(trades):
    if not trades:
        return {"n": 0, "pnl_pct": 0.0, "wr": 0.0, "pf": 0.0, "sharpe": 0.0, "maxdd": 0.0, "avg_hold": 0.0}
    t = np.array([tr["pnl_pct"] for tr in trades])
    gross_p = t[t > 0].sum()
    gross_l = -t[t < 0].sum()
    pf = float(gross_p / gross_l) if gross_l > 0 else 0.0
    cum = np.cumsum(t)
    peak = np.maximum.accumulate(cum)
    dd = cum - peak
    return {"n": len(t), "pnl_pct": float(t.sum()), "wr": float((t > 0).mean()),
            "pf": pf,
            "sharpe": float(t.mean() / t.std() * np.sqrt(252 * 24)) if t.std() > 0 else 0.0,
            "maxdd": float(dd.min()) if len(dd) else 0.0,
            "avg_hold": float(np.mean([tr["held"] for tr in trades]))}

def walk_forward(df):
    rows = []
    start = df["begin"].min(); end = df["begin"].max()
    t0 = start; fold = 0
    while t0 + pd.Timedelta(days=TRAIN_D + TEST_D) <= end:
        te_start = t0 + pd.Timedelta(days=TRAIN_D)
        te_end = te_start + pd.Timedelta(days=TEST_D)
        test = df[(df.begin >= te_start) & (df.begin < te_end)].reset_index(drop=True)
        fold += 1
        if len(test) < 100:
            t0 += pd.Timedelta(days=STEP_D); continue
        trs = simulate(test)
        s = stats(trs)
        rows.append({"fold": fold, **s})
        t0 += pd.Timedelta(days=STEP_D)
    return rows

def main():
    h1 = load(H1_PATH)
    h4 = load(H4_PATH)
    print(f"H1: {len(h1)} rows ({h1['begin'].iloc[0]} -> {h1['begin'].iloc[-1]})")
    print(f"H4: {len(h4)} rows ({h4['begin'].iloc[0]} -> {h4['begin'].iloc[-1]})")
    df = add_indicators(h1, h4)
    rows = walk_forward(df)
    if not rows:
        print("Нет данных."); return
    out = pd.DataFrame(rows)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    path = os.path.join(OUT_DIR, f"btc_atr_expansion_wf_{ts}.csv")
    out.to_csv(path, index=False)
    print(f"\nСохранено: {path} (rows={len(out)})")
    print("\n=== Сводка (mean по фолдам) ===")
    print(f"  folds={len(out)} n={int(out['n'].sum())} pnl_pct={out['pnl_pct'].mean():+.4f} "
          f"wr={out['wr'].mean():.3f} pf={out['pf'].mean():.2f} "
          f"sharpe={out['sharpe'].mean():+.2f} maxdd_pct={out['maxdd'].mean():+.4f} "
          f"avg_hold={out['avg_hold'].mean():.1f}")
    for _, r in out.iterrows():
        print(f"  fold{int(r['fold'])}: n={int(r['n'])} pnl_pct={r['pnl_pct']:+.4f} wr={r['wr']:.3f} pf={r['pf']:.2f} sharpe={r['sharpe']:+.2f}")

if __name__ == "__main__":
    main()

