"""kalman_m10_delta_test.py — проверка: окупается ли cost на M10 при быстром Кальмане (delta=1e-2)."""
import json, numpy as np, pandas as pd
from pathlib import Path

CANDLES = Path('/root/finlab/data/candles')
CONFIG_V3 = Path('/root/finlab/FinLabPy/My_Indicators/pairs_config_v3.json')
COMMISSION = 0.0028; SLIPPAGE = 0.0002
COST = 2*COMMISSION + 2*SLIPPAGE
N_FOLDS = 5; WINDOW = 20; EXIT_Z = 0.5; TIME_EXIT_M10 = 120
ENTRY_Z_GRID = [1.2, 1.5, 1.8, 2.0, 2.5, 3.0]
DELTAS = [1e-4, 1e-3, 1e-2, 1e-1]

def load_pair(a, b, tf):
    fa = CANDLES / f'{a}_{tf}.parquet'; fb = CANDLES / f'{b}_{tf}.parquet'
    if not fa.exists() or not fb.exists(): return None
    da = pd.read_parquet(fa); db = pd.read_parquet(fb)
    _ca = 'begin' if 'begin' in da.columns else 'tradedate'
    _cb = 'begin' if 'begin' in db.columns else 'tradedate'
    m = pd.merge(da[[_ca,'close']].rename(columns={_ca:'dt'}),
                 db[[_cb,'close']].rename(columns={_cb:'dt'}),
                 on='dt', suffixes=('_a','_b'))
    m['close_a']=m['close_a'].apply(lambda x: float(x) if not isinstance(x,bytes) else 0.0)
    m['close_b']=m['close_b'].apply(lambda x: float(x) if not isinstance(x,bytes) else 0.0)
    m=m[(m['close_a']>0)&(m['close_b']>0)].reset_index(drop=True)
    if len(m)<200: return None
    return m.sort_values('dt').reset_index(drop=True)

def kalman_beta(y, x, delta):
    n=len(y); beta=np.zeros(n); P=np.zeros(n)
    beta[0]=1.0; P[0]=1.0; Q=delta; R=1e-3
    for t in range(1,n):
        bp=beta[t-1]; Pp=P[t-1]+Q; H=x[t]; S=H*Pp*H+R; K=Pp*H/S
        beta[t]=bp+K*(y[t]-H*bp); P[t]=(1-K*H)*Pp
    return beta

def simulate(m, entry_z, delta, window=WINDOW, exit_z=EXIT_Z, time_exit=TIME_EXIT_M10, warmup=100):
    df=m.copy()
    la=np.log(df['close_a'].values); lb=np.log(df['close_b'].values)
    beta=kalman_beta(la,lb,delta)
    df['spread']=la-beta*lb
    df['mean']=df['spread'].rolling(window).mean()
    df['std']=df['spread'].rolling(window).std()
    df['z']=(df['spread']-df['mean'])/df['std']
    pos=0; ep=0; ei=0; gross=[]
    for i in range(max(window,warmup), len(df)):
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
    cfg=json.loads(CONFIG_V3.read_text())
    m10_pairs=[(k,v) for k,v in cfg['pairs'].items() if v.get('enabled') and '_M10' in k]
    print(f"M10 enabled-пар: {len(m10_pairs)}")
    print(f"COST={COST:.6f}, deltas={DELTAS}")
    rows=[]
    for pair_name, pv in m10_pairs:
        base=pair_name.replace('_M10','')
        a,b=base.split('-')
        m=load_pair(a,b,'M10')
        if m is None: print(f"  [skip] {pair_name}: no data"); continue
        n=len(m); fs=n//N_FOLDS
        print(f"\n== {pair_name} (rows={n}, fold_size={fs})")
        for delta in DELTAS:
            for ez in ENTRY_Z_GRID:
                fold_results=[]
                for f in range(N_FOLDS):
                    s=f*fs; e=(f+1)*fs if f<N_FOLDS-1 else n
                    sub=m.iloc[s:e].reset_index(drop=True)
                    if len(sub)<WINDOW+20: continue
                    g,net=simulate(sub,ez,delta)
                    fold_results.append(stats(net))
                if not fold_results: continue
                tn=sum(r['n'] for r in fold_results)
                npnl=sum(r['pnl'] for r in fold_results)
                nz=[r for r in fold_results if r['n']>0]
                awr=float(np.mean([r['wr'] for r in nz])) if nz else 0.0
                ash=float(np.mean([r['sharpe'] for r in nz])) if nz else 0.0
                print(f"  delta={delta:.0e} ez={ez:.2f}: n={tn:4d} NET={npnl:9.4f} wr={awr:.3f} net_sharpe={ash:7.3f}")
                rows.append({'pair':pair_name,'delta':delta,'entry_z':ez,
                             'n':tn,'net_pnl':npnl,'wr':awr,'net_sharpe':ash})
    out=Path('/root/finlab/logs')/f'kalman_m10_delta_{pd.Timestamp.now().date()}.csv'
    pd.DataFrame(rows).to_csv(out,index=False)
    print(f"\n✅ CSV: {out}")
    if rows:
        df=pd.DataFrame(rows)
        print("\n=== ЛУЧШИЙ (delta, entry_z) ПО ПАРЕ (по net_sharpe, только net_pnl>0) ===")
        for pair in df['pair'].unique():
            sub=df[(df['pair']==pair)&(df['net_pnl']>0)]
            if sub.empty:
                print(f"  {pair:20s}: NO POSITIVE (net_pnl<=0 при всех delta/entry_z)")
                continue
            best=sub.loc[sub['net_sharpe'].idxmax()]
            print(f"  {pair:20s}: delta={best['delta']:.0e} entry_z={best['entry_z']:.2f} net_pnl={best['net_pnl']:9.4f} net_sharpe={best['net_sharpe']:7.3f} n={int(best['n'])}")

if __name__=='__main__': main()
