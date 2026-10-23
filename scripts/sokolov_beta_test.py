#!/usr/bin/env python3
"""
sokolov_beta_test.py — тест комбинирования коинтеграционных соотношений (Соколов, гл. 2.1).
Read-only. v2/v3 не трогает. Пишет в logs/.

Для каждой пары (rank>=2):
  - baseline: β = hedge_ratio из pairs_config.json (один β).
  - combined_v1: два β из coint_johansen на train, веса по (2.1.34) — без корреляции.
  - combined_v2: два β из coint_johansen на train, веса по (2.1.35) — с корреляцией.

Walk-forward: train=30д, test=7д, шаг=7д (как в EMA-тесте).
entry_z=1.8, exit_z=0.5, fee=0.28%, slip=0.04%.

Пары: 9 с rank>=2 (из pairs_config.json).
"""
import os, sys, json
import numpy as np
import pandas as pd
from statsmodels.tsa.vector_ar.vecm import coint_johansen

PAIRS = [
    "BANE-BN_M10",  # единственная пара с rho<0.9 (см. проверку)
]
ENTRY_Z, EXIT_Z = 1.8, 0.5
FEE, SLIP = 0.0028, 0.0004
TRAIN_D, TEST_D, STEP_D = 30, 7, 7
DATA_DIR = "data/candles"
CFG_PATH = "FinLabPy/My_Indicators/pairs_config.json"
OUT_DIR  = "logs"

def parse_pair(name):
    # "BANE-BN_M10" -> ("BANE", "BN", "M10")
    base, tf = name.rsplit("_", 1)
    a, b = base.split("-", 1)
    return a, b, tf

def load_tf(ticker, tf):
    path = os.path.join(DATA_DIR, f"{ticker}_{tf}.parquet")
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    df = pd.read_parquet(path)
    cols = {c.lower(): c for c in df.columns}
    if "begin" not in cols or "close" not in cols:
        raise ValueError(f"{path}: нет begin/close. Есть: {list(df.columns)}")
    df = df.rename(columns={cols["begin"]: "begin", cols["close"]: "close"})
    df["begin"] = pd.to_datetime(df["begin"], errors="coerce")
    df = df.dropna(subset=["begin", "close"]).sort_values("begin").reset_index(drop=True)
    return df[["begin", "close"]]

def ols_beta(logA, logB):
    x = logB.values; y = logA.values
    xm, ym = x.mean(), y.mean()
    v = ((x - xm) ** 2).mean()
    if v == 0 or np.isnan(v): return np.nan
    return ((x - xm) * (y - ym)).mean() / v

def johansen_two_betas(logA, logB):
    """Возвращает 2 нормированных β (по первой компоненте = 1) или None."""
    data = np.column_stack([logA.values, logB.values])
    data = data[~np.isnan(data).any(axis=1)]
    if len(data) < 60: return None
    try:
        res = coint_johansen(data, det_order=0, k_ar_diff=1)
    except Exception:
        return None
    vecs = res.evec  # shape (n, n): columns — векторы
    if vecs.shape[1] < 2: return None
    betas = []
    for j in range(2):
        v = vecs[:, j]
        if abs(v[0]) < 1e-9: continue
        betas.append(v[1] / v[0])  # β = coef_B / coef_A, A = 1
    if len(betas) < 2: return None
    return betas[0], betas[1]

def build_z(spread, entry_z=ENTRY_Z):
    s = spread.replace([np.inf, -np.inf], np.nan).dropna()
    if len(s) < 50: return None
    mu, sd = s.mean(), s.std(ddof=1)
    if sd == 0 or np.isnan(sd): return None
    return (s - mu) / sd

def simulate(zdf, entry_z=ENTRY_Z, exit_z=EXIT_Z):
    """PnL нормирован на std(spread) — сравнимо между baseline и combined."""
    if len(zdf) < 2: return 0, 0.0, 0.0, 0.0
    sd = zdf["spread"].std(ddof=1)
    if sd == 0 or np.isnan(sd): return 0, 0.0, 0.0, 0.0
    pos = 0; entry_price = None
    trades = []
    for _, r in zdf.iterrows():
        z = r["z"]
        if pos == 0:
            if abs(z) >= entry_z:
                pos = -1 if z > 0 else 1
                entry_price = r["spread"]
        else:
            if abs(z) <= exit_z:
                exit_price = r["spread"]
                direction = 1 if pos == 1 else -1
                gross = (direction * (exit_price - entry_price)) / sd
                net = gross - (FEE + SLIP) / sd
                trades.append(net); pos = 0
    if pos != 0:
        exit_price = zdf.iloc[-1]["spread"]
        direction = 1 if pos == 1 else -1
        gross = direction * (exit_price - entry_price)
        trades.append(gross - (FEE + SLIP))
    if not trades:
        return 0, 0.0, 0.0, 0.0
    t = np.array(trades, dtype=float)
    pnl = t.sum(); wr = (t > 0).mean()
    sharpe = (t.mean() / t.std(ddof=1) * np.sqrt(len(t))) if (len(t) > 1 and t.std(ddof=1) > 0) else 0.0
    return len(t), pnl, wr, sharpe

def run_pair(name, cfg):
    A, B, tf = parse_pair(name)
    try:
        dfA = load_tf(A, tf); dfB = load_tf(B, tf)
    except Exception as e:
        print(f"[{name}] загрузка: {e}"); return []

    hr = cfg["pairs"][name].get("johansen", {}).get("hedge_ratio")
    if hr is None:
        print(f"[{name}] нет hedge_ratio в конфиге"); return []

    start, end = dfA["begin"].min(), dfA["begin"].max()
    t0 = start; fold = 0; rows = []
    while t0 + pd.Timedelta(days=TRAIN_D + TEST_D) <= end:
        train_end = t0 + pd.Timedelta(days=TRAIN_D)
        test_end  = train_end + pd.Timedelta(days=TEST_D)
        fold += 1
        dA_tr = dfA[(dfA.begin >= t0) & (dfA.begin < train_end)]
        dB_tr = dfB[(dfB.begin >= t0) & (dfB.begin < train_end)]
        dA_te = dfA[(dfA.begin >= train_end) & (dfA.begin < test_end)]
        dB_te = dfB[(dfB.begin >= train_end) & (dfB.begin < test_end)]
        if min(len(dA_tr), len(dB_tr), len(dA_te), len(dB_te)) < 40:
            t0 += pd.Timedelta(days=STEP_D); continue

        # baseline β (из конфига)
        b_base = hr

        # combined: 2 β из johansen на train
        m_tr = pd.merge(dA_tr, dB_tr, on="begin", suffixes=("_A","_B")).dropna()
        logA_tr = np.log(m_tr["close_A"].replace(0, np.nan))
        logB_tr = np.log(m_tr["close_B"].replace(0, np.nan))
        jres = johansen_two_betas(logA_tr, logB_tr)

        # test: merge
        m_te = pd.merge(dA_te, dB_te, on="begin", suffixes=("_A","_B")).dropna()
        if len(m_te) < 40:
            t0 += pd.Timedelta(days=STEP_D); continue
        logA_te = np.log(m_te["close_A"].replace(0, np.nan))
        logB_te = np.log(m_te["close_B"].replace(0, np.nan))

        # baseline z
        sp_base = logA_te - b_base * logB_te
        z_base = build_z(sp_base)
        if z_base is not None:
            zdf = pd.DataFrame({"begin": m_te["begin"].values, "spread": sp_base.values, "z": z_base.values})
            n, pnl, wr, sh = simulate(zdf)
            rows.append({"pair": name, "mode": "baseline", "fold": fold, "trades": n, "pnl": pnl, "wr": wr, "sharpe": sh})

        # combined v1 / v2
        if jres is not None:
            b1, b2 = jres
            v = logA_te - b1 * logB_te
            w = logA_te - b2 * logB_te
            sv, sw = v.var(ddof=1), w.var(ddof=1)
            if sv > 0 and sw > 0:
                rho = v.cov(w) / np.sqrt(sv * sw)
                # v1: без корреляции
                denom1 = sw - sv
                if abs(denom1) > 1e-12:
                    a1 = sw / denom1; b1w = sv / denom1
                    comb1 = a1 * v + b1w * w
                    z1 = build_z(comb1)
                    if z1 is not None:
                        zdf = pd.DataFrame({"begin": m_te["begin"].values, "spread": comb1.values, "z": z1.values})
                        n, pnl, wr, sh = simulate(zdf)
                        rows.append({"pair": name, "mode": "combined_v1", "fold": fold, "trades": n, "pnl": pnl, "wr": wr, "sharpe": sh})
                # v2: с корреляцией (2.1.35 через σ = sqrt(var), не σ²)
                sv_ = np.sqrt(sv); sw_ = np.sqrt(sw)
                denom2 = sw - 2*rho*sv_*sw_ + sv
                if abs(denom2) > 1e-12:
                    a2 = sw_ * (sw_ - rho*sv_) / denom2
                    b2w = sv_ * (rho*sw_ - sv_) / denom2
                    comb2 = a2 * v + b2w * w
                    z2 = build_z(comb2)
                    if z2 is not None:
                        zdf = pd.DataFrame({"begin": m_te["begin"].values, "spread": comb2.values, "z": z2.values})
                        n, pnl, wr, sh = simulate(zdf)
                        rows.append({"pair": name, "mode": "combined_v2", "fold": fold, "trades": n, "pnl": pnl, "wr": wr, "sharpe": sh})
        t0 += pd.Timedelta(days=STEP_D)
    return rows

def main():
    cfg = json.load(open(CFG_PATH))
    os.makedirs(OUT_DIR, exist_ok=True)
    all_rows = []
    for name in PAIRS:
        print(f"=== {name} ===")
        try:
            rows = run_pair(name, cfg)
        except Exception as e:
            print(f"  [ERR] {e}"); continue
        for r in rows:
            print(f"  fold={r['fold']} mode={r['mode']:12s} trades={r['trades']:3d} pnl={r['pnl']:+.4f} wr={r['wr']:.3f} sharpe={r['sharpe']:+.2f}")
        all_rows.extend(rows)
    if all_rows:
        out = pd.DataFrame(all_rows)
        ts = pd.Timestamp.now().strftime("%Y-%m-%d_%H%M")
        path = os.path.join(OUT_DIR, f"sokolov_beta_{ts}.csv")
        out.to_csv(path, index=False)
        print(f"\nСохранено: {path}")
        print("\n=== Сводка (сумма по фолдам) ===")
        agg = out.groupby(["pair","mode"]).agg(
            trades=("trades","sum"), pnl=("pnl","sum"),
            wr=("wr","mean"), sharpe=("sharpe","mean"), folds=("fold","count")
        ).reset_index()
        print(agg.to_string(index=False))
    else:
        print("Нет данных.")

if __name__ == "__main__":
    main()
