#!/usr/bin/env bash
# 异地容灾站点准备：拉取镜像、准备目录、从对象存储拉取最新备份
# 用法: 在灾备节点执行；需配置 env.example 或 backup_config.env 中的 S3/OSS 变量
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${SCRIPT_DIR}/../.."
source "${SCRIPT_DIR}/env.example" 2>/dev/null || true
[ -f "${SCRIPT_DIR}/../backup_config.env" ] && . "${SCRIPT_DIR}/../backup_config.env" 2>/dev/null || true

BACKUP_DIR="${BACKUP_DIR:-/data/paas/backup}"
PREFIX="${BACKUP_S3_PREFIX:-paas/cells}"

echo "[dr] Preparing DR site..."
mkdir -p "$BACKUP_DIR"

# 1. 拉取镜像（按实际仓库取消注释并修改）
# docker pull your-registry/superpaas/gateway:latest
# docker pull your-registry/superpaas/governance:latest

# 2. 从 S3/OSS 拉取最新备份
if [ -n "${BACKUP_S3_BUCKET}" ] && command -v aws >/dev/null 2>&1; then
  aws s3 sync "s3://${BACKUP_S3_BUCKET}/${PREFIX}/" "$BACKUP_DIR/" ${BACKUP_S3_ENDPOINT:+--endpoint-url "$BACKUP_S3_ENDPOINT"} --exclude "*" --include "*.tar.gz" 2>/dev/null || true
  echo "[dr] Backup synced to $BACKUP_DIR"
else
  echo "[dr] Skip S3 sync (BACKUP_S3_BUCKET or aws cli not set)"
fi

echo "[dr] Done. Next: run restore_full.sh with RESTORE_DATE=<latest>, then start services and dr_failover.sh when switching."
exit 0
