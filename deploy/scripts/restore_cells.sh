#!/usr/bin/env sh
# 按细胞独立恢复（从 S3 拉取并解压）。推荐使用 restore_full.sh 实现恢复前自动备份与单细胞恢复。
# 用法: RESTORE_DATE=20250101_0200 BACKUP_DIR=/backup/paas ./restore_cells.sh
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
[ -f "${SCRIPT_DIR}/backup_config.env" ] && . "${SCRIPT_DIR}/backup_config.env" 2>/dev/null || true
BACKUP_DIR="${BACKUP_DIR:-./backup}"
RESTORE_DATE="${RESTORE_DATE:?set RESTORE_DATE}"
CELLS="${BACKUP_CELLS:-crm erp oa srm wms mes tms plm ems his lis lims hrm}"
PREFIX="${BACKUP_S3_PREFIX:-paas/cells}"
if [ -n "$BACKUP_S3_BUCKET" ] && command -v aws >/dev/null 2>&1; then
  mkdir -p "$BACKUP_DIR"
  for cell in $CELLS; do
    aws s3 cp "s3://${BACKUP_S3_BUCKET}/${PREFIX}/cell_${cell}_${RESTORE_DATE}.tar.gz" "$BACKUP_DIR/" ${BACKUP_S3_ENDPOINT:+--endpoint-url "$BACKUP_S3_ENDPOINT"} 2>/dev/null || true
  done
fi
for cell in $CELLS; do
  arc="$BACKUP_DIR/cell_${cell}_${RESTORE_DATE}.tar.gz"
  [ ! -f "$arc" ] && continue
  tar -xzf "$arc" -C "$BACKUP_DIR"
  rm -rf "$BACKUP_DIR/cell_${cell}_${RESTORE_DATE}" 2>/dev/null || true
done
echo "[restore] Done"
