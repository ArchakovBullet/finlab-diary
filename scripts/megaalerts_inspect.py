"""
Диагностика MegaAlerts:
- читает все файлы data/mega_alerts/*.parquet
- чистит дубли (по secid + tradetime + alert_type)
- парсит reference (JSON) — извлекает горизонты (m_5, m_15, ...)
- агрегирует по alert_type: n, mean fwd return, WR по каждому горизонту
"""
import pandas as pd, glob, json, os
from collections import defaultdict

files = sorted(glob.glob('data/mega_alerts/*.parquet'))
print(f"файлов: {len(files)}")

frames = []
for f in files:
    df = pd.read_parquet(f)
    df['ticker'] = os.path.basename(f).replace('_alerts.parquet', '')
    frames.append(df)

all_df = pd.concat(frames, ignore_index=True)
print(f"всего строк (с дублями): {len(all_df)}")

# Чистим дубли
key_cols = ['ticker', 'tradedate', 'tradetime', 'alert_type', 'threshold', 'value']
before = len(all_df)
all_df = all_df.drop_duplicates(subset=key_cols)
print(f"после чистки дублей: {len(all_df)} (убрано {before - len(all_df)})")

# Уникальные alert_type
print("\n=== уникальные alert_type (топ-20 по частоте) ===")
vc = all_df['alert_type'].value_counts()
print(vc.head(20))

# Парсим reference — берём первый элемент
print("\n=== пример reference (первая строка) ===")
sample_ref = all_df['reference'].iloc[0]
print(sample_ref[:300])

# Попробуем распарсить
def parse_ref(ref_str):
    try:
        obj = json.loads(ref_str)
        if isinstance(obj, list) and len(obj) > 0:
            return obj[0]
        return obj
    except Exception as e:
        return None

all_df['ref_parsed'] = all_df['reference'].apply(parse_ref)

# Соберём все ключи горизонта
horizons = set()
for r in all_df['ref_parsed'].dropna().head(1000):
    if isinstance(r, dict):
        horizons.update(r.keys())
print("\n=== горизонты в reference ===")
print(sorted(horizons))

# Агрегация по alert_type: считаем n и средний forward return по m_5
def mean_m5(r):
    if not isinstance(r, dict) or 'm_5' not in r:
        return None
    try:
        return float(r['m_5'][0])
    except Exception:
        return None

all_df['m5_mean'] = all_df['ref_parsed'].apply(mean_m5)

print("\n=== агрегация по alert_type (n >= 50) ===")
agg = (all_df.dropna(subset=['m5_mean'])
       .groupby('alert_type')
       .agg(n=('m5_mean', 'size'),
            mean_m5=('m5_mean', 'mean'),
            wr_m5=('m5_mean', lambda x: (x > 0).mean()))
       .query('n >= 50')
       .sort_values('mean_m5', ascending=False))
print(agg.to_string())
