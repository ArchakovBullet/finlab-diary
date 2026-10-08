#!/bin/bash
cd /root/finlab
cp FinLabPy/My_Indicators/pairs_config.json FinLabPy/My_Indicators/pairs_config.json.bak_addh4_$(date +%Y%m%d_%H%M%S)

/root/finlab/venv/bin/python << 'PYEOF'
import json
from pathlib import Path

p = Path('/root/finlab/FinLabPy/My_Indicators/pairs_config.json')
cfg = json.load(p.open())

# Проверяем структуру
if 'pairs' not in cfg:
    cfg['pairs'] = {}

NEW_PAIRS = {
    'GAZPF-SBERF_H4': {'entry_z': 2.5, 'exit_z': 0.5, 'window': 30, 'resid_window': 60, 'use_coint': True},
    'GD-SV_H4':       {'entry_z': 2.5, 'exit_z': 0.5, 'window': 30, 'resid_window': 60, 'use_coint': True},
    'PD-SV_H4':       {'entry_z': 2.5, 'exit_z': 0.5, 'window': 30, 'resid_window': 60, 'use_coint': True},
}

added = 0
for name, params in NEW_PAIRS.items():
    if name not in cfg['pairs']:
        cfg['pairs'][name] = {
            'enabled': True,
            'best_params': params,
        }
        added += 1
        print(f'  Добавлена: {name}')

p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))
print(f'Добавлено: {added}')
PYEOF

echo ""
echo "=== Проверка ==="
/root/finlab/venv/bin/python << 'PYEOF'
import json
cfg = json.load(open('/root/finlab/FinLabPy/My_Indicators/pairs_config.json'))
pairs = cfg.get('pairs', cfg)
active = [(n, p) for n, p in pairs.items() if isinstance(p, dict) and p.get('enabled')]
print(f'Активных пар: {len(active)}')
for n, p in sorted(active):
    bp = p.get('best_params', {})
    print(f'  {n}: entry_z={bp.get("entry_z")}, window={bp.get("window")}, use_coint={bp.get("use_coint")}')
PYEOF
