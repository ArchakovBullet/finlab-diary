#!/bin/bash
cd /root/finlab
FILE=robots/pairs_robot.py
cp "$FILE" "$FILE.bak_coint_zscore_$(date +%Y%m%d_%H%M%S)"

/root/finlab/venv/bin/python << 'PYEOF'
from pathlib import Path

p = Path('/root/finlab/robots/pairs_robot.py')
text = p.read_text()

# Найти текущую calculate_zscore
import re
m = re.search(r'def calculate_zscore\([^)]*\):.*?(?=\ndef |\Z)', text, re.DOTALL)
if not m:
    print('НЕ НАЙДЕНО: calculate_zscore')
    exit(1)

print('Текущая calculate_zscore:')
print(m.group(0)[:600])
print('---')

# Новая версия — с use_coint
new_func = '''def calculate_zscore(df_a, df_b, window=20, use_coint=False, resid_window=60):
    """Z-score спреда.

    Если use_coint=True — rolling OLS residuals:
        log_a = beta * log_b + alpha + resid
        z-score по resid.
    Иначе — простой spread = log_a - log_b.
    """
    _ca = 'begin' if 'begin' in df_a.columns else 'tradedate'
    _cb = 'begin' if 'begin' in df_b.columns else 'tradedate'
    a = df_a[[_ca, 'close']].rename(columns={_ca: 'dt'})
    b = df_b[[_cb, 'close']].rename(columns={_cb: 'dt'})
    m = pd.merge(a, b, on='dt', suffixes=('_a', '_b')).sort_values('dt').reset_index(drop=True)
    m['close_a'] = m['close_a'].apply(lambda x: float(x) if not isinstance(x, bytes) else 0.0)
    m['close_b'] = m['close_b'].apply(lambda x: float(x) if not isinstance(x, bytes) else 0.0)
    m['log_a'] = np.log(m['close_a'].replace(0, np.nan))
    m['log_b'] = np.log(m['close_b'].replace(0, np.nan))

    if use_coint:
        # Rolling OLS residuals
        import numpy as _np
        try:
            from statsmodels.regression.linear_model import OLS as _OLS
            from statsmodels.tools import add_constant as _add_constant
        except ImportError:
            use_coint = False

    if use_coint:
        resid = []
        betas = []
        for i in range(len(m)):
            if i < resid_window:
                resid.append(_np.nan); betas.append(_np.nan); continue
            y = m['log_a'].iloc[i-resid_window:i].values
            x = _add_constant(m['log_b'].iloc[i-resid_window:i].values)
            try:
                model = _OLS(y, x).fit()
                beta = model.params[1]; alpha = model.params[0]
                r = m['log_a'].iloc[i] - beta * m['log_b'].iloc[i] - alpha
                resid.append(r); betas.append(beta)
            except Exception:
                resid.append(_np.nan); betas.append(_np.nan)
        m['resid'] = resid
        m['beta'] = betas
        m['spread'] = m['resid']
    else:
        m['spread'] = m['log_a'] - m['log_b']

    m['mean'] = m['spread'].rolling(window).mean()
    m['std'] = m['spread'].rolling(window).std()
    m['z'] = (m['spread'] - m['mean']) / m['std']

    return {
        'current_zscore': float(m['z'].iloc[-1]) if len(m) > 0 and not pd.isna(m['z'].iloc[-1]) else 0.0,
        'price_a': float(m['close_a'].iloc[-1]),
        'price_b': float(m['close_b'].iloc[-1]),
        'spread_trend': float(m['z'].iloc[-1] - m['z'].iloc[-2]) if len(m) > 1 and not pd.isna(m['z'].iloc[-1]) and not pd.isna(m['z'].iloc[-2]) else 0.0,
        'std': float(m['std'].iloc[-1]) if len(m) > 0 and not pd.isna(m['std'].iloc[-1]) else 0.0,
        'mean': float(m['mean'].iloc[-1]) if len(m) > 0 and not pd.isna(m['mean'].iloc[-1]) else 0.0,
    }


'''

text = text[:m.start()] + new_func + text[m.end():]
p.write_text(text)
print('OK: calculate_zscore обновлена')
PYEOF

echo ""
echo "=== Синтаксис ==="
/root/finlab/venv/bin/python -m py_compile "$FILE" && echo "OK"
