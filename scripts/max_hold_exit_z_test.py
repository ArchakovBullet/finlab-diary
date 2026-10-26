#!/usr/bin/env python3
"""
max_hold_exit_z_test.py — тест MAX_HOLD / exit_z / max_z для M10 (IDEAS п.15/17).
Read-only. v2/v3/v4 не трогает. Пишет результат в logs/.

Параметры (по одному за раз, остальные = off/baseline):
  MAX_HOLD: off, 90, 120 (минуты; M10 -> 9/12 баров)
  exit_z:   off(0.5), 0.3, 0.0
  max_z:    off(None), 4.0, 3.5, 3.0  (вход только если |z| <= max_z)

Walk-forward: train=30д, test=7д, шаг=7д.
entry_z=1.8, fee=0.28%, slip=0.04% (0.02*2).
Пары: SFIN-SH_M10, BANE-BN_M10, BELU-NB_M10.
"""
import os
import numpy as np
import pandas as pd

PAIRS = [
    ("SFIN-SH_M10", "SFIN", "SH"),
    ("BANE-BN_M10", "BANE", "BN"),
    ("BELU-NB_M10", "BELU", "NB"),
]
ENTRY_Z = 1.8
EXIT_Z_DEFAULT = 0.5
FEE  = 0.0028
SLIP = 0.0004
TRAIN_D = 30
TEST_D  = 7
STEP_D  = 7
DATA_DIR = "data/candles"
OUT_DIR  = "logs"
M10_BAR_MIN = 10  # 1 бар = 10 минут

def load_m10(ticker):
    path = os.path.join(DATA_DIR, f"{ticker}_M10.parquet")
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    df = pd.read_parquet(path)
    cols = {c.lower(): c for c in df.columns}
    for n in ("begin", "close"):
        if n not in cols:
            raise ValueError(f"{path}: нет колонки {n}. Есть: {list(df.columns)}")
    df = df.rename(columns={cols["begin"]: "begin", cols["close"]: "close"})
    df["begin"] = pd.to_datetime(df["begin"], errors="coerce", utc=False)
    df = df.dropna(subset=["begin", "close"]).sort_values("begin").reset_index(drop=True)
    return df[["begin", "close"]]

def ols_beta(logA, logB):
    x = logB.values; y = logA.values
    xm, ym = x.mean(), y.mean()
    var = ((x - xm) ** 2).mean()
    if var == 0 or np.isnan(var):
        return np.nan
    return ((x - xm) * (y - ym)).mean() / var

def build_spread(dfA, dfB, beta=None):
    m = pd.merge(dfA, dfB, on="begin", suffixes=("_A", "_B")).dropna()
    if len(m) < 50:
        return None
    logA = np.log(m["close_A"].replace(0, np.nan))
    logB = np.log(m["close_B"].replace(0, np.nan))
    m = m.assign(logA=logA.values, logB=logB.values).dropna()
    if len(m) < 50:
        return None
    b = beta if (beta is not None and not np.isnan(beta)) else ols_beta(m["logA"], m["logB"])
    if b is None or np.isnan(b) or b == 0:
        return None
    s = (m["logA"] - b * m["logB"]).replace([np.inf, -np.inf], np.nan).dropna()
    if len(s) < 50:
        return None
    mu = s.mean(); sd = s.std(ddof=1)
    if sd == 0 or np.isnan(sd):
        return None
    z = (s - mu) / sd
    out = pd.DataFrame({"begin": m.loc[s.index, "begin"].values, "spread": s.values, "z": z.values}).reset_index(drop=True)
    return out, b

def simulate(zdf, exit_z, max_hold_bars, max_z):
    """Вход |z|>=ENTRY_Z (и |z|<=max_z, если задан), выход |z|<=exit_z / MAX_HOLD / конец."""
    pos = 0; entry_price = None; bars_held = 0
    trades = []
    for _, r in zdf.iterrows():
        z = r["z"]
        if pos == 0:
            if abs(z) >= ENTRY_Z and (max_z is None or abs(z) <= max_z):
                pos = -1 if z > 0 else 1
                entry_price = r["spread"]
                bars_held = 0
        else:
            bars_held += 1
            hit_exit = abs(z) <= exit_z
            hit_hold = (max_hold_bars is not None and bars_held >= max_hold_bars)
            if hit_exit or hit_hold:
                direction = 1 if pos == 1 else -1
                gross = direction * (r["spread"] - entry_price)
                net = gross - 2 * (FEE / 2 + SLIP / 2)
                trades.append(net)
                pos = 0
    if pos != 0:
        direction = 1 if pos == 1 else -1
        gross = direction * (zdf.iloc[-1]["spread"] - entry_price)
        net = gross - 2 * (FEE / 2 + SLIP / 2)
        trades.append(net)
    return trades

def metrics(trades):
    if not trades:
        return 0, 0.0, 0.0, 0.0
    t = np.array(trades, dtype=float)
    pnl = float(t.sum())
    wr = float((t > 0).mean())
    sharpe = float(t.mean() / t.std(ddof=1) * np.sqrt(len(t))) if t.std(ddof=1) > 0 else 0.0
    return len(t), pnl, wr, sharpe

def variants():
    """По одному параметру за раз (baseline=off)."""
    v = []
    # MAX_HOLD
    for mh in (None, 90, 120):
        v.append(("max_hold", "off" if mh is None else str(mh), EXIT_Z_DEFAULT, None if mh is None else mh // M10_BAR_MIN, None))
    # exit_z
    for ez in (None, 0.3, 0.0):
        v.append(("exit_z", "off" if ez is None else str(ez), EXIT_Z_DEFAULT if ez is None else ez, None, None))
    # max_z
    for mz in (None, 4.0, 3.5, 3.0):
        v.append(("max_z", "off" if mz is None else str(mz), EXIT_Z_DEFAULT, None, mz))
    return v

def walk_forward_pair(name, A, B):
    dfA = load_m10(A); dfB = load_m10(B)
    if len(dfA) < 100 or len(dfB) < 100:
        print(f"[{name}] мало данных, пропуск"); return []

    rows = []
    start = dfA["begin"].min(); end = dfA["begin"].max()
    t0 = start; fold = 0
    while t0 + pd.Timedelta(days=TRAIN_D + TEST_D) <= end:
        train_end = t0 + pd.Timedelta(days=TRAIN_D)
        test_end  = train_end + pd.Timedelta(days=TEST_D)
        fold += 1
        dA_tr = dfA[(dfA.begin >= t0) & (dfA.begin < train_end)]
        dB_tr = dfB[(dfB.begin >= t0) & (dfB.begin < train_end)]
        dA_te = dfA[(dfA.begin >= train_end) & (dfA.begin < test_end)]
        dB_te = dfB[(dfB.begin >= train_end) & (dfB.begin < test_end)]
        if len(dA_tr) < 100 or len(dB_tr) < 100 or len(dA_te) < 50 or len(dB_te) < 50:
            t0 += pd.Timedelta(days=STEP_D); continue
        m_tr = pd.merge(dA_tr, dB_tr, on="begin", suffixes=("_A", "_B"))
        if len(m_tr) < 50:
            t0 += pd.Timedelta(days=STEP_D); continue
        b_tr = ols_beta(np.log(m_tr["close_A"].replace(0, np.nan)),
                        np.log(m_tr["close_B"].replace(0, np.nan)))
        if b_tr is None or np.isnan(b_tr) or b_tr == 0:
            t0 += pd.Timedelta(days=STEP_D); continue

        res = build_spread(dA_te, dB_te, beta=b_tr)
        if res is None:
            t0 += pd.Timedelta(days=STEP_D); continue
        zdf, _ = res

        for group, val, exit_z, mh_bars, max_z in variants():
            trades = simulate(zdf, exit_z=exit_z, max_hold_bars=mh_bars, max_z=max_z)
            n, pnl, wr, sharpe = metrics(trades)
            rows.append({"pair": name, "group": group, "value": val, "fold": fold,
                         "trades": n, "pnl": pnl, "wr": wr, "sharpe": sharpe})
        t0 += pd.Timedelta(days=STEP_D)
    return rows

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    all_rows = []
    for name, A, B in PAIRS:
        print(f"=== {name} ===")
        try:
            rows = walk_forward_pair(name, A, B)
        except Exception as e:
            print(f"  [ERR] {e}"); continue
        all_rows.extend(rows)
    if not all_rows:
        print("Нет данных."); return
    out = pd.DataFrame(all_rows)
    ts = pd.Timestamp.now().strftime("%Y-%m-%d_%H%M")
    path = os.path.join(OUT_DIR, f"max_hold_exit_z_{ts}.csv")
    out.to_csv(path, index=False)
    print(f"\nСохранено: {path}")
    agg = out.groupby(["pair","group","value"]).agg(
        trades=("trades","sum"), pnl=("pnl","sum"),
        wr=("wr","mean"), sharpe=("sharpe","mean"), folds=("fold","count")
    ).reset_index()
    # компактный вывод: по группам
    for group in ("max_hold","exit_z","max_z"):
        g = agg[agg.group == group]
        if g.empty: continue
        print(f"\n--- {group} ---")
        for pair in g["pair"].unique():
            gp = g[g.pair == pair]
            base = gp[gp.value == "off"]
            base_pnl = float(base["pnl"].iloc[0]) if not base.empty else float('nan')
            base_sh  = float(base["sharpe"].iloc[0]) if not base.empty else float('nan')
            print(f"  {pair}: baseline pnl={base_pnl:+.4f} sharpe={base_sh:+.2f}")
            for _, r in gp.iterrows():
                if r["value"] == "off": continue
                print(f"    {r['value']:>5}: pnl={r['pnl']:+.4f} (Δ{r['pnl']-base_pnl:+.4f}) "
                      f"trades={int(r['trades'])} wr={r['wr']:.3f} sharpe={r['sharpe']:+.2f} (Δ{r['sharpe']-base_sh:+.2f})")

if __name__ == "__main__":
    main()
