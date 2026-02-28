#!/bin/bash
# 性能测试执行脚本：基准 / 负载 / 压力 / 稳定性
# 依赖: pip install locust
# 用法: GATEWAY_URL=http://localhost:8000 ./run_performance_tests.sh [baseline|load|stress|stability]

set -e
GATEWAY_URL="${GATEWAY_URL:-http://localhost:8000}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

mode="${1:-baseline}"
case "$mode" in
  baseline)  python run_performance_tests.py baseline ;;
  load)      python run_performance_tests.py load ;;
  stress)    python run_performance_tests.py stress ;;
  stability) python run_performance_tests.py stability ;;
  *)
    echo "Usage: $0 [baseline|load|stress|stability]"
    echo "  baseline:  10 users, 5 min"
    echo "  load:      100 users, 10 min"
    echo "  stress:    500 users, 15 min"
    echo "  stability: 200 users, 72h"
    exit 1
    ;;
esac
