"""v4_multiple_entry_test.py — walk-forward: multiple entry_z (1.5/2.0/2.5, разные размеры) vs single."""
import numpy as np, pandas as pd
from pathlib import Path

CANDLES = Path('/root/finlab/data/candles')
COMMISSION = 0.0028; SLIPPAGE = 0.0002
COST = 2*COMMISSION + 2*SLIPPAGE
N_FOLDS = 3; WINDOW = 20; EXIT_Z = 0.5
TIME_EXIT_H4 = 30; TIME_EXIT_M10 = 120
PAIRS = [
    ('SFIN','SH','M10'), ('BANE','BN','M10'), ('BELU','NB','M10'),
    ('GD','SV','H4'), ('PD','SV','H4'), ('PT','SV','H4'), ('LK','IMOEXF','H4'),
]
# Multiple entry_z: (порог, размер)
MULTIPLE = [(1.5, 0.25), (2.0, 0.50), (2.5, 1.0)]
SINGLE = {'M10': 1.8, 'H4': 2.0}

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

def calc_z(m, window=WINDOW):
    df = m.copy()
    la = np.log(df['close_a'].values); lb = np.log(df['close_b'].values)
    beta = np.sum(la*lb) / np.sum(lb*lb)
    df['spread'] = la - beta*lb
    df['mean'] = df['spread'].rolling(window).mean()
    df['std'] = df['spread'].rolling(window).std()
    df['z'] = (df['spread'] - df['mean']) / df['std']
    return df

def simulate_single(m, entry_z, tf, window=WINDOW, exit_z=EXIT_Z):
    df = calc_z(m, window)
    time_exit = TIME_EXIT_M10 if tf == 'M10' else TIME_EXIT_H4
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
    return [g-COST for g in gross]

def simulate_multiple(m, tf, window=WINDOW, exit_z=EXIT_Z):
    df = calc_z(m, window)
    time_exit = TIME_EXIT_M10 if tf == 'M10' else TIME_EXIT_H4
    positions = []  # список (direction, entry_price, entry_i, size)
    gross = []
    for i in range(window, len(df)):
        z=df['z'].iloc[i]
        if pd.isna(z): continue
        # Проверяем выход для всех открытых
        for j in range(len(positions)-1, -1, -1):
            d, ep, ei, sz = positions[j]
            if (i-ei)>=time_exit or abs(z)<=exit_z:
                gross.append((df['spread'].iloc[i]-ep)*d*sz); positions.pop(j)
        # Проверяем вход (multiple)
        for thr, sz in MULTIPLE:
            if z>=thr:
                positions.append((-1, df['spread'].iloc[i], i, sz))
                break  # только один вход за бар
            elif z<=-thr:
                positions.append((1, df['spread'].iloc[i], i, sz))
                break
    # Закрываем оставшиеся в конце
    for d, ep, ei, sz in positions:
        gross.append((df['spread'].iloc[-1]-ep)*d*sz)
    # Cost: за каждую сделку (вход+выход)
    return [g - COST*sz for g, sz in zip(gross, [1]*len(gross))]

def stats(t):
    if not t: return {'n':0,'pnl':0,'wr':0,'sharpe':0}
    t=np.array(t); std=t.std()
    return {'n':len(t),'pnl':float(t.sum()),'wr':float((t>0).mean()),
            'sharpe': float(t.mean()/std*np.sqrt(252)) if std>0 else 0.0}

def walk_one(m, tf, mode='single'):
    n=len(m); fs=max(n//N_FOLDS, 100)
    results=[]
    for f in range(N_FOLDS):
        s=f*fs; e=(f+1)*fs if f<N_FOLDS-1 else n
        sub=m.iloc[s:e].reset_index(drop=True)
        if len(sub)<WINDOW+20: continue
        if mode=='single':
            net=simulate_single(sub, SINGLE[tf], tf)
        else:
            net=simulate_multiple(sub, tf)
        results.append(stats(net))
    if not results: return {'n':0,'pnl':0,'wr':0,'sharpe':0}
    tn=sum(r['n'] for r in results); npnl=sum(r['pnl'] for r in results)
    nz=[r for r in results if r['n']>0]
    awr=float(np.mean([r['wr'] for r in nz])) if nz else 0.0
    ash=float(np.mean([r['sharpe'] for r in nz])) if nz else 0.0
    return {'n':tn,'pnl':npnl,'wr':awr,'sharpe':ash}

def main():
    print(f"Multiple entry_z: {MULTIPLE}")
    print(f"Single: M10={SINGLE['M10']}, H4={SINGLE['H4']}")
    print(f"COST={COST:.6f}, N_FOLDS={N_FOLDS}")
    for a,b,tf in PAIRS:
        m=load_pair(a,b,tf)
        if m is None: print(f"  [skip] {a}-{b}_{tf}: no data"); continue
        print(f"\n== {a}-{b}_{tf} (rows={len(m)}) ==")
        s = walk_one(m, tf, 'single')
        print(f"  single ({SINGLE[tf]}): n={s['n']:4d} NET={s['pnl']:9.4f} wr={s['wr']:.3f} sharpe={s['sharpe']:7.3f}")
        mu = walk_one(m, tf, 'multiple')
        print(f"  multiple (1.5/2.0/2.5): n={mu['n']:4d} NET={mu['pnl']:9.4f} wr={mu['wr']:.3f} sharpe={mu['sharpe']:7.3f}")

if __name__=='__main__': main()
