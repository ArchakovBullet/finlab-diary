#!/usr/bin/env python3
"""
h4_exit_z_wf.py — WF для exit_z (0.5/0.3) и wait_z0 на H4-парах (GD-SV, PD-SV, PT-SV, GD-PT).
Read-only. v2/v3/v4 не трогает. Пишет CSV в logs/.
look-ahead исправлен (i+1), PnL — exp(spread_diff)-1.
"""
import os
import numpy as np
import pandas as pd
import statsmodels.api as sm
from datetime import datetime

ROOT = "/root/finlab"
CANDLES = os.path.join(ROOT, "data", "candles")
OUT_DIR = os.path.join(ROOT, "logs")
PAIRS = [("GD", "SV"), ("PD", "SV"), ("PT", "SV"), ("GD", "PT")]
WINDOW = 20
ENTRY_Z = 2.0
EXIT_Z_GRID = [0.5, 0.3]
WAIT_Z0 = [False, True]
FEE_PCT_GRID = [0.28, 0.14]
TRAIN_D = 30
TEST_D = 7
STEP_D = 7
TIME_STOP = 30  # H4: 30 баров = 5 дней

def load_pair(a, b, tf="H4"):
    fa = os.path.join(CANDLES, f"{a}_{tf}.parquet")
    fb = os.path.join(CANDLES, f"{b}_{tf}.parquet")
    if not os.path.exists(fa) or not os.path.exists(fb):
        return None
    da = pd.read_parquet(fa)
    db = pd.read_parquet(fb)
    ca = "begin" if "begin" in da.columns else ("tradedate" if "tradedate" in da.columns else None)
    cb = "begin" if "begin" in db.columns else ("tradedate" if "tradedate" in db.columns else None)
    if ca is None or cb is None:
        return None
    da = da[[ca, "open", "close"]].rename(columns={ca: "dt"})
    db = db[[cb, "open", "close"]].rename(columns={cb: "dt"})
    m = pd.merge(da, db, on="dt", suffixes=("_a", "_b")).dropna()
    m["dt"] = pd.to_datetime(m["dt"], errors="coerce")
    m = m.dropna(subset=["dt"]).sort_values("dt").reset_index(drop=True)
    return m

def ols_beta(train):
    x = sm.add_constant(train["lb"].values)
    y = train["la"].values
    res = sm.OLS(y, x).fit()
    return float(res.params[1])

def simulate(test, beta, exit_z, wait_z0, fee_pct, window=WINDOW):
    if len(test) < window + 2: return []
    spread = test["la"] - beta * test["lb"]
    mu = spread.rolling(window).mean()
    sd = spread.rolling(window).std()
    z = (spread - mu) / sd
    trades = []
    pos = 0
    entry_i = 0
    entry_price = 0
    for i in range(window, len(test) - 1):
        if pd.isna(z.iloc[i]): continue
        if pos == 0:
            if z.iloc[i] >= ENTRY_Z:
                pos = -1; entry_i = i + 1; entry_price = spread.iloc[i + 1]
            elif z.iloc[i] <= -ENTRY_Z:
                pos = 1; entry_i = i + 1; entry_price = spread.iloc[i + 1]
        else:
            held = i - entry_i + 1
            close = False
            z_val = z.iloc[i]
            if held >= TIME_STOP:
                close = True
            elif abs(z_val) <= exit_z:
                close = True
            if close:
                if i + 1 >= len(test): break
                a_entry = test.iloc[entry_i]["open_a"]
                b_entry = test.iloc[entry_i]["open_b"]
                a_exit = test.iloc[i + 1]["open_a"]
                b_exit = test.iloc[i + 1]["open_b"]
                ratio_a = a_exit / a_entry
                ratio_b = b_exit / b_entry
                if pos == 1:
                    pnl = (ratio_a) / (ratio_b ** beta) - 1.0
                else:
                    pnl = (ratio_b ** beta) / (ratio_a) - 1.0
                pnl_pct = pnl * 100.0 - fee_pct
                trades.append({"pnl_pct": pnl_pct, "held": held, "entry_z": float(z.iloc[entry_i - 1]), "exit_z": float(z_val)})
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
    sharpe = float(t.mean() / t.std() * np.sqrt(252 * 6)) if (t.std() > 0 and len(t) >= 10) else None
    return {"n": len(t), "pnl_pct": float(t.sum()), "wr": float((t > 0).mean()),
            "pf": pf,
            "sharpe": sharpe,
            "maxdd": float(dd.min()) if len(dd) else 0.0,
            "avg_hold": float(np.mean([tr["held"] for tr in trades]))}

def walk_forward(a, b):
    m = load_pair(a, b)
    if m is None or len(m) < 200: return []
    m["la"] = np.log(m["close_a"].replace(0, np.nan))
    m["lb"] = np.log(m["close_b"].replace(0, np.nan))
    m = m.dropna(subset=["la","lb"]).reset_index(drop=True)
    rows = []
    start = m["dt"].min(); end = m["dt"].max()
    t0 = start; fold = 0
    while t0 + pd.Timedelta(days=TRAIN_D + TEST_D) <= end:
        te_start = t0 + pd.Timedelta(days=TRAIN_D)
        te_end = te_start + pd.Timedelta(days=TEST_D)
        train = m[(m.dt >= t0) & (m.dt < te_start)].reset_index(drop=True)
        test = m[(m.dt >= te_start) & (m.dt < te_end)].reset_index(drop=True)
        fold += 1
        if len(train) < 100 or len(test) < 30:
            t0 += pd.Timedelta(days=STEP_D); continue
        beta = ols_beta(train)
        for ez in EXIT_Z_GRID:
            for wait in WAIT_Z0:
                for fee in FEE_PCT_GRID:
                    trs = simulate(test, beta, ez, wait, fee)
                    s = stats(trs)
                    rows.append({"pair": f"{a}/{b}", "fold": fold, "exit_z": ez, "wait_z0": wait, "fee_pct": fee, **s})
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
    path = os.path.join(OUT_DIR, f"h4_exit_z_wf_{ts}.csv")
    out.to_csv(path, index=False)
    print(f"\nСохранено: {path} (rows={len(out)})")
    print("\n=== Сводка (mean по фолдам) ===")
    agg = out.groupby(["pair","exit_z","wait_z0","fee_pct"]).agg(
        n=("n","sum"), pnl_pct=("pnl_pct","mean"), wr=("wr","mean"),
        pf=("pf","mean"), sharpe=("sharpe","mean"), avg_hold=("avg_hold","mean"),
        maxdd=("maxdd","mean"), folds=("fold","count")).reset_index()
    for p in agg["pair"].unique():
        sub = agg[agg.pair == p]
        print(f"--- {p} ---")
        for _, r in sub.iterrows():
            print(f"  exit_z={r['exit_z']} wait_z0={r['wait_z0']} fee={r['fee_pct']}: n={int(r['n'])} pnl_pct={r['pnl_pct']:+.4f} wr={r['wr']:.3f} pf={r['pf']:.2f} sharpe={r['sharpe']:+.2f} avg_hold={r['avg_hold']:.1f} maxdd={r['maxdd']:+.4f}")

if __name__ == "__main__":
    main()
