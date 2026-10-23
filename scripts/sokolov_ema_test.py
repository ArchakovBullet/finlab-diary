#!/usr/bin/env python3
"""
sokolov_ema_test.py — тест сглаживания EMA (по мотивам Соколова, гл. 2.3).
Read-only. v2/v3 не трогает. Пишет результат в logs/.

Варианты (5):
  1. baseline      — сырой спред, OLS β на train, z на test.
  2. ema3_spread   — сглаживаем спред EMA-3.
  3. ema5_spread   — сглаживаем спред EMA-5.
  4. ema3_legs     — сглаживаем каждую ногу EMA-3, потом спред.
  5. ema5_legs     — сглаживаем каждую ногу EMA-5, потом спред.

Walk-forward: скользящее окно train=30д, test=7д, шаг=7д.
entry_z=1.8, exit_z=0.5, fee=0.28% (0.14*2) + slip=0.02%*2.

Пары: SFIN-SH_M10, BANE-BN_M10, BELU-NB_M10.
"""
import os, sys, glob
import numpy as np
import pandas as pd

PAIRS = [
    ("SFIN-SH_M10",  "SFIN",  "SH"),
    ("BANE-BN_M10",  "BANE",  "BN"),
    ("BELU-NB_M10",  "BELU",  "NB"),
]
ENTRY_Z = 1.8
EXIT_Z  = 0.5
FEE     = 0.0028   # 0.14% * 2
SLIP    = 0.0004   # 0.02% * 2
TRAIN_D = 30
TEST_D  = 7
STEP_D  = 7
DATA_DIR = "data/candles"
OUT_DIR  = "logs"

def load_m10(ticker):
    path = os.path.join(DATA_DIR, f"{ticker}_M10.parquet")
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    df = pd.read_parquet(path)
    # нормализуем колонки
    cols = {c.lower(): c for c in df.columns}
    need = ["begin", "close"]
    for n in need:
        if n not in cols:
            raise ValueError(f"{path}: нет колонки {n}. Есть: {list(df.columns)}")
    df = df.rename(columns={cols["begin"]: "begin", cols["close"]: "close"})
    df["begin"] = pd.to_datetime(df["begin"], errors="coerce", utc=False)
    df = df.dropna(subset=["begin", "close"]).sort_values("begin").reset_index(drop=True)
    return df[["begin", "close"]]

def ols_beta(logA, logB):
    # logA = a + b*logB  ->  b = cov/var
    x = logB.values; y = logA.values
    xm, ym = x.mean(), y.mean()
    var = ((x - xm) ** 2).mean()
    if var == 0 or np.isnan(var):
        return np.nan
    return ((x - xm) * (y - ym)).mean() / var

def build_spread(dfA, dfB, mode, beta=None):
    """
    mode: 'baseline' | 'ema3_spread' | 'ema5_spread' | 'ema3_legs' | 'ema5_legs'
    Возвращает DataFrame с begin, spread, z.
    β: если None — OLS по всему переданному куску (для train-фолда).
    """
    m = pd.merge(dfA, dfB, on="begin", suffixes=("_A", "_B")).dropna()
    if len(m) < 50:
        return None
    logA = np.log(m["close_A"].replace(0, np.nan))
    logB = np.log(m["close_B"].replace(0, np.nan))
    m = m.assign(logA=logA.values, logB=logB.values).dropna()
    if len(m) < 50:
        return None

    b = beta if beta is not None and not np.isnan(beta) else ols_beta(m["logA"], m["logB"])
    if b is None or np.isnan(b) or b == 0:
        return None

    if mode == "baseline":
        s = m["logA"] - b * m["logB"]
    elif mode == "ema3_spread":
        raw = m["logA"] - b * m["logB"]
        s = raw.ewm(span=3, adjust=False).mean()
    elif mode == "ema5_spread":
        raw = m["logA"] - b * m["logB"]
        s = raw.ewm(span=5, adjust=False).mean()
    elif mode == "ema3_legs":
        sA = m["logA"].ewm(span=3, adjust=False).mean()
        sB = m["logB"].ewm(span=3, adjust=False).mean()
        s = sA - b * sB
    elif mode == "ema5_legs":
        sA = m["logA"].ewm(span=5, adjust=False).mean()
        sB = m["logB"].ewm(span=5, adjust=False).mean()
        s = sA - b * sB
    else:
        raise ValueError(mode)

    s = s.replace([np.inf, -np.inf], np.nan).dropna()
    if len(s) < 50:
        return None
    mu = s.mean(); sd = s.std(ddof=1)
    if sd == 0 or np.isnan(sd):
        return None
    z = (s - mu) / sd
    out = pd.DataFrame({"begin": m.loc[s.index, "begin"].values, "spread": s.values, "z": z.values})
    return out, b

def walk_forward_pair(name, A, B):
    dfA = load_m10(A); dfB = load_m10(B)
    if len(dfA) < 100 or len(dfB) < 100:
        print(f"[{name}] мало данных, пропуск"); return []

    modes = ["baseline", "ema3_spread", "ema5_spread", "ema3_legs", "ema5_legs"]
    rows = []
    start = dfA["begin"].min()
    end   = dfA["begin"].max()
    t0 = start
    fold = 0
    while t0 + pd.Timedelta(days=TRAIN_D+TEST_D) <= end:
        train_end = t0 + pd.Timedelta(days=TRAIN_D)
        test_end  = train_end + pd.Timedelta(days=TEST_D)
        fold += 1
        dA_tr = dfA[(dfA.begin >= t0) & (dfA.begin < train_end)]
        dB_tr = dfB[(dfB.begin >= t0) & (dfB.begin < train_end)]
        dA_te = dfA[(dfA.begin >= train_end) & (dfA.begin < test_end)]
        dB_te = dfB[(dfB.begin >= train_end) & (dfB.begin < test_end)]

        if len(dA_tr) < 100 or len(dB_tr) < 100 or len(dA_te) < 50 or len(dB_te) < 50:
            t0 += pd.Timedelta(days=STEP_D); continue

        # β на train
        m_tr = pd.merge(dA_tr, dB_tr, on="begin", suffixes=("_A","_B"))
        if len(m_tr) < 50:
            t0 += pd.Timedelta(days=STEP_D); continue
        b_tr = ols_beta(np.log(m_tr["close_A"].replace(0,np.nan)),
                        np.log(m_tr["close_B"].replace(0,np.nan)))
        if b_tr is None or np.isnan(b_tr) or b_tr == 0:
            t0 += pd.Timedelta(days=STEP_D); continue

        for mode in modes:
            res = build_spread(dA_te, dB_te, mode, beta=b_tr)
            if res is None:
                rows.append({"pair": name, "mode": mode, "fold": fold,
                             "trades": 0, "pnl": 0.0, "wr": 0.0, "sharpe": 0.0, "n_z": 0})
                continue
            zdf, b = res
            # симуляция: вход при |z|>=ENTRY_Z, выход при |z|<=EXIT_Z или в конце
            pos = 0; entry_z = None; entry_price = None
            trades = []
            for _, r in zdf.iterrows():
                z = r["z"]
                if pos == 0:
                    if abs(z) >= ENTRY_Z:
                        pos = -1 if z > 0 else 1
                        entry_z = z
                        entry_price = r["spread"]
                else:
                    if abs(z) <= EXIT_Z:
                        exit_price = r["spread"]
                        direction = 1 if pos == 1 else -1
                        gross = direction * (exit_price - entry_price)
                        net = gross - 2*(FEE/2 + SLIP/2)  # упрощённо
                        trades.append(net)
                        pos = 0
            # если остался открытый — закрываем в конце
            if pos != 0:
                exit_price = zdf.iloc[-1]["spread"]
                direction = 1 if pos == 1 else -1
                gross = direction * (exit_price - entry_price)
                net = gross - 2*(FEE/2 + SLIP/2)
                trades.append(net)
            if not trades:
                rows.append({"pair": name, "mode": mode, "fold": fold,
                             "trades": 0, "pnl": 0.0, "wr": 0.0, "sharpe": 0.0, "n_z": len(zdf)})
            else:
                t = np.array(trades, dtype=float)
                pnl = t.sum()
                wr = (t > 0).mean()
                if t.std(ddof=1) > 0:
                    sharpe = t.mean() / t.std(ddof=1) * np.sqrt(len(t))
                else:
                    sharpe = 0.0
                rows.append({"pair": name, "mode": mode, "fold": fold,
                             "trades": len(t), "pnl": pnl, "wr": wr, "sharpe": sharpe, "n_z": len(zdf)})
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
            print(f"  [ERR] {e}")
            continue
        for r in rows:
            print(f"  fold={r['fold']} mode={r['mode']:14s} trades={r['trades']:3d} "
                  f"pnl={r['pnl']:+.4f} wr={r['wr']:.3f} sharpe={r['sharpe']:+.2f}")
        all_rows.extend(rows)
    if all_rows:
        out = pd.DataFrame(all_rows)
        ts = pd.Timestamp.now().strftime("%Y-%m-%d_%H%M")
        path = os.path.join(OUT_DIR, f"sokolov_ema_{ts}.csv")
        out.to_csv(path, index=False)
        print(f"\nСохранено: {path}")
        print("\n=== Сводка по mode (сумма по фолдам) ===")
        agg = out.groupby(["pair","mode"]).agg(
            trades=("trades","sum"), pnl=("pnl","sum"),
            wr=("wr","mean"), sharpe=("sharpe","mean"), folds=("fold","count")
        ).reset_index()
        print(agg.to_string(index=False))
    else:
        print("Нет данных для сохранения.")

if __name__ == "__main__":
    main()
