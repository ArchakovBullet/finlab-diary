#!/usr/bin/env python3
"""
audit_quarantine.py — аудит disabled фьюч+фьюч пар (corr, coint_p, total_rows).
Read-only. v2/v3/v4 не трогает. Пишет CSV в logs/.
"""
import os
import json
import numpy as np
import pandas as pd
from datetime import datetime
from statsmodels.tsa.stattools import coint

ROOT = "/root/finlab"
CANDLES = os.path.join(ROOT, "data", "candles")
CONFIG = os.path.join(ROOT, "FinLabPy", "My_Indicators", "pairs_config_v2.json")
OUT_DIR = os.path.join(ROOT, "logs")
CORR_MIN = 0.5
COINT_MAX = 0.05
ROWS_MIN = 500

def load_pair(a, b, tf):
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
    da = da[[ca, "close"]].rename(columns={ca: "dt"})
    db = db[[cb, "close"]].rename(columns={cb: "dt"})
    m = pd.merge(da, db, on="dt", suffixes=("_a", "_b")).dropna()
    m["dt"] = pd.to_datetime(m["dt"], errors="coerce")
    m = m.dropna(subset=["dt"]).sort_values("dt").reset_index(drop=True)
    return m

def audit_pair(name, a, b, tf):
    m = load_pair(a, b, tf)
    if m is None or len(m) < 100:
        return {"pair": name, "tf": tf, "rows": 0, "corr": None, "coint_p": None, "candidate": False}
    la = np.log(m["close_a"].replace(0, np.nan))
    lb = np.log(m["close_b"].replace(0, np.nan))
    m2 = pd.DataFrame({"la": la, "lb": lb}).dropna()
    if len(m2) < 100:
        return {"pair": name, "tf": tf, "rows": len(m2), "corr": None, "coint_p": None, "candidate": False}
    corr = float(m2["la"].corr(m2["lb"]))
    try:
        _, pval, _ = coint(m2["la"], m2["lb"])
        pval = float(pval)
    except Exception:
        pval = None
    rows = len(m2)
    candidate = (corr is not None and corr >= CORR_MIN and pval is not None and pval < COINT_MAX and rows >= ROWS_MIN)
    return {"pair": name, "tf": tf, "rows": rows, "corr": round(corr, 3) if corr is not None else None, "coint_p": round(pval, 4) if pval is not None else None, "candidate": candidate}

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    cfg = json.load(open(CONFIG))
    pairs = cfg.get("pairs", {})
    disabled = [k for k, v in pairs.items() if not v.get("enabled")]
    fut = [k for k in disabled if any(x in k.split("_")[0] for x in ["LK-", "RN-", "HY-", "IR-", "GAZPF", "BR-", "EURRUBF", "USDRUBF", "GLDRUBF", "GD-"])]
    print(f"disabled фьюч+фьюч: {len(fut)}")
    rows = []
    for p in fut:
        parts = p.split("_")
        if len(parts) != 2:
            continue
        base, tf = parts
        ab = base.split("-")
        if len(ab) != 2:
            continue
        a, b = ab
        r = audit_pair(p, a, b, tf)
        rows.append(r)
        tag = "✅" if r["candidate"] else "  "
        print(f"  {tag} {p}: rows={r['rows']} corr={r['corr']} coint_p={r['coint_p']}")
    out = pd.DataFrame(rows)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    path = os.path.join(OUT_DIR, f"quarantine_audit_{ts}.csv")
    out.to_csv(path, index=False)
    cands = out[out["candidate"] == True]
    print(f"\nСохранено: {path}")
    print(f"Кандидаты (corr ≥ {CORR_MIN}, coint_p < {COINT_MAX}, rows ≥ {ROWS_MIN}): {len(cands)}")
    if len(cands):
        print(cands.to_string(index=False))

if __name__ == "__main__":
    main()
