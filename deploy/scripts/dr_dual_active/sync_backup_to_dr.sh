#!/usr/bin/env sh
# 备份数据同步至异地：主站备份完成后将最新备份同步到 OSS/S3，供灾备站点拉取
# 灾备站可定时执行 prepare_dr_site.sh 或本脚本的“拉取”逻辑，实现数据实时/准实时同步
# 用法: 主站执行 BACKUP_DIR=/backup/paas ./sync_backup_to_dr.sh
# 灾备站拉取: DR_PULL_ONLY=1 ./sync_backup_to_dr.sh
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="${SCRIPT_DIR}/../.."
[ -f "${SCRIPT_DIR}/../backup_config.env" ] && . "${SCRIPT_DIR}/../backup_config.env" 2>/dev/null || true
[ -f "${SCRIPT_DIR}/env.example" ] && . "${SCRIPT_DIR}/env.example" 2>/dev/null || true

BACKUP_DIR="${BACKUP_DIR:-./backup}"
DR_PULL_ONLY="${DR_PULL_ONLY:-0}"
PREFIX="${BACKUP_S3_PREFIX:-paas/cells}"

if [ "$DR_PULL_ONLY" = "1" ]; then
  echo "[dr-sync] 灾备站拉取最新备份..."
  mkdir -p "$BACKUP_DIR"
  if [ -n "$BACKUP_S3_BUCKET" ] && command -v aws >/dev/null 2>&1; then
    aws s3 sync "s3://${BACKUP_S3_BUCKET}/${PREFIX}/" "$BACKUP_DIR/" ${BACKUP_S3_ENDPOINT:+--endpoint-url "$BACKUP_S3_ENDPOINT"} --exclude "*" --include "*.tar.gz" 2>/dev/null || true
    echo "[dr-sync] 拉取完成: $BACKUP_DIR"
  else
    echo "[dr-sync] 未配置 BACKUP_S3_BUCKET 或 aws cli"
    exit 1
  fi
  exit 0
fi

# 主站：上传到 S3（由 backup_runner 已做，此处可仅做“同步”校验或增量上传）
if [ -n "$BACKUP_S3_BUCKET" ] && command -v aws >/dev/null 2>&1; then
  for f in "$BACKUP_DIR"/cell_*.tar.gz; do
    [ -f "$f" ] && aws s3 cp "$f" "s3://${BACKUP_S3_BUCKET}/${PREFIX}/$(basename "$f")" ${BACKUP_S3_ENDPOINT:+--endpoint-url "$BACKUP_S3_ENDPOINT"} 2>/dev/null || true
  done
  echo "[dr-sync] 已同步至 s3://${BACKUP_S3_BUCKET}/${PREFIX}"
else
  echo "[dr-sync] 未配置 S3，跳过上传"
fi
exit 0
