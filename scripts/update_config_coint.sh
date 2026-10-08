#!/bin/bash
cd /root/finlab
cp FinLabPy/My_Indicators/pairs_config.json FinLabPy/My_Indicators/pairs_config.json.bak_coint_$(date +%Y%m%d_%H%M%S)

/root/finlab/venv/bin/python << 'PYEOF'
import json
from pathlib import Path

p = Path('/root/finlab/FinLabPy/My_Indicators/pairs_config.json')
cfg = json.load(p.open())
pairs = cfg.get('pairs', cfg)

# OK-пары (cointegration, 4+/5 фолдов)
OK_PAIRS = {
    'SFIN-SH_M10':    {'entry_z': 2.5, 'exit_z': 0.5, 'window': 30, 'resid_window': 60},
    'BANE-BN_M10':    {'entry_z': 2.5, 'exit_z': 0.5, 'window': 30, 'resid_window': 60},
    'BELU-NB_M10':    {'entry_z': 2.5, 'exit_z': 0.5, 'window': 30, 'resid_window': 60},
    'GAZPF-SBERF_H4': {'entry_z': 2.5, 'exit_z': 0.5, 'window': 30, 'resid_window': 60},
    'GD-SV_H4':       {'entry_z': 2.5, 'exit_z': 0.5, 'window': 30, 'resid_window': 60},
    'PD-SV_H4':       {'entry_z': 2.5, 'exit_z': 0.5, 'window': 30, 'resid_window': 60},
}

enabled = 0
for name, pair in pairs.items():
    if not isinstance(pair, dict): continue
    if name in OK_PAIRS:
        pair['enabled'] = True
        pair['best_params'] = {**pair.get('best_params', {}), **OK_PAIRS[name], 'use_coint': True}
        enabled += 1
    else:
        pair['enabled'] = False

p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))
print(f'Активных: {enabled}')
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
