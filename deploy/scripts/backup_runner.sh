#!/usr/bin/env sh
# 企业级备份入口：全量/增量、多目标（本地/S3/NAS）、定时调用、完成后校验、失败告警
# 用法:
#   BACKUP_TYPE=full ./backup_runner.sh
#   BACKUP_TYPE=incremental ./backup_runner.sh
#   crontab: 0 2 * * * BACKUP_TYPE=full /path/to/backup_runner.sh
# 依赖: backup_cells.sh, backup_full.sh(可选), verify_backup.sh, alert_on_backup_failure.sh
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="${SCRIPT_DIR}/../.."
cd "$ROOT"
[ -f "${SCRIPT_DIR}/backup_config.env" ] && . "${SCRIPT_DIR}/backup_config.env" 2>/dev/null || true

BACKUP_TYPE="${BACKUP_TYPE:-full}"
BACKUP_DIR="${BACKUP_DIR:-./backup}"
BACKUP_TARGETS="${BACKUP_TARGETS:-local}"
DATE=$(date +%Y%m%d_%H%M)
LOG_DIR="${BACKUP_DIR}/logs"
mkdir -p "$BACKUP_DIR" "$LOG_DIR"
LOG_FILE="${LOG_DIR}/backup_${BACKUP_TYPE}_${DATE}.log"
exec 1> "$LOG_FILE" 2>&1

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
alert_fail() {
  log "ALERT: Backup failed - $*"
  [ -x "${SCRIPT_DIR}/alert_on_backup_failure.sh" ] && BACKUP_LOG_FILE="$LOG_FILE" "${SCRIPT_DIR}/alert_on_backup_failure.sh" "$@" || true
  exit 1
}

log "=== Backup start: type=$BACKUP_TYPE targets=$BACKUP_TARGETS ==="

# 1. 执行细胞备份（全量或增量均先打包当前细胞数据）
export BACKUP_DIR
export BACKUP_DATE="$DATE"
export BACKUP_TYPE
if [ "$BACKUP_TYPE" = "incremental" ] && [ -f "${BACKUP_DIR}/.last_full_date" ]; then
  LAST_FULL=$(cat "${BACKUP_DIR}/.last_full_date")
  log "Incremental since full $LAST_FULL"
fi
if ! "${SCRIPT_DIR}/backup_cells.sh"; then
  alert_fail "backup_cells.sh failed"
fi

# 2. 全量时写入标记，便于增量与恢复时识别
if [ "$BACKUP_TYPE" = "full" ]; then
  echo "$DATE" > "${BACKUP_DIR}/.last_full_date"
  log "Full backup marker written: $DATE"
fi

# 3. 上传到 S3/OSS（若配置）
if echo "$BACKUP_TARGETS" | grep -q "s3"; then
  if [ -n "$BACKUP_S3_BUCKET" ] && command -v aws >/dev/null 2>&1; then
    PREFIX="${BACKUP_S3_PREFIX:-paas/cells}"
    for f in "$BACKUP_DIR"/cell_*_${DATE}.tar.gz; do
      [ -f "$f" ] && aws s3 cp "$f" "s3://${BACKUP_S3_BUCKET}/${PREFIX}/$(basename "$f")" ${BACKUP_S3_ENDPOINT:+--endpoint-url "$BACKUP_S3_ENDPOINT"} || true
    done
    log "Uploaded to S3: ${BACKUP_S3_BUCKET}/${PREFIX}"
  else
    log "WARN: S3 target configured but BACKUP_S3_BUCKET or aws cli missing"
  fi
fi

# 4. 同步到 NAS（若配置）
if echo "$BACKUP_TARGETS" | grep -q "nas"; then
  if [ -n "$BACKUP_NAS_PATH" ] && [ -d "$BACKUP_NAS_PATH" ]; then
    cp -p "$BACKUP_DIR"/cell_*_${DATE}.tar.gz "$BACKUP_NAS_PATH/" 2>/dev/null || log "WARN: NAS copy failed"
    log "Copied to NAS: $BACKUP_NAS_PATH"
  elif [ -n "$BACKUP_NAS_RSYNC" ]; then
    rsync -av "$BACKUP_DIR"/cell_*_${DATE}.tar.gz "$BACKUP_NAS_RSYNC/" 2>/dev/null || log "WARN: NAS rsync failed"
    log "Rsynced to NAS: $BACKUP_NAS_RSYNC"
  else
    log "WARN: NAS target configured but BACKUP_NAS_PATH/BACKUP_NAS_RSYNC missing"
  fi
fi

# 5. 备份完成后校验
if ! "${SCRIPT_DIR}/verify_backup.sh" "$DATE"; then
  alert_fail "verify_backup.sh failed for date $DATE"
fi

# 6. 清理过期备份（本地）
retention_full="${BACKUP_RETENTION_FULL_DAYS:-7}"
retention_incr="${BACKUP_RETENTION_INCR_DAYS:-3}"
find "$BACKUP_DIR" -maxdepth 1 -name "cell_*.tar.gz" -mtime +${retention_full} -delete 2>/dev/null || true
find "$LOG_DIR" -maxdepth 1 -name "backup_*.log" -mtime +${retention_full} -delete 2>/dev/null || true
log "=== Backup finished successfully: $BACKUP_DIR date=$DATE ==="
exit 0
