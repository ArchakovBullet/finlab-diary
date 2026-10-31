#!/usr/bin/env python3
"""
bybit_walkforward.py — walk-forward тест пар BTC/ETH, BTC/SOL (H4).
Read-only. v2/v3/v4 не трогает. Пишет CSV в logs/.

OLS-β на train, z-score (rolling window=60), entry_z 2.5/3.0, exit_z=0.5, time-stop 30 H4-свечей (5 дней).
Walk-forward: train=180д, test=30д, шаг=30д (≈42 фолда на 10000 H4 ≈ 4.5 года).
Fee: Bybit taker 0.055%*2 + slip 0.01%*2 = 0.13%.
"""
import os
import numpy as np
import pandas as pd
import statsmodels.api as sm
from datetime import datetime

ROOT = "/root/finlab"
OUT_DIR = os.path.join(ROOT, "logs")
PAIRS = [("BTCUSDT", "ETHUSDT"), ("BTCUSDT", "SOLUSDT"), ("ETHUSDT", "SOLUSDT")]
WINDOW = 60
ENTRY_Z_GRID = [2.5, 3.0]
EXIT_Z = 0.5
TIME_STOP_BARS = 30
FEE = 0.0013
TRAIN_D = 180
TEST_D = 30
STEP_D = 30

def load_h4(ticker):
    p = os.path.join(ROOT, "data", "bybit", f"{ticker}_H4.parquet")
    if not os.path.exists(p): return None
    df = pd.read_parquet(p)[["begin","close"]].copy()
    df["begin"] = pd.to_datetime(df["begin"], errors="coerce")
    return df.dropna().sort_values("begin").reset_index(drop=True)

def merge_pair(a, b):
    da = load_h4(a)
    db = load_h4(b)
    if da is None or db is None: return None
    m = pd.merge(da, db, on="begin", suffixes=("_a","_b")).sort_values("begin").reset_index(drop=True)
    m["la"] = np.log(m["close_a"].replace(0, np.nan))
    m["lb"] = np.log(m["close_b"].replace(0, np.nan))
    return m.dropna(subset=["la","lb"]).reset_index(drop=True)

def ols_beta(train):
    x = sm.add_constant(train["lb"].values)
    y = train["la"].values
    res = sm.OLS(y, x).fit()
    return float(res.params[1])

def simulate(test, beta, entry_z, exit_z, window=WINDOW):
    if len(test) < window + 2: return []
    spread = test["la"] - beta * test["lb"]
    mu = spread.rolling(window).mean()
    sd = spread.rolling(window).std()
    z = (spread - mu) / sd
    trades = []
    pos = 0
    entry_i = 0
    entry_price = 0
    for i in range(window, len(test)):
        if pd.isna(z.iloc[i]): continue
        if pos == 0:
            if z.iloc[i] >= entry_z:
                pos = -1; entry_i = i; entry_price = spread.iloc[i]
            elif z.iloc[i] <= -entry_z:
                pos = 1; entry_i = i; entry_price = spread.iloc[i]
        else:
            held = i - entry_i
            if held >= TIME_STOP_BARS or abs(z.iloc[i]) <= exit_z:
                pnl = (spread.iloc[i] - entry_price) * pos - FEE
                trades.append({"pnl": pnl, "held": held, "entry_z": float(z.iloc[entry_i]), "exit_z": float(z.iloc[i])})
                pos = 0
    return trades

def stats(trades):
    if not trades:
        return {"n": 0, "pnl": 0.0, "wr": 0.0, "sharpe": 0.0, "avg": 0.0, "avg_hold": 0.0, "maxdd": 0.0}
    t = np.array([tr["pnl"] for tr in trades])
    cum = np.cumsum(t)
    peak = np.maximum.accumulate(cum)
    dd = cum - peak
    return {"n": len(t), "pnl": float(t.sum()), "wr": float((t > 0).mean()),
            "sharpe": float(t.mean() / t.std() * np.sqrt(252 * 6)) if t.std() > 0 else 0.0,
            "avg": float(t.mean()), "avg_hold": float(np.mean([tr["held"] for tr in trades])),
            "maxdd": float(dd.min()) if len(dd) else 0.0}

def walk_forward(a, b):
    m = merge_pair(a, b)
    if m is None or len(m) < 100: return []
    rows = []
    start = m["begin"].min(); end = m["begin"].max()
    t0 = start; fold = 0
    while t0 + pd.Timedelta(days=TRAIN_D + TEST_D) <= end:
        tr_start = t0
        tr_end = t0 + pd.Timedelta(days=TRAIN_D)
        te_start = tr_end
        te_end = te_start + pd.Timedelta(days=TEST_D)
        train = m[(m.begin >= tr_start) & (m.begin < tr_end)].reset_index(drop=True)
        test = m[(m.begin >= te_start) & (m.begin < te_end)].reset_index(drop=True)
        fold += 1
        if len(train) < 50 or len(test) < 20:
            t0 += pd.Timedelta(days=STEP_D); continue
        beta = ols_beta(train)
        for ez in ENTRY_Z_GRID:
            trs = simulate(test, beta, ez, EXIT_Z)
            s = stats(trs)
            rows.append({"pair": f"{a}/{b}", "fold": fold, "entry_z": ez, **s})
        t0 += pd.Timedelta(days=STEP_D)
    return rows

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    all_rows = []
    for a, b in PAIRS:
        print(f"=== {a}/{b} ===")
        rows = walk_forward(a, b)
        all_rows.extend(rows)
    if not all_rows:
        print("Нет данных."); return
    out = pd.DataFrame(all_rows)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    path = os.path.join(OUT_DIR, f"bybit_walkforward_{ts}.csv")
    out.to_csv(path, index=False)
    print("Сохранено:", path, "(rows=" + str(len(out)) + ")")
    print("=== Сводка: pair x entry_z (mean по фолдам) ===")
    agg = out.groupby(["pair","entry_z"]).agg(
        n=("n","sum"), pnl=("pnl","mean"), wr=("wr","mean"),
        sharpe=("sharpe","mean"), avg_hold=("avg_hold","mean"),
        maxdd=("maxdd","mean"), folds=("fold","count")).reset_index()
    for p in agg["pair"].unique():
        sub = agg[agg.pair == p]
        print("---", p, "---")
        for _, r in sub.iterrows():
            print(f"  entry_z={r['entry_z']}: n={int(r['n'])} pnl={r['pnl']:+.4f} wr={r['wr']:.3f} sharpe={r['sharpe']:+.2f} avg_hold={r['avg_hold']:.1f} maxdd={r['maxdd']:+.4f}")

if __name__ == "__main__":
    main()

