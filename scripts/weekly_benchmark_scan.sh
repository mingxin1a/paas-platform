#!/usr/bin/env bash
# 待补充项清单 8: 每周业界对标扫描
# 用法: bash scripts/weekly_benchmark_scan.sh
# Cron: 0 9 * * 1 cd /path/to/pass-platform && bash scripts/weekly_benchmark_scan.sh

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
CELLS_DIR="${1:-cells}"

echo "[weekly_benchmark] $(date -Iseconds) start"

if [ -f "run_evolution_cycle.sh" ]; then
  bash run_evolution_cycle.sh || true
fi

LOG="$ROOT/glass_house/weekly_benchmark.log"
mkdir -p "$(dirname "$LOG")"
for d in "$CELLS_DIR"/*/; do
  [ -d "$d" ] || continue
  name=$(basename "$d")
  echo "$(date -Iseconds) cell=$name" >> "$LOG"
done

echo "[weekly_benchmark] done; see glass_house/gap_analysis and $LOG"
