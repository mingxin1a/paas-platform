#!/usr/bin/env sh
# SuperPaaS 一键自检脚本（与 self_check.py 能力一致）
# 执行：PaaS 核心健康、网关路由、双端前端、细胞合规、文档与代码一致性、全细胞交付校验、pytest
# 用法: ./scripts/self_check.sh  或  项目根 ./self_check.sh（兼容）
# 可选环境变量: GATEWAY_URL, GOVERNANCE_URL, MONITOR_CENTER_URL

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

# 优先调用 Python 自检脚本（细胞合规性 + 平台健康度一键校验，含 JSON 报告）
if command -v python3 >/dev/null 2>&1; then
  exec python3 "${ROOT}/scripts/self_check.py" "$@"
fi
if command -v python >/dev/null 2>&1; then
  exec python "${ROOT}/scripts/self_check.py" "$@"
fi

# 无 Python 时回退：仅全细胞交付校验 + 简单提示
echo "[self_check] 未找到 python3/python，仅执行 shell 可做步骤" 1>&2
REPORT_JSON="${ROOT}/glass_house/health_report.json"
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
mkdir -p glass_house

if [ -f "${ROOT}/evolution_engine/verify_all_cells.py" ]; then
  if python3 "${ROOT}/evolution_engine/verify_all_cells.py" 2>/dev/null || python "${ROOT}/evolution_engine/verify_all_cells.py"; then
    echo "[self_check] verify_all_cells 通过"
  else
    echo "[self_check] verify_all_cells 失败" 1>&2
    echo "{\"version\":\"2.0\",\"generatedAt\":\"$TS\",\"summary\":{\"status\":\"degraded\",\"failed\":1}}" > "$REPORT_JSON"
    exit 1
  fi
fi

echo "{\"version\":\"2.0\",\"generatedAt\":\"$TS\",\"summary\":{\"status\":\"healthy\",\"passed\":1,\"failed\":0}}" > "$REPORT_JSON"
echo "[self_check] 建议安装 Python 并运行 scripts/self_check.py 以执行完整自检（PaaS 健康、细胞合规、文档一致性等）"
exit 0
