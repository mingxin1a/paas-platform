#!/usr/bin/env bash
# CRM 细胞健康检查脚本（商用可运维）
# 用于 PaaS 层巡检或运维人工执行；与 /health、/metrics 配合使用
set -e
BASE_URL="${CRM_BASE_URL:-http://localhost:8001}"
echo "[CRM] 健康检查: $BASE_URL"
# 1. 存活
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health" || echo "000")
if [ "$STATUS" != "200" ]; then
  echo "[CRM] FAIL: /health 返回 $STATUS"
  exit 1
fi
echo "[CRM] /health OK"
# 2. 指标（若需鉴权可加 -H "Authorization: Bearer ..."）
METRICS=$(curl -s "$BASE_URL/metrics" || echo "{}")
if echo "$METRICS" | grep -q '"cell":"crm"'; then
  echo "[CRM] /metrics OK"
else
  echo "[CRM] WARN: /metrics 未返回预期格式"
fi
echo "[CRM] 健康检查通过"
