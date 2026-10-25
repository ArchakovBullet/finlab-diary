#!/usr/bin/env python3
"""
sokolov_modelprice_test.py — тест модельной цены (Соколов, гл. 2.4).
Read-only. v2/v3/v4 не трогает. Пишет в logs/.

Варианты:
  baseline     — M10-close (как в v2).
  model_h1     — close последней H1-свечи внутри M10-бара (аналог «быстрого» периода).
  model_h1_avg — среднее close H1 внутри M10 (если несколько H1).

Walk-forward: train=30д, test=7д, шаг=7д.
entry_z=1.8, exit_z=0.5, fee=0.28%, slip=0.04%.
Пары: SFIN-SH_M10, BANE-BN_M10, BELU-NB_M10.
"""
import os, glob
import numpy as np
import pandas as pd

PAIRS = [
    ("SFIN-SH_M10", "SFIN", "SH"),
    ("BANE-BN_M10", "BANE", "BN"),
    ("BELU-NB_M10", "BELU", "NB"),
]
ENTRY_Z, EXIT_Z = 1.8, 0.5
FEE, SLIP = 0.0028, 0.0004
TRAIN_D, TEST_D, STEP_D = 30, 7, 7
DATA_DIR = "data/candles"
OUT_DIR = "logs"

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

def build_model_price(df_m10, df_h1, mode="model_h1"):
    """M10-close или модельная цена (close H1 внутри M10)."""
    m10 = df_m10.copy()
    if mode == "baseline" or df_h1 is None or len(df_h1) == 0:
        m10["price"] = m10["close"]
        return m10[["begin", "price"]]
    h1 = df_h1.copy()
    # Для каждого M10-бара — последний H1-close внутри [begin, begin+M10)
    m10 = m10.sort_values("begin").reset_index(drop=True)
    h1 = h1.sort_values("begin").reset_index(drop=True)
    prices = []
    for _, r in m10.iterrows():
        t0 = r["begin"]
        t1 = t0 + pd.Timedelta(minutes=10)
        sub = h1[(h1["begin"] >= t0) & (h1["begin"] < t1)]
        if len(sub) == 0:
            prices.append(np.nan)
        elif mode == "model_h1":
            prices.append(float(sub["close"].iloc[-1]))
        elif mode == "model_h1_avg":
            prices.append(float(sub["close"].mean()))
        else:
            prices.append(np.nan)
    m10["price"] = prices
    return m10[["begin", "price"]].dropna()

def ols_beta(logA, logB):
    x = logB.values; y = logA.values
    xm, ym = x.mean(), y.mean()
    v = ((x - xm) ** 2).mean()
    if v == 0 or np.isnan(v): return np.nan
    return ((x - xm) * (y - ym)).mean() / v

def build_z(dfA, dfB, mode, beta=None):
    m = pd.merge(dfA.rename(columns={"price": "price_a"}), dfB.rename(columns={"price": "price_b"}), on="begin")
    if len(m) < 50: return None
    logA = np.log(m["price_a"].replace(0, np.nan))
    logB = np.log(m["price_b"].replace(0, np.nan))
    m = m.assign(logA=logA.values, logB=logB.values).dropna()
    if len(m) < 50: return None
    b = beta if (beta is not None and not np.isnan(beta)) else ols_beta(m["logA"], m["logB"])
    if b is None or np.isnan(b) or b == 0: return None
    s = m["logA"] - b * m["logB"]
    s = s.replace([np.inf, -np.inf], np.nan).dropna()
    if len(s) < 50: return None
    mu, sd = s.mean(), s.std(ddof=1)
    if sd == 0 or np.isnan(sd): return None
    z = (s - mu) / sd
    out = pd.DataFrame({"begin": m.loc[s.index, "begin"].values, "spread": s.values, "z": z.values})
    return out, b

def simulate(zdf, entry_z=ENTRY_Z, exit_z=EXIT_Z):
    pos = 0; entry_price = None; trades = []
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
                gross = direction * (exit_price - entry_price)
                net = gross - (FEE + SLIP)
                trades.append(net); pos = 0
    if pos != 0:
        exit_price = zdf.iloc[-1]["spread"]
        direction = 1 if pos == 1 else -1
        trades.append(direction * (exit_price - entry_price) - (FEE + SLIP))
    if not trades: return 0, 0.0, 0.0, 0.0
    t = np.array(trades, dtype=float)
    pnl = t.sum(); wr = (t > 0).mean()
    sharpe = (t.mean() / t.std(ddof=1) * np.sqrt(len(t))) if (len(t) > 1 and t.std(ddof=1) > 0) else 0.0
    return len(t), pnl, wr, sharpe

def walk_forward(name, A, B):
    dfA_m10 = load_tf(A, "M10"); dfB_m10 = load_tf(B, "M10")
    try:
        dfA_h1 = load_tf(A, "H1"); dfB_h1 = load_tf(B, "H1")
    except Exception:
        dfA_h1 = dfB_h1 = None

    modes = ["baseline", "model_h1", "model_h1_avg"]
    prices = {}
    for mode in modes:
        prices[mode] = (
            build_model_price(dfA_m10, dfA_h1 if mode != "baseline" else None, mode),
            build_model_price(dfB_m10, dfB_h1 if mode != "baseline" else None, mode),
        )

    start = dfA_m10["begin"].min(); end = dfA_m10["begin"].max()
    t0 = start; fold = 0; rows = []
    while t0 + pd.Timedelta(days=TRAIN_D + TEST_D) <= end:
        train_end = t0 + pd.Timedelta(days=TRAIN_D)
        test_end = train_end + pd.Timedelta(days=TEST_D)
        fold += 1
        for mode in modes:
            pA, pB = prices[mode]
            dA_tr = pA[(pA.begin >= t0) & (pA.begin < train_end)]
            dB_tr = pB[(pB.begin >= t0) & (pB.begin < train_end)]
            dA_te = pA[(pA.begin >= train_end) & (pA.begin < test_end)]
            dB_te = pB[(pB.begin >= train_end) & (pB.begin < test_end)]
            if min(len(dA_tr), len(dB_tr), len(dA_te), len(dB_te)) < 40:
                rows.append({"pair": name, "mode": mode, "fold": fold, "trades": 0, "pnl": 0.0, "wr": 0.0, "sharpe": 0.0}); continue
            m_tr = pd.merge(dA_tr.rename(columns={"price":"price_a"}), dB_tr.rename(columns={"price":"price_b"}), on="begin")
            if len(m_tr) < 40:
                rows.append({"pair": name, "mode": mode, "fold": fold, "trades": 0, "pnl": 0.0, "wr": 0.0, "sharpe": 0.0}); continue
            b_tr = ols_beta(np.log(m_tr["price_a"].replace(0,np.nan)), np.log(m_tr["price_b"].replace(0,np.nan)))
            res = build_z(dA_te, dB_te, mode, beta=b_tr)
            if res is None:
                rows.append({"pair": name, "mode": mode, "fold": fold, "trades": 0, "pnl": 0.0, "wr": 0.0, "sharpe": 0.0}); continue
            zdf, _ = res
            n, pnl, wr, sh = simulate(zdf)
            rows.append({"pair": name, "mode": mode, "fold": fold, "trades": n, "pnl": pnl, "wr": wr, "sharpe": sh})
        t0 += pd.Timedelta(days=STEP_D)
    return rows

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    all_rows = []
    for name, A, B in PAIRS:
        print(f"=== {name} ===")
        try:
            rows = walk_forward(name, A, B)
        except Exception as e:
            print(f"  [ERR] {e}"); continue
        for r in rows:
            print(f"  fold={r['fold']} mode={r['mode']:14s} trades={r['trades']:3d} pnl={r['pnl']:+.4f} wr={r['wr']:.3f} sharpe={r['sharpe']:+.2f}")
        all_rows.extend(rows)
    if all_rows:
        out = pd.DataFrame(all_rows)
        ts = pd.Timestamp.now().strftime("%Y-%m-%d_%H%M")
        path = os.path.join(OUT_DIR, f"sokolov_modelprice_{ts}.csv")
        out.to_csv(path, index=False)
        print(f"\nСохранено: {path}")
        print("\n=== Сводка (сумма по фолдам) ===")
        agg = out.groupby(["pair","mode"]).agg(trades=("trades","sum"), pnl=("pnl","sum"),
                                               wr=("wr","mean"), sharpe=("sharpe","mean"), folds=("fold","count")).reset_index()
        print(agg.to_string(index=False))
    else:
        print("Нет данных.")

if __name__ == "__main__":
    main()
