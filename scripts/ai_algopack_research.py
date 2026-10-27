#!/usr/bin/env python3
"""
ai_algopack_research.py — AI-исследование Algopack (SBER/GAZP/LKOH).
Read-only. v2/v3/v4 не трогает. Пишет CSV в logs/, отчёт в stdout.

Источники:
  - candles/{TICKER}_H1.parquet (цена H1)
  - futoi_1h.parquet (ticker='{TICKER}F' — FutOI по фьючерсу)
  - tradestats/{TICKER}_tradestats.parquet (цены/объёмы/волатильность)
  - mega_alerts/{TICKER}_alerts.parquet (+ {TICKER}F_alerts.parquet)
  - hi2_daily.parquet (ticker in TICKER/TICKERF/TICKERP)
  - sector_indices/MOEXFN_D1.parquet (сектор D1)
"""
import os
import numpy as np
import pandas as pd

ROOT = "/root/finlab"
OUT_DIR = os.path.join(ROOT, "logs")
TICKERS = ["SBER", "GAZP", "LKOH"]
LAGS_H = [0, 1, 2, 4, 8]
EVENT_LAGS_H = [0, 1, 2, 4, 8]

def _load(path, cols=None):
    if not os.path.exists(path): return None
    df = pd.read_parquet(path)
    if cols: df = df[[c for c in cols if c in df.columns]]
    return df

def load_price_h1(t):
    p = f"{ROOT}/data/candles/{t}_H1.parquet"
    df = _load(p)
    if df is None: return None
    cols = {c.lower(): c for c in df.columns}
    df = df.rename(columns={cols.get("begin","begin"): "begin", cols.get("close","close"): "close"})
    df["begin"] = pd.to_datetime(df["begin"], errors="coerce")
    df = df.dropna(subset=["begin","close"]).sort_values("begin").reset_index(drop=True)
    return df[["begin","close"]].rename(columns={"close":"price"})

def load_futoi_h1(tfut):
    p = f"{ROOT}/data/futoi_1h/futoi_1h.parquet"
    df = _load(p)
    if df is None or "ticker" not in df.columns: return None
    d = df[df["ticker"] == tfut].copy()
    if d.empty: return None
    tcol = "hour" if "hour" in d.columns else ("begin" if "begin" in d.columns else None)
    if tcol is None: return None
    d[tcol] = pd.to_datetime(d[tcol], errors="coerce")
    d = d.dropna(subset=[tcol]).sort_values(tcol).reset_index(drop=True)
    keep = [tcol] + [c for c in ["fiz_long","fiz_short","yur_long","yur_short","fiz_total","yur_total"] if c in d.columns]
    return d[keep].rename(columns={tcol:"begin"})

def load_tradestats_h1(t):
    p = f"{ROOT}/data/tradestats/{t}_tradestats.parquet"
    df = _load(p)
    if df is None: return None
    if "tradedate" in df.columns and "tradetime" in df.columns:
        dt = pd.to_datetime(df["tradedate"].astype(str) + " " + df["tradetime"].astype(str), errors="coerce")
        df = df.assign(begin=dt)
    elif "begin" in df.columns:
        df["begin"] = pd.to_datetime(df["begin"], errors="coerce")
    else: return None
    keep = ["begin"] + [c for c in ["vol","val","pr_close","pr_std"] if c in df.columns]
    return df[keep].dropna(subset=["begin"]).sort_values("begin").reset_index(drop=True)

def load_mega(t):
    p = f"{ROOT}/data/mega_alerts/{t}_alerts.parquet"
    df = _load(p)
    if df is None: return None
    if "tradedate" in df.columns and "tradetime" in df.columns:
        dt = pd.to_datetime(df["tradedate"].astype(str) + " " + df["tradetime"].astype(str), errors="coerce")
        df = df.assign(begin=dt)
    elif "SYSTIME" in df.columns:
        df = df.assign(begin=pd.to_datetime(df["SYSTIME"], errors="coerce"))
    else: return None
    keep = ["begin"] + [c for c in ["alert_type","threshold","value"] if c in df.columns]
    return df[keep].dropna(subset=["begin"]).sort_values("begin").reset_index(drop=True)

def load_hi2_d1():
    p = f"{ROOT}/data/hi2_daily.parquet"
    df = _load(p)
    if df is None or "ticker" not in df.columns: return None
    tickers = []
    for t in TICKERS: tickers += [t, t+"F", t+"P"]
    d = df[df["ticker"].isin(tickers)].copy()
    if d.empty: return None
    tcol = "tradedate" if "tradedate" in d.columns else ("begin" if "begin" in d.columns else None)
    if tcol is None: return None
    d[tcol] = pd.to_datetime(d[tcol], errors="coerce")
    keep = [tcol,"ticker"] + [c for c in ["hhi_agressive","hhi_netflow_buy","hhi_netflow_sell"] if c in d.columns]
    d = d[keep].dropna(subset=[tcol]).sort_values(tcol).reset_index(drop=True)
    d = d.rename(columns={tcol: "begin"})
    return d

def load_sector_d1():
    p = f"{ROOT}/data/sector_indices/MOEXFN_D1.parquet"
    df = _load(p)
    if df is None: return None
    if "begin" in df.columns and "close" in df.columns:
        df["begin"] = pd.to_datetime(df["begin"], errors="coerce")
        return df[["begin","close"]].dropna().sort_values("begin").reset_index(drop=True).rename(columns={"close":"sector"})
    return None

def corr_table(t, price_h1, futoi_h1, tradestats_h1):
    rows = []
    if price_h1 is None or futoi_h1 is None: return rows
    m = pd.merge(price_h1, futoi_h1, on="begin", how="inner").sort_values("begin")
    if len(m) < 30: return rows
    m["ret"] = np.log(m["price"]).diff()
    for col in ["fiz_long","fiz_short","yur_long","yur_short","fiz_total","yur_total"]:
        if col not in m.columns: continue
        m[col] = pd.to_numeric(m[col], errors="coerce")
        for lag in LAGS_H:
            c = m["ret"].corr(m[col].shift(lag))
            if pd.notna(c):
                rows.append({"ticker":t,"source":"futoi","feature":col,"target":f"{t}_ret_H1","lag_h":lag,"corr":round(float(c),4),"n":int(m["ret"].notna().sum())})
    if tradestats_h1 is not None:
        mt = pd.merge(m[["begin","ret"]], tradestats_h1, on="begin", how="inner").sort_values("begin")
        if len(mt) >= 30:
            for col in ["vol","val","pr_std"]:
                if col not in mt.columns: continue
                mt[col] = pd.to_numeric(mt[col], errors="coerce")
                for lag in LAGS_H:
                    c = mt["ret"].corr(mt[col].shift(lag))
                    if pd.notna(c):
                        rows.append({"ticker":t,"source":"tradestats","feature":col,"target":f"{t}_ret_H1","lag_h":lag,"corr":round(float(c),4),"n":int(mt["ret"].notna().sum())})
    return rows

def divergence_rows(t, price_h1, futoi_h1):
    rows = []
    if price_h1 is None or futoi_h1 is None: return rows
    m = pd.merge(price_h1, futoi_h1, on="begin", how="inner").sort_values("begin")
    if len(m) < 50: return rows
    m["ret"] = np.log(m["price"]).diff()
    for col in ["fiz_total","yur_total"]:
        if col not in m.columns: continue
        s = pd.to_numeric(m[col], errors="coerce").diff()
        div = (np.sign(m["ret"]) != np.sign(s)) & m["ret"].notna() & s.notna()
        if div.any():
            m["fwd_ret"] = m["ret"].shift(-1)
            sub = m[div].dropna(subset=["fwd_ret"])
            if len(sub) >= 10:
                rows.append({"ticker":t,"source":"futoi","feature":col,"event":"divergence",
                             "n":int(len(sub)),"mean_fwd_ret":round(float(sub["fwd_ret"].mean()),6),
                             "wr":round(float((sub["fwd_ret"]>0).mean()),3)})
    return rows

def mega_rows(t, price_h1, mega):
    rows = []
    if price_h1 is None or mega is None or mega.empty: return rows
    p = price_h1.set_index("begin").sort_index()["price"]
    for _, r in mega.iterrows():
        tt = r["begin"]
        if pd.isna(tt): continue
        idx = p.index.searchsorted(tt)
        if idx >= len(p): continue
        p0 = p.iloc[idx]
        for lag in EVENT_LAGS_H:
            j = idx + lag
            if j >= len(p): continue
            ret = float(np.log(p.iloc[j] / p0)) if p0 > 0 else np.nan
            if np.isnan(ret): continue
            rows.append({"ticker":t,"event_time":str(tt),"alert_type":r.get("alert_type"),
                         "threshold":r.get("threshold"),"value":r.get("value"),"lag_h":lag,"fwd_ret":round(ret,6)})
    return rows

def hi2_rows(t, price_h1, hi2):
    rows = []
    if price_h1 is None or hi2 is None or hi2.empty: return rows
    p = price_h1.copy(); p["date"] = p["begin"].dt.normalize()
    p_d1 = p.groupby("date")["price"].last().reset_index().rename(columns={"date":"begin"})
    p_d1["ret_d1"] = np.log(p_d1["price"]).diff()
    for tk in hi2["ticker"].unique():
        h = hi2[hi2["ticker"]==tk].copy()
        h["begin"] = pd.to_datetime(h["begin"], errors="coerce").dt.normalize()
        m = pd.merge(p_d1, h, on="begin", how="inner").sort_values("begin")
        if len(m) < 30: continue
        for col in ["hhi_agressive","hhi_netflow_buy","hhi_netflow_sell"]:
            if col not in m.columns: continue
            x = pd.to_numeric(m[col], errors="coerce")
            for lag in LAGS_H:
                c = m["ret_d1"].corr(x.shift(lag))
                if pd.notna(c):
                    rows.append({"ticker":t,"source":"hi2","hi2_ticker":tk,"feature":col,
                                 "target":f"{t}_ret_D1","lag_h":lag,"corr":round(float(c),4),"n":int(m["ret_d1"].notna().sum())})
    return rows

def sector_divergence(t, price_h1, sector):
    rows = []
    if price_h1 is None or sector is None: return rows
    p = price_h1.copy(); p["date"] = p["begin"].dt.normalize()
    p_d1 = p.groupby("date")["price"].last().reset_index().rename(columns={"date":"begin"})
    p_d1["ret_x"] = np.log(p_d1["price"]).diff()
    s = sector.copy(); s["begin"] = pd.to_datetime(s["begin"], errors="coerce").dt.normalize()
    s["ret_sector"] = np.log(s["sector"]).diff()
    m = pd.merge(p_d1[["begin","ret_x"]], s[["begin","ret_sector"]], on="begin", how="inner").dropna()
    if len(m) < 30: return rows
    c = m["ret_x"].corr(m["ret_sector"])
    rows.append({"ticker":t,"source":"sector","feature":"MOEXFN_ret_D1","target":f"{t}_ret_D1","lag_h":0,"corr":round(float(c),4),"n":int(len(m))})
    div = (np.sign(m["ret_x"]) != np.sign(m["ret_sector"])) & m["ret_x"].notna() & m["ret_sector"].notna()
    if div.any():
        sub = m[div]
        rows.append({"ticker":t,"source":"sector","feature":"MOEXFN_ret_D1","target":f"{t}_ret_D1","lag_h":"divergence",
                     "corr":None,"n":int(len(sub)),
                     "mean_ticker":round(float(sub["ret_x"].mean()),6),
                     "mean_sector":round(float(sub["ret_sector"].mean()),6)})
    return rows

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    sector = load_sector_d1()
    hi2 = load_hi2_d1()
    out = []
    for t in TICKERS:
        tfut = t + "F"
        price_h1 = load_price_h1(t)
        futoi_h1 = load_futoi_h1(tfut)
        tradestats_h1 = load_tradestats_h1(t)
        mega_stock = load_mega(t)
        mega_fut = load_mega(tfut)
        print(f"=== {t} ===")
        for name, obj in [("price_h1",price_h1),("futoi_h1",futoi_h1),("tradestats_h1",tradestats_h1),
                          ("mega_stock",mega_stock),("mega_fut",mega_fut)]:
            n = len(obj) if obj is not None else 0
            print(f"  {name}: {n}")
        out.extend(corr_table(t, price_h1, futoi_h1, tradestats_h1))
        out.extend(divergence_rows(t, price_h1, futoi_h1))
        for tag, mg in [(f"mega_{t}",mega_stock),(f"mega_{tfut}",mega_fut)]:
            ev = mega_rows(t, price_h1, mg)
            if ev:
                ev_df = pd.DataFrame(ev)
                agg = ev_df.groupby(["alert_type","lag_h"]).agg(n=("fwd_ret","size"), mean_fwd_ret=("fwd_ret","mean")).reset_index()
                for _, r in agg.iterrows():
                    out.append({"ticker":t,"source":tag,"feature":str(r["alert_type"]),"target":f"{t}_fwd_ret",
                                "lag_h":int(r["lag_h"]),"corr":None,"n":int(r["n"]),
                                "mean_fwd_ret":round(float(r["mean_fwd_ret"]),6)})
        out.extend(hi2_rows(t, price_h1, hi2))
        out.extend(sector_divergence(t, price_h1, sector))

    df = pd.DataFrame(out)
    ts = pd.Timestamp.now().strftime("%Y-%m-%d_%H%M")
    path = os.path.join(OUT_DIR, f"ai_algopack_multi_{ts}.csv")
    df.to_csv(path, index=False)
    print(f"\nСохранено: {path}  (rows={len(df)})")

    if not df.empty:
        cdf = df[df["corr"].notna()].copy()
        if not cdf.empty:
            cdf["abs_corr"] = cdf["corr"].abs()
            print("\n=== Топ-20 |corr| (все тикеры) ===")
            for _, r in cdf.sort_values("abs_corr", ascending=False).head(20).iterrows():
                extra = f" [{r.get('hi2_ticker','')}]" if pd.notna(r.get('hi2_ticker')) else ""
                print(f"  {r['ticker']:5s} {r['source']:10s} {str(r['feature'])[:18]:18s}{extra} -> {r['target']:14s} lag={r['lag_h']:>3} corr={r['corr']:+.3f} n={int(r['n'])}")
        ev = df[df["corr"].isna()].head(20)
        if not ev.empty:
            print("\n=== События / divergence (первые 20) ===")
            for _, r in ev.iterrows():
                print("  ", {k:r[k] for k in r.index if pd.notna(r[k])})

if __name__ == "__main__":
    main()
