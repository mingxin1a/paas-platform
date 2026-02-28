#!/usr/bin/env sh
# 执行一次自主进化周期（可被 cron 每 24 小时调用）
# 例: 0 0 * * * cd /path/to/paas-platform && ./scripts/run_evolution_cycle.sh
# 或从项目根: ./run_evolution_cycle.sh（兼容）
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"
exec python evolution_engine/evolution_engine.py
