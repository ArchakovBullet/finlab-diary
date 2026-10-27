#!/usr/bin/env python3
"""
moexfn_divergence_test.py — walk-forward тест divergence SBER/GAZP/LKOH vs MOEXFN.
Read-only. v2/v3/v4 не трогает. Пишет CSV в logs/.

Гипотеза: если акция и сектор (MOEXFN) движутся в разные стороны (divergence),
то акция возвращается к сектору (forward return в сторону сектора) на 1/2/4/8 дней.

Walk-forward: train=6мес, test=1мес, шаг=1мес.
Baseline: все дни (без divergence).
"""
import os
import numpy as np
import pandas as pd

ROOT = "/root/finlab"
OUT_DIR = os.path.join(ROOT, "logs")
TICKERS = ["SBER", "GAZP", "LKOH"]
HORIZONS = [1, 2, 4, 8]  # дни
TRAIN_D = 180  # 6 мес
TEST_D = 30    # 1 мес
STEP_D = 30

def load_price_d1(t):
    p = f"{ROOT}/data/candles/{t}_D1.parquet"
    if not os.path.exists(p): return None
    df = pd.read_parquet(p)
    cols = {c.lower(): c for c in df.columns}
    df = df.rename(columns={cols.get("begin","begin"): "begin", cols.get("close","close"): "close"})
    df["begin"] = pd.to_datetime(df["begin"], errors="coerce").dt.normalize()
    df = df.dropna(subset=["begin","close"]).sort_values("begin").reset_index(drop=True)
    return df[["begin","close"]].rename(columns={"close":"price"})

def load_sector_d1():
    p = f"{ROOT}/data/sector_indices/MOEXFN_D1.parquet"
    if not os.path.exists(p): return None
    df = pd.read_parquet(p)
    df["begin"] = pd.to_datetime(df["begin"], errors="coerce").dt.normalize()
    df = df.dropna(subset=["begin","close"]).sort_values("begin").reset_index(drop=True)
    return df[["begin","close"]].rename(columns={"close":"sector"})

def merge_data(t):
    p = load_price_d1(t)
    s = load_sector_d1()
    if p is None or s is None: return None
    m = pd.merge(p, s, on="begin", how="inner").sort_values("begin").reset_index(drop=True)
    if len(m) < 100: return None
    m["ret_x"] = np.log(m["price"]).diff()
    m["ret_sector"] = np.log(m["sector"]).diff()
    for h in HORIZONS:
        m[f"fwd_{h}"] = np.log(m["price"].shift(-h) / m["price"])
    m["divergence"] = (np.sign(m["ret_x"]) != np.sign(m["ret_sector"])) & m["ret_x"].notna() & m["ret_sector"].notna()
    # направление возврата: если акция упала, а сектор вырос -> ожидаем рост акции (fwd > 0)
    m["expected_sign"] = np.sign(m["ret_sector"])  # акция должна догнать сектор
    return m

def eval_block(df, label):
    rows = []
    for h in HORIZONS:
        col = f"fwd_{h}"
        for cond_name, cond in [("baseline", pd.Series(True, index=df.index)), ("divergence", df["divergence"])]:
            sub = df[cond & df[col].notna()].copy()
            if len(sub) < 10: continue
            # для divergence: проверяем, что return в сторону сектора (expected_sign)
            if cond_name == "divergence":
                aligned = sub[col] * sub["expected_sign"]
                mean_aligned = float(aligned.mean())
                wr_aligned = float((aligned > 0).mean())
                sharpe = float(aligned.mean() / aligned.std(ddof=1) * np.sqrt(len(aligned))) if aligned.std(ddof=1) > 0 else 0.0
                rows.append({"block":label,"cond":cond_name,"h":h,"n":int(len(sub)),
                             "mean_fwd":round(float(sub[col].mean()),6),
                             "mean_aligned":round(mean_aligned,6),
                             "wr_aligned":round(wr_aligned,3),
                             "sharpe_aligned":round(sharpe,3)})
            else:
                rows.append({"block":label,"cond":cond_name,"h":h,"n":int(len(sub)),
                             "mean_fwd":round(float(sub[col].mean()),6),
                             "mean_aligned":None,"wr_aligned":None,"sharpe_aligned":None})
    return rows

def walk_forward(t, m):
    if m is None: return []
    rows = []
    start = m["begin"].min(); end = m["begin"].max()
    t0 = start; fold = 0
    while t0 + pd.Timedelta(days=TRAIN_D + TEST_D) <= end:
        test_start = t0 + pd.Timedelta(days=TRAIN_D)
        test_end = test_start + pd.Timedelta(days=TEST_D)
        test = m[(m.begin >= test_start) & (m.begin < test_end)].copy()
        fold += 1
        if len(test) < 10:
            t0 += pd.Timedelta(days=STEP_D); continue
        for r in eval_block(test, f"fold{fold}"):
            r["ticker"] = t; r["fold"] = fold
            rows.append(r)
        t0 += pd.Timedelta(days=STEP_D)
    return rows

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    all_rows = []
    for t in TICKERS:
        m = merge_data(t)
        if m is None:
            print(f"{t}: нет данных"); continue
        print(f"=== {t} === rows={len(m)} | divergence={int(m['divergence'].sum())}")
        rows = walk_forward(t, m)
        all_rows.extend(rows)
    if not all_rows:
        print("Нет данных."); return
    out = pd.DataFrame(all_rows)
    ts = pd.Timestamp.now().strftime("%Y-%m-%d_%H%M")
    path = os.path.join(OUT_DIR, f"moexfn_divergence_{ts}.csv")
    out.to_csv(path, index=False)
    print(f"\nСохранено: {path} (rows={len(out)})")

    print("\n=== Сводка по тикеру / условию / горизонту (mean по фолдам) ===")
    agg = out.groupby(["ticker","cond","h"]).agg(
        n=("n","sum"),
        mean_fwd=("mean_fwd","mean"),
        mean_aligned=("mean_aligned","mean"),
        wr_aligned=("wr_aligned","mean"),
        sharpe_aligned=("sharpe_aligned","mean"),
        folds=("fold","count"),
    ).reset_index()
    for t in TICKERS:
        sub = agg[agg.ticker==t]
        if sub.empty: continue
        print(f"\n--- {t} ---")
        for h in HORIZONS:
            base = sub[(sub.cond=="baseline") & (sub.h==h)]
            div  = sub[(sub.cond=="divergence") & (sub.h==h)]
            if base.empty or div.empty: continue
            b = base.iloc[0]; d = div.iloc[0]
            print(f"  h={h}: baseline n={int(b['n'])} mean_fwd={b['mean_fwd']:+.6f} | "
                  f"divergence n={int(d['n'])} mean_fwd={d['mean_fwd']:+.6f} "
                  f"mean_aligned={d['mean_aligned']:+.6f} wr_aligned={d['wr_aligned']:.3f} sharpe_aligned={d['sharpe_aligned']:+.2f}")

if __name__ == "__main__":
    main()
