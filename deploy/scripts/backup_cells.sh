#!/usr/bin/env sh
# 按细胞独立备份（全量）；支持多目标由 backup_runner 统一上传 S3/NAS
# 用法: BACKUP_DIR=/backup/paas ./backup_cells.sh
# 可选: BACKUP_DATE=20250101_0200 指定时间戳；BACKUP_CELLS="crm erp wms" 指定细胞列表
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
[ -f "${SCRIPT_DIR}/backup_config.env" ] && . "${SCRIPT_DIR}/backup_config.env" 2>/dev/null || true
BACKUP_DIR="${BACKUP_DIR:-./backup}"
BACKUP_DATE="${BACKUP_DATE:-$(date +%Y%m%d_%H%M)}"
DATE="$BACKUP_DATE"
CELLS="${BACKUP_CELLS:-crm erp oa srm wms mes tms plm ems his lis lims hrm}"
mkdir -p "$BACKUP_DIR"
for cell in $CELLS; do
  [ -d "${SCRIPT_DIR}/../../cells/${cell}" ] || continue
  cell_dir="$BACKUP_DIR/cell_${cell}_${DATE}"
  mkdir -p "$cell_dir"
  echo "{\"cell\":\"$cell\",\"backed_at\":\"$DATE\",\"type\":\"full\"}" > "$cell_dir/meta.json"
  tar -czf "$BACKUP_DIR/cell_${cell}_${DATE}.tar.gz" -C "$BACKUP_DIR" "cell_${cell}_${DATE}"
  rm -rf "$cell_dir"
done
# S3 上传由 backup_runner 统一处理，此处不再重复上传
echo "[backup] Finished: $BACKUP_DIR date=$DATE cells=$CELLS"
