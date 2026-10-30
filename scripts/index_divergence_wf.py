#!/usr/bin/env python3
"""index_divergence_wf.py — walk-forward тест divergence SBER/GAZP vs MOEXFN (D1). Read-only. Пишет CSV в logs/."""
import os
import numpy as np
import pandas as pd
from datetime import datetime

ROOT = "/root/finlab"
OUT_DIR = os.path.join(ROOT, "logs")
TICKERS = ["SBER", "GAZP"]
SECTOR_FILE = os.path.join(ROOT, "data", "sector_indices", "MOEXFN_D1.parquet")
CANDLES_DIR = os.path.join(ROOT, "data", "candles")
WINDOW = 60
H_DAYS = 1
FEE = 0.0028
SLIP = 0.0004
TRAIN_D = 180
TEST_D = 30
STEP_D = 30
MIN_ENTRY_Z_GRID = [0.0, 0.5, 1.0, 1.5, 2.0]
EXIT_Z_GRID = [0.5, 0.3]

def load_price_d1(ticker):
    p = os.path.join(CANDLES_DIR, f"{ticker}_D1.parquet")
    if not os.path.exists(p): return None
    df = pd.read_parquet(p)
    df = df[["begin", "close"]].copy()
    df["begin"] = pd.to_datetime(df["begin"], errors="coerce").dt.normalize()
    return df.dropna().sort_values("begin").reset_index(drop=True)

def load_sector():
    df = pd.read_parquet(SECTOR_FILE)[["begin", "close"]].rename(columns={"close": "sector"})
    df["begin"] = pd.to_datetime(df["begin"], errors="coerce").dt.normalize()
    return df.dropna().sort_values("begin").reset_index(drop=True)

def build_features(df, sector):
    m = pd.merge(df, sector, on="begin", how="inner").sort_values("begin").reset_index(drop=True)
    m["log_stock"] = np.log(m["close"].replace(0, np.nan))
    m["log_sector"] = np.log(m["sector"].replace(0, np.nan))
    m = m.dropna().reset_index(drop=True)
    m["ret_stock"] = m["log_stock"].diff()
    m["ret_sector"] = m["log_sector"].diff()
    m["divergence"] = (np.sign(m["ret_stock"]) != np.sign(m["ret_sector"])) & m["ret_stock"].notna() & m["ret_sector"].notna()
    n = len(m)
    z_arr = np.full(n, np.nan)
    for i in range(WINDOW, n):
        x = m["log_sector"].values[i-WINDOW:i]
        y = m["log_stock"].values[i-WINDOW:i]
        xm, ym = x.mean(), y.mean()
        var = ((x - xm) ** 2).mean()
        if var <= 0: continue
        beta = ((x - xm) * (y - ym)).mean() / var
        spread = m["log_stock"].values[i-WINDOW:i+1] - beta * m["log_sector"].values[i-WINDOW:i+1]
        mu, sd = spread.mean(), spread.std(ddof=1)
        if sd <= 0: continue
        z_arr[i] = (spread[-1] - mu) / sd
    m["z"] = z_arr
    return m

def simulate_fold(test, ticker, min_entry_z, exit_z):
    if test is None or len(test) < 2: return []
    trades = []
    open_pos = None
    dates = test["begin"].tolist()
    z_vals = test["z"].tolist()
    prices = test["close"].tolist()
    divs = test["divergence"].tolist()
    ret_sec = test["ret_sector"].tolist()
    for i in range(len(test)):
        if pd.isna(z_vals[i]): continue
        if open_pos is not None:
            held_days = (dates[i].normalize() - open_pos["entry_date"].normalize()).days
            if held_days >= H_DAYS or (held_days >= 1 and abs(z_vals[i]) <= exit_z):
                sign = 1 if open_pos["dir"] == "LONG" else -1
                gross = sign * (prices[i] - open_pos["entry_price"])
                net = gross - (FEE + SLIP) * open_pos["entry_price"]
                trades.append({"ticker": ticker, "entry_date": open_pos["entry_date"], "exit_date": dates[i], "entry_z": open_pos["entry_z"], "exit_z": z_vals[i], "pnl": net, "held_days": held_days})
                open_pos = None
        if open_pos is None and divs[i] and abs(z_vals[i]) >= min_entry_z:
            direction = "LONG" if ret_sec[i] > 0 else "SHORT"
            open_pos = {"entry_date": dates[i], "entry_price": prices[i], "entry_z": z_vals[i], "dir": direction}
    return trades

def stats(trades):
    if not trades:
        return {"n": 0, "pnl": 0.0, "wr": 0.0, "sharpe": 0.0, "avg": 0.0, "maxdd": 0.0, "avg_hold": 0.0}
    t = np.array([tr["pnl"] for tr in trades])
    cum = np.cumsum(t)
    peak = np.maximum.accumulate(cum)
    dd = cum - peak
    return {"n": len(t), "pnl": float(t.sum()), "wr": float((t > 0).mean()),
            "sharpe": float(t.mean() / t.std() * np.sqrt(252)) if t.std() > 0 else 0.0,
            "avg": float(t.mean()), "maxdd": float(dd.min()) if len(dd) else 0.0,
            "avg_hold": float(np.mean([tr["held_days"] for tr in trades]))}

def walk_forward(ticker, m):
    if m is None or len(m) < TRAIN_D + TEST_D: return []
    rows = []
    start = m["begin"].min(); end = m["begin"].max()
    t0 = start; fold = 0
    while t0 + pd.Timedelta(days=TRAIN_D + TEST_D) <= end:
        test_start = t0 + pd.Timedelta(days=TRAIN_D)
        test_end = test_start + pd.Timedelta(days=TEST_D)
        test = m[(m.begin >= test_start) & (m.begin < test_end)].reset_index(drop=True)
        fold += 1
        if len(test) < 5:
            t0 += pd.Timedelta(days=STEP_D); continue
        for mez in MIN_ENTRY_Z_GRID:
            for ez in EXIT_Z_GRID:
                tr = simulate_fold(test, ticker, mez, ez)
                s = stats(tr)
                rows.append({"ticker": ticker, "fold": fold, "min_entry_z": mez, "exit_z": ez, **s})
        t0 += pd.Timedelta(days=STEP_D)
    return rows

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    sector = load_sector()
    all_rows = []
    for t in TICKERS:
        df = load_price_d1(t)
        if df is None: print(t, "нет D1"); continue
        m = build_features(df, sector)
        n_div = int(m["divergence"].sum())
        print("===", t, "=== rows=", len(m), "| divergence=", n_div)
        rows = walk_forward(t, m)
        all_rows.extend(rows)
    if not all_rows:
        print("Нет данных."); return
    out = pd.DataFrame(all_rows)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    path = os.path.join(OUT_DIR, "index_divergence_wf_" + ts + ".csv")
    out.to_csv(path, index=False)
    print("Сохранено:", path, "(rows=" + str(len(out)) + ")")
    print("=== Сводка: ticker x min_entry_z x exit_z (mean по фолдам) ===")
    agg = out.groupby(["ticker","min_entry_z","exit_z"]).agg(
        n=("n","sum"), pnl=("pnl","mean"), wr=("wr","mean"),
        sharpe=("sharpe","mean"), avg_hold=("avg_hold","mean"),
        maxdd=("maxdd","mean"), folds=("fold","count"),
    ).reset_index()
    for t in TICKERS:
        sub = agg[agg.ticker==t]
        if sub.empty: continue
        print("---", t, "---")
        for mez in MIN_ENTRY_Z_GRID:
            for ez in EXIT_Z_GRID:
                r = sub[(sub.min_entry_z==mez) & (sub.exit_z==ez)]
                if r.empty: continue
                r = r.iloc[0]
                tag = " (baseline)" if mez == 0.0 else ""
                print("  min_entry_z={:.1f} exit_z={:.1f}: n={} pnl={:+.4f} wr={:.3f} sharpe={:+.2f} avg_hold={:.1f}d maxdd={:+.4f}{}".format(
                    mez, ez, int(r["n"]), r["pnl"], r["wr"], r["sharpe"], r["avg_hold"], r["maxdd"], tag))

if __name__ == "__main__":
    main()
