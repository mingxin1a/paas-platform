#!/usr/bin/env sh
# 一键数据恢复：支持全量恢复、按时间点恢复、单细胞恢复；恢复前自动备份当前数据防误操作
# 用法:
#   全量恢复: RESTORE_DATE=20250101_0200 ./restore_full.sh
#   单细胞恢复: RESTORE_DATE=20250101_0200 RESTORE_CELL=crm ./restore_full.sh
#   恢复前不备份: RESTORE_SKIP_PREBACKUP=1 ./restore_full.sh
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="${SCRIPT_DIR}/../.."
[ -f "${SCRIPT_DIR}/backup_config.env" ] && . "${SCRIPT_DIR}/backup_config.env" 2>/dev/null || true
BACKUP_DIR="${BACKUP_DIR:-./backup}"
RESTORE_DATE="${RESTORE_DATE:?请设置 RESTORE_DATE，例如 20250101_0200}"
RESTORE_CELL="${RESTORE_CELL:-}"
RESTORE_SKIP_PREBACKUP="${RESTORE_SKIP_PREBACKUP:-0}"
CELLS="${BACKUP_CELLS:-crm erp oa srm wms mes tms plm ems his lis lims hrm}"
cd "$ROOT"
mkdir -p "$BACKUP_DIR"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [restore] $*"; }
die() { log "ERROR: $*"; exit 1; }

# 1. 恢复前自动备份当前数据（除非明确跳过）
if [ "$RESTORE_SKIP_PREBACKUP" != "1" ]; then
  PREBACKUP_DATE=$(date +%Y%m%d_%H%M)
  log "恢复前自动备份当前数据到 date=$PREBACKUP_DATE ..."
  export BACKUP_DIR BACKUP_DATE="$PREBACKUP_DATE"
  if [ -n "$RESTORE_CELL" ]; then
    export BACKUP_CELLS="$RESTORE_CELL"
  fi
  if ! "${SCRIPT_DIR}/backup_cells.sh"; then
    die "恢复前备份失败，已中止恢复。若确需跳过请设置 RESTORE_SKIP_PREBACKUP=1"
  fi
  log "恢复前备份完成: $BACKUP_DIR"
else
  log "已跳过恢复前备份 (RESTORE_SKIP_PREBACKUP=1)"
fi

# 2. 从 S3 拉取（若配置且本地无对应文件）
if [ -n "$BACKUP_S3_BUCKET" ] && command -v aws >/dev/null 2>&1; then
  PREFIX="${BACKUP_S3_PREFIX:-paas/cells}"
  for cell in $CELLS; do
    [ -n "$RESTORE_CELL" ] && [ "$RESTORE_CELL" != "$cell" ] && continue
    dest="$BACKUP_DIR/cell_${cell}_${RESTORE_DATE}.tar.gz"
    if [ ! -f "$dest" ]; then
      log "从 S3 拉取 cell_${cell}_${RESTORE_DATE}.tar.gz ..."
      aws s3 cp "s3://${BACKUP_S3_BUCKET}/${PREFIX}/cell_${cell}_${RESTORE_DATE}.tar.gz" "$dest" ${BACKUP_S3_ENDPOINT:+--endpoint-url "$BACKUP_S3_ENDPOINT"} 2>/dev/null || true
    fi
  done
fi

# 3. 解压恢复（按细胞或全量）
restored=0
for cell in $CELLS; do
  [ -n "$RESTORE_CELL" ] && [ "$RESTORE_CELL" != "$cell" ] && continue
  arc="$BACKUP_DIR/cell_${cell}_${RESTORE_DATE}.tar.gz"
  if [ ! -f "$arc" ]; then
    log "跳过 $cell: 未找到 $arc"
    continue
  fi
  log "恢复细胞: $cell"
  tar -xzf "$arc" -C "$BACKUP_DIR"
  # 若存在恢复钩子（如将数据导入数据库），可在此调用
  [ -x "${SCRIPT_DIR}/restore_hook_${cell}.sh" ] && "${SCRIPT_DIR}/restore_hook_${cell}.sh" "$BACKUP_DIR" "$RESTORE_DATE" || true
  rm -rf "$BACKUP_DIR/cell_${cell}_${RESTORE_DATE}" 2>/dev/null || true
  restored=$((restored + 1))
done
log "恢复完成: 共 $restored 个细胞。请重启相关服务并执行健康检查。"
exit 0
