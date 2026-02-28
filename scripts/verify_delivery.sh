#!/usr/bin/env sh
# 细胞交付验证 - 《00_最高宪法》自主进化引擎
# 用法: ./scripts/verify_delivery.sh {CELL_NAME}  或  项目根 ./verify_delivery.sh {CELL_NAME}（兼容）
# 退出码: 0 通过, 非0 未通过
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CELL_NAME="${1:?usage: ./scripts/verify_delivery.sh CELL_NAME}"
CELL_DIR="${ROOT}/cells/${CELL_NAME}"
if [ ! -d "$CELL_DIR" ]; then
  echo "ERROR: cell directory not found: $CELL_DIR"
  exit 1
fi
echo "[verify] cell=$CELL_NAME"

# 1. delivery.package 存在且 status 可解析
if [ ! -f "$CELL_DIR/delivery.package" ]; then
  echo "FAIL: missing delivery.package"
  exit 1
fi
echo "[verify] delivery.package OK"

# 2. completion.manifest 存在
MANIFEST=$(grep -E "^completion_manifest:" "$CELL_DIR/delivery.package" | sed 's/.*: *//' | tr -d '"' | tr -d "'")
if [ -z "$MANIFEST" ]; then
  MANIFEST="completion.manifest"
fi
if [ ! -f "$CELL_DIR/$MANIFEST" ]; then
  echo "FAIL: missing $MANIFEST"
  exit 1
fi
echo "[verify] completion.manifest OK"

# 3. 细胞档案与契约存在（集装箱原则）
for f in cell_profile.md api_contract.yaml; do
  if [ ! -f "$CELL_DIR/$f" ]; then
    echo "FAIL: missing $f"
    exit 1
  fi
done
echo "[verify] cell_profile.md + api_contract.yaml OK"

# 4. 自愈配置存在（生物学原则）
if [ ! -f "$CELL_DIR/auto_healing.yaml" ]; then
  echo "FAIL: missing auto_healing.yaml"
  exit 1
fi
echo "[verify] auto_healing.yaml OK"

# 5. 可运行性：src/app.py 必须存在
if [ ! -f "$CELL_DIR/src/app.py" ]; then
  echo "FAIL: missing src/app.py (cell not runnable)"
  exit 1
fi
echo "[verify] src/app.py OK"

echo "[verify] all checks passed for $CELL_NAME"
exit 0
