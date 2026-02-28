#!/usr/bin/env sh
# 细胞交付校验脚本：符合 delivery.package.schema 与《接口设计说明书》
# 用法：在细胞根目录执行 ./verify_delivery.sh 或 sh verify_delivery.sh
set -e
CELL_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$CELL_ROOT"

echo "[verify] 检查 delivery.package ..."
test -f delivery.package || { echo "缺少 delivery.package"; exit 1; }

echo "[verify] 检查 completion.manifest ..."
test -f completion.manifest || { echo "缺少 completion.manifest"; exit 1; }

echo "[verify] 检查 cell_profile.md ..."
test -f cell_profile.md || { echo "缺少 cell_profile.md"; exit 1; }

echo "[verify] 运行单元测试 ..."
export CELL_DATABASE_URL="${CELL_DATABASE_URL:-sqlite:///./tmp_verify.db}"
python -m pytest tests/ -v --tb=short -q || { echo "单元测试未通过"; exit 1; }

echo "[verify] 健康接口 ..."
python -c "
from main import app
from fastapi.testclient import TestClient
c = TestClient(app)
r = c.get('/health')
assert r.status_code == 200, r.text
assert r.json().get('status') == 'up', r.json()
print('  /health OK')
"

echo "[verify] 交付校验通过。"
