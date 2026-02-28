#!/usr/bin/env sh
# 商用验收一键全量校验：自检（含架构合规、全链路健康）+ 批次1 细胞交付校验
# 用法: ./scripts/commercial_acceptance_verify.sh
# 从项目根执行: ./run.sh commercial_accept 或 直接 ./scripts/commercial_acceptance_verify.sh

set -e
ROOT="${0%/*}/.."
cd "$ROOT"
echo "[commercial_acceptance] 开始商用验收全量校验"

# 1. 自检（含 PaaS 健康、网关路由、细胞合规、架构合规、全链路健康、verify_all_cells、pytest）
if [ -x "./scripts/self_check.sh" ]; then
  ./scripts/self_check.sh
else
  python3 scripts/self_check.py || python scripts/self_check.py
fi
echo "[commercial_acceptance] self_check 完成"

# 2. 批次1 细胞交付校验
for cell in crm erp oa srm; do
  if [ -x "./scripts/verify_delivery.sh" ]; then
    ./scripts/verify_delivery.sh "$cell"
  else
    python3 evolution_engine/verify_delivery.py "$cell" || python evolution_engine/verify_delivery.py "$cell"
  fi
  echo "[commercial_acceptance] verify_delivery $cell 通过"
done

# 3. 可选：备份校验（若有近期备份）
# BACKUP_DIR=/backup/paas ./deploy/scripts/verify_backup.sh 2>/dev/null || true

echo "[commercial_acceptance] 全量校验通过"
