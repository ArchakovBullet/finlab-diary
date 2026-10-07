#!/bin/bash
FILE=robots/pairs_robot.py
cp "$FILE" "$FILE.bak_pairs_pause_$(date +%Y%m%d_%H%M%S)"
echo "Бэкап создан"
echo "Диагностика process_command:"
sed -n '606,616p' "$FILE"
