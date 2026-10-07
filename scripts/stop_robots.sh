#!/bin/bash
echo "=== STOP ==="
sudo systemctl stop finlab-futures-algopack finlab-futures-algopack-v2 finlab-stocks-tradestats
echo "=== DISABLE ==="
sudo systemctl disable finlab-futures-algopack finlab-futures-algopack-v2 finlab-stocks-tradestats
echo "=== STATUS ==="
for s in finlab-futures-algopack finlab-futures-algopack-v2 finlab-stocks-tradestats; do
  printf "%-40s active=%-10s enabled=%s\n" "$s" "$(systemctl is-active $s)" "$(systemctl is-enabled $s 2>/dev/null)"
done
echo "=== DONE ==="
