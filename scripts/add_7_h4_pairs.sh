#!/bin/bash
cd /root/finlab
cp FinLabPy/My_Indicators/pairs_config.json FinLabPy/My_Indicators/pairs_config.json.bak_7h4_$(date +%Y%m%d_%H%M%S)

/root/finlab/venv/bin/python << 'PYEOF'
import json
from pathlib import Path

p = Path('/root/finlab/FinLabPy/My_Indicators/pairs_config.json')
cfg = json.load(p.open())
if 'pairs' not in cfg:
    cfg['pairs'] = {}

# 7 OK H4-пар
OK_H4_PAIRS = {
    'GD-SV_H4':      {'entry_z': 2.0, 'exit_z': 0.5, 'window': 20, 'resid_window': 30, 'use_coint': True},
    'PT-SV_H4':      {'entry_z': 2.0, 'exit_z': 0.5, 'window': 20, 'resid_window': 30, 'use_coint': True},
    'GD-PT_H4':      {'entry_z': 2.0, 'exit_z': 0.5, 'window': 20, 'resid_window': 30, 'use_coint': True},
    'BR-GAZPF_H4':   {'entry_z': 2.0, 'exit_z': 0.5, 'window': 20, 'resid_window': 30, 'use_coint': True},
    'GLDRUBF-GD_H4': {'entry_z': 2.0, 'exit_z': 0.5, 'window': 20, 'resid_window': 30, 'use_coint': True},
    'GAZPF-SBERF_H4':{'entry_z': 2.0, 'exit_z': 0.5, 'window': 20, 'resid_window': 30, 'use_coint': True},
    'LK-IMOEXF_H4':  {'entry_z': 2.0, 'exit_z': 0.5, 'window': 20, 'resid_window': 30, 'use_coint': True},
}

added = 0
for name, params in OK_H4_PAIRS.items():
    if name not in cfg['pairs']:
        cfg['pairs'][name] = {'enabled': True, 'best_params': params}
        added += 1
        print(f'  Добавлена: {name}')

p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))
print(f'\nДобавлено: {added}')
PYEOF

echo ""
echo "=== Проверка ==="
/root/finlab/venv/bin/python << 'PYEOF'
import json
cfg = json.load(open('/root/finlab/FinLabPy/My_Indicators/pairs_config.json'))
pairs = cfg.get('pairs', cfg)
active = [(n, p) for n, p in pairs.items() if isinstance(p, dict) and p.get('enabled')]
print(f'Активных пар: {len(active)}')
by_tf = {}
for n, p in active:
    tf = n.rsplit('_', 1)[1]
    by_tf.setdefault(tf, []).append(n)
for tf, names in sorted(by_tf.items()):
    print(f'  {tf}: {len(names)}')
    for n in sorted(names):
        print(f'    {n}')
PYEOF
