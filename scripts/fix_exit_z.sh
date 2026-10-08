#!/bin/bash
cd /root/finlab
cp FinLabPy/My_Indicators/pairs_config.json FinLabPy/My_Indicators/pairs_config.json.bak_exit_z_$(date +%Y%m%d_%H%M%S)

/root/finlab/venv/bin/python << 'PYEOF'
import json
from pathlib import Path

p = Path('/root/finlab/FinLabPy/My_Indicators/pairs_config.json')
cfg = json.load(p.open())

pairs = cfg.get('pairs', cfg)
changed = 0
for name, pair in pairs.items():
    if not isinstance(pair, dict):
        continue
    if not pair.get('enabled'):
        continue
    bp = pair.get('best_params', {})
    if bp.get('exit_z', None) == 0.0:
        bp['exit_z'] = 0.5
        changed += 1
        print(f'  {name}: exit_z 0.0 → 0.5')

p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))
print(f'\nИзменено пар: {changed}')
PYEOF
