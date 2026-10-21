"""ml_belu_test.py — walk-forward для BELU-NB_M10: ML on/off/adaptive."""
import numpy as np, pandas as pd
from pathlib import Path

CANDLES = Path('/root/finlab/data/candles')
COMMISSION = 0.0028; SLIPPAGE = 0.0002
COST = 2*COMMISSION + 2*SLIPPAGE
N_FOLDS = 3; WINDOW = 20; EXIT_Z = 0.5
TIME_EXIT_M10 = 120
ENTRY_Z = 1.8
PAIR = ('BELU', 'NB')
TF = 'M10'

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

def simulate(m, entry_z, use_ml='off', ml_threshold=0.5, window=WINDOW, exit_z=EXIT_Z, time_exit=TIME_EXIT_M10):
    """use_ml: 'off' (без ML) | 'fixed' (порог 0.5) | 'adaptive' (30-й перцентиль)."""
    df=m.copy()
    la=np.log(df['close_a'].values); lb=np.log(df['close_b'].values)
    beta=np.sum(la*lb)/np.sum(lb*lb)
    df['spread']=la-beta*lb
    df['mean']=df['spread'].rolling(window).mean()
    df['std']=df['spread'].rolling(window).std()
    df['z']=(df['spread']-df['mean'])/df['std']
    # Эмуляция ML: proba = 0.5 + 0.5*tanh(-z) — чем сильнее z, тем выше proba (для LONG)
    # Это заглушка, т.к. реальный ML не в этом скрипте. Но для теста логики — ок.
    df['ml_proba'] = 0.5 + 0.5*np.tanh(-df['z'])  # для LONG_SPREAD (z<0)
    pos=0; ep=0; ei=0; gross=[]
    ml_history = []
    for i in range(window, len(df)):
        z=df['z'].iloc[i]
        if pd.isna(z): continue
        if pos==0:
            if z>=entry_z or z<=-entry_z:
                # ML-фильтр
                allow = True
                if use_ml == 'fixed':
                    allow = df['ml_proba'].iloc[i] >= ml_threshold
                elif use_ml == 'adaptive':
                    if len(ml_history) >= 30:
                        thr = np.percentile(ml_history[-30:], 30)
                    else:
                        thr = 0.3  # начальный
                    allow = df['ml_proba'].iloc[i] >= thr
                if allow:
                    pos = -1 if z>=entry_z else 1
                    ep = df['spread'].iloc[i]; ei = i
                    ml_history.append(df['ml_proba'].iloc[i])
        else:
            if (i-ei)>=time_exit or abs(z)<=exit_z:
                gross.append((df['spread'].iloc[i]-ep)*pos); pos=0
    net=[g-COST for g in gross]
    return net

def stats(t):
    if not t: return {'n':0,'pnl':0,'wr':0,'sharpe':0}
    t=np.array(t); std=t.std()
    return {'n':len(t),'pnl':float(t.sum()),'wr':float((t>0).mean()),
            'sharpe': float(t.mean()/std*np.sqrt(252)) if std>0 else 0.0}

def main():
    print(f"PAIR={PAIR[0]}-{PAIR[1]}_{TF}, ENTRY_Z={ENTRY_Z}, COST={COST:.6f}")
    m = load_pair(PAIR[0], PAIR[1], TF)
    if m is None:
        print("NO DATA"); return
    n=len(m); fs=max(n//N_FOLDS, 100)
    print(f"rows={n}, fold_size={fs}")
    for use_ml in ['off', 'fixed', 'adaptive']:
        fold_results=[]
        for f in range(N_FOLDS):
            s=f*fs; e=(f+1)*fs if f<N_FOLDS-1 else n
            sub=m.iloc[s:e].reset_index(drop=True)
            if len(sub)<WINDOW+20: continue
            net=simulate(sub, ENTRY_Z, use_ml=use_ml)
            fold_results.append(stats(net))
        if not fold_results: continue
        tn=sum(r['n'] for r in fold_results)
        npnl=sum(r['pnl'] for r in fold_results)
        nz=[r for r in fold_results if r['n']>0]
        awr=float(np.mean([r['wr'] for r in nz])) if nz else 0.0
        ash=float(np.mean([r['sharpe'] for r in nz])) if nz else 0.0
        print(f"  ML={use_ml:10s}: n={tn:4d} NET={npnl:9.4f} wr={awr:.3f} net_sharpe={ash:7.3f}")

if __name__=='__main__': main()
