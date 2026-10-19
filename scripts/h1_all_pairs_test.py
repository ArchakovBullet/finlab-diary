"""h1_all_pairs_test.py — walk-forward OLS на ВСЕХ H1-парах из v2 config (disabled)."""
import json, numpy as np, pandas as pd
from pathlib import Path

CANDLES = Path('/root/finlab/data/candles')
CONFIG = Path('/root/finlab/FinLabPy/My_Indicators/pairs_config_v2.json')
COMMISSION = 0.0028; SLIPPAGE = 0.0002
COST = 2*COMMISSION + 2*SLIPPAGE
N_FOLDS = 3; WINDOW = 20; EXIT_Z = 0.5
TIME_EXIT_H1 = 120
ENTRY_Z_GRID = [1.5, 2.0, 2.5, 3.0]
TF = 'H1'

def load_pair(a, b, tf):
    fa = CANDLES / f'{a}_{tf}.parquet'; fb = CANDLES / f'{b}_{tf}.parquet'
    if not fa.exists() or not fb.exists(): return None
    da = pd.read_parquet(fa); db = pd.read_parquet(fb)
    _ca = 'begin' if 'begin' in da.columns else 'tradedate'
    _cb = 'begin' if 'begin' in db.columns else 'tradedate'
    a_df = da[[_ca,'close']].rename(columns={_ca:'dt'}).copy()
    b_df = db[[_cb,'close']].rename(columns={_cb:'dt'}).copy()
    a_df['dt'] = pd.to_datetime(a_df['dt'], errors='coerce')
    b_df['dt'] = pd.to_datetime(b_df['dt'], errors='coerce')
    a_df = a_df.dropna(subset=['dt']); b_df = b_df.dropna(subset=['dt'])
    m = pd.merge(a_df, b_df, on='dt', suffixes=('_a','_b'))
    m['close_a']=m['close_a'].apply(lambda x: float(x) if not isinstance(x,bytes) else 0.0)
    m['close_b']=m['close_b'].apply(lambda x: float(x) if not isinstance(x,bytes) else 0.0)
    m=m[(m['close_a']>0)&(m['close_b']>0)].reset_index(drop=True)
    if len(m)<100: return None
    return m.sort_values('dt').reset_index(drop=True)

def simulate(m, entry_z, window=WINDOW, exit_z=EXIT_Z, time_exit=TIME_EXIT_H1):
    df=m.copy()
    la=np.log(df['close_a'].values); lb=np.log(df['close_b'].values)
    beta_ols=np.sum(la*lb)/np.sum(lb*lb)
    df['spread']=la-beta_ols*lb
    df['mean']=df['spread'].rolling(window).mean()
    df['std']=df['spread'].rolling(window).std()
    df['z']=(df['spread']-df['mean'])/df['std']
    pos=0; ep=0; ei=0; gross=[]
    for i in range(window, len(df)):
        z=df['z'].iloc[i]
        if pd.isna(z): continue
        if pos==0:
            if z>=entry_z: pos=-1; ep=df['spread'].iloc[i]; ei=i
            elif z<=-entry_z: pos=1; ep=df['spread'].iloc[i]; ei=i
        else:
            if (i-ei)>=time_exit or abs(z)<=exit_z:
                gross.append((df['spread'].iloc[i]-ep)*pos); pos=0
    net=[g-COST for g in gross]
    return gross, net

def stats(t):
    if not t: return {'n':0,'pnl':0,'wr':0,'sharpe':0}
    t=np.array(t); std=t.std()
    return {'n':len(t),'pnl':float(t.sum()),'wr':float((t>0).mean()),
            'sharpe': float(t.mean()/std*np.sqrt(252)) if std>0 else 0.0}

def main():
    cfg = json.loads(CONFIG.read_text())
    pairs = [(k,v) for k,v in cfg["pairs"].items() if "_H1" in k]
    print(f"H1-пар в v2: {len(pairs)}")
    print(f"COST={COST:.6f}, N_FOLDS={N_FOLDS}, TIME_EXIT={TIME_EXIT_H1}")
    results = []
    for pair_name, pv in pairs:
        base = pair_name.replace("_H1","")
        a, b = base.split("-")
        m = load_pair(a, b, TF)
        if m is None:
            print(f"\n  [skip] {pair_name}: no data")
            results.append({"pair":pair_name,"n":0,"best_ez":None,"net_pnl":0,"wr":0,"sharpe":0,"status":"no_data"})
            continue
        n = len(m); fs = max(n//N_FOLDS, 100)
        la=np.log(m['close_a']); lb=np.log(m['close_b'])
        beta_ols=np.sum(la*lb)/np.sum(lb*lb)
        sp=(la-beta_ols*lb).abs()
        best = None
        for ez in ENTRY_Z_GRID:
            fold_results=[]
            for f in range(N_FOLDS):
                s=f*fs; e=(f+1)*fs if f<N_FOLDS-1 else n
                sub=m.iloc[s:e].reset_index(drop=True)
                if len(sub)<WINDOW+20: continue
                g,net=simulate(sub,ez)
                fold_results.append(stats(net))
            if not fold_results: continue
            tn=sum(r['n'] for r in fold_results)
            npnl=sum(r['pnl'] for r in fold_results)
            nz=[r for r in fold_results if r['n']>0]
            awr=float(np.mean([r['wr'] for r in nz])) if nz else 0.0
            ash=float(np.mean([r['sharpe'] for r in nz])) if nz else 0.0
            rec = {"ez":ez,"n":tn,"net_pnl":npnl,"wr":awr,"sharpe":ash}
            if best is None or (npnl > best["net_pnl"]):
                best = rec
        if best:
            status = "PROFIT" if best["net_pnl"] > 0 else "LOSS"
            print(f"\n== {pair_name} (rows={n}, |spread| mean={sp.mean():.5f})")
            print(f"  best: ez={best['ez']:.2f} n={best['n']:4d} NET={best['net_pnl']:9.4f} wr={best['wr']:.3f} sharpe={best['sharpe']:7.3f} [{status}]")
            results.append({"pair":pair_name,"n":best["n"],"best_ez":best["ez"],"net_pnl":best["net_pnl"],
                            "wr":best["wr"],"sharpe":best["sharpe"],"status":status})
        else:
            results.append({"pair":pair_name,"n":0,"best_ez":None,"net_pnl":0,"wr":0,"sharpe":0,"status":"no_trades"})
    out = Path('/root/finlab/logs') / 'h1_all_pairs_test.csv'
    pd.DataFrame(results).to_csv(out, index=False)
    print(f"\nOK CSV: {out}")
    profit = [r for r in results if r["status"]=="PROFIT"]
    print(f"\n=== ПРИБЫЛЬНЫЕ H1-пары ({len(profit)}/{len(results)}) ===")
    for r in sorted(profit, key=lambda x: x["net_pnl"], reverse=True):
        print(f"  {r['pair']:20s} ez={r['best_ez']:.2f} net_pnl={r['net_pnl']:9.4f} wr={r['wr']:.3f} sharpe={r['sharpe']:7.3f} n={r['n']}")

if __name__=='__main__': main()
