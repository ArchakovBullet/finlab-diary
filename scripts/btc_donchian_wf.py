#!/usr/bin/env python3
"""
btc_donchian_wf.py — walk-forward Donchian-55 (BTCUSDT H1, 2 года).
Read-only. v2/v3/v4 не трогает. Пишет CSV в logs/.

Логика (публично валидирована, out-of-sample PF 1.59):
- Long: close(H1) > 55-bar high + close > D1 EMA200 + H4 BB width(20,2σ) <= 0.109 + H4 RSI(14) >= 52
- Short: close(H1) < 55-bar low + close < D1 EMA200 + H4 BB width <= 0.109 + H4 RSI(14) <= 48
- Exit: SL 1×ATR(14,H1), TP 10×ATR(14,H1), time stop 240 H1-баров (10 дней)
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
DONCHIAN = 55
BB_WIN = 20
BB_WIDTH_MAX = 0.109
RSI_WIN = 14
RSI_LONG = 52
RSI_SHORT = 48
ATR_WIN = 14
SL_ATR = 1.0
TP_ATR = 10.0
TIME_STOP = 240
FEE = 0.0013
TRAIN_D = 180
TEST_D = 30
STEP_D = 30

def load(path):
    df = pd.read_parquet(path)[["begin","open","high","low","close","volume"]].copy()
    df["begin"] = pd.to_datetime(df["begin"], errors="coerce")
    return df.dropna().sort_values("begin").reset_index(drop=True)

def add_indicators(h1, h4):
    # D1 EMA200
    h1["date"] = h1["begin"].dt.normalize()
    d1 = h1.groupby("date")["close"].last().reset_index()
    d1["ema200"] = d1["close"].ewm(span=200, adjust=False).mean()
    h1 = h1.merge(d1[["date","ema200"]], on="date", how="left")
    # H4 BB width + RSI
    h4 = h4.copy()
    h4["bb_mid"] = h4["close"].rolling(BB_WIN).mean()
    h4["bb_std"] = h4["close"].rolling(BB_WIN).std()
    h4["bb_width"] = (h4["bb_std"] * 2) / h4["bb_mid"]
    delta = h4["close"].diff()
    gain = delta.clip(lower=0).ewm(alpha=1/RSI_WIN, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/RSI_WIN, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    h4["rsi"] = 100 - 100 / (1 + rs)
    # merge_asof H4 -> H1
    h1 = pd.merge_asof(h1.sort_values("begin"), h4[["begin","bb_width","rsi"]].sort_values("begin"), on="begin", direction="backward")
    # Donchian-55 (на H1)
    h1["don_hi"] = h1["high"].rolling(DONCHIAN).max().shift(1)
    h1["don_lo"] = h1["low"].rolling(DONCHIAN).min().shift(1)
    # ATR(14)
    h1["tr"] = np.maximum(h1["high"] - h1["low"], np.maximum((h1["high"] - h1["close"].shift()).abs(), (h1["low"] - h1["close"].shift()).abs()))
    h1["atr"] = h1["tr"].ewm(alpha=1/ATR_WIN, adjust=False).mean()
    return h1

def simulate(df, fee=FEE):
    pos = 0
    entry = 0.0
    entry_i = 0
    sl = 0.0
    tp = 0.0
    trades = []
    for i in range(1, len(df)):
        r = df.iloc[i]
        if any(pd.isna(r[c]) for c in ["don_hi","don_lo","ema200","bb_width","rsi","atr"]):
            continue
        if pos == 0:
            long_ok = (r["close"] > r["don_hi"]) and (r["close"] > r["ema200"]) and (r["bb_width"] <= BB_WIDTH_MAX) and (r["rsi"] >= RSI_LONG)
            short_ok = (r["close"] < r["don_lo"]) and (r["close"] < r["ema200"]) and (r["bb_width"] <= BB_WIDTH_MAX) and (r["rsi"] <= RSI_SHORT)
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
                pnl = (exit_price - entry) * pos - FEE * entry
                trades.append({"pnl": pnl, "held": held, "entry_i": entry_i, "exit_i": i})
                pos = 0
    return trades

def stats(trades):
    if not trades:
        return {"n": 0, "pnl": 0.0, "wr": 0.0, "pf": 0.0, "sharpe": 0.0, "maxdd": 0.0, "avg_hold": 0.0}
    t = np.array([tr["pnl"] for tr in trades])
    gross_p = t[t > 0].sum()
    gross_l = -t[t < 0].sum()
    pf = float(gross_p / gross_l) if gross_l > 0 else 0.0
    cum = np.cumsum(t)
    peak = np.maximum.accumulate(cum)
    dd = cum - peak
    return {"n": len(t), "pnl": float(t.sum()), "wr": float((t > 0).mean()),
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
    path = os.path.join(OUT_DIR, f"btc_donchian_wf_{ts}.csv")
    out.to_csv(path, index=False)
    print(f"\nСохранено: {path} (rows={len(out)})")
    print("\n=== Сводка (mean по фолдам) ===")
    print(f"  folds={len(out)} n={int(out['n'].sum())} pnl={out['pnl'].mean():+.4f} "
          f"wr={out['wr'].mean():.3f} pf={out['pf'].mean():.2f} "
          f"sharpe={out['sharpe'].mean():+.2f} maxdd={out['maxdd'].mean():+.4f} "
          f"avg_hold={out['avg_hold'].mean():.1f}")
    for _, r in out.iterrows():
        print(f"  fold{int(r['fold'])}: n={int(r['n'])} pnl={r['pnl']:+.4f} wr={r['wr']:.3f} pf={r['pf']:.2f} sharpe={r['sharpe']:+.2f}")

if __name__ == "__main__":
    main()

