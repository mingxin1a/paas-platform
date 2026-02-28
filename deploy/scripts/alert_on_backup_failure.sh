#!/usr/bin/env sh
# 备份失败告警：接收备份阶段错误信息，发送 Webhook 或记录告警日志
# 由 backup_runner.sh 在备份/校验失败时调用；需配置 BACKUP_ALERT_WEBHOOK 或 BACKUP_ALERT_EMAIL
# 用法: 由 backup_runner 调用，或手动: BACKUP_LOG_FILE=/path/to/log ./alert_on_backup_failure.sh "reason"
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
[ -f "${SCRIPT_DIR}/backup_config.env" ] && . "${SCRIPT_DIR}/backup_config.env" 2>/dev/null || true
REASON="${1:-Backup or verify failed}"
LOG_FILE="${BACKUP_LOG_FILE:-}"
HOSTNAME=$(hostname 2>/dev/null || echo "unknown")
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
BODY="SuperPaaS 备份告警\n时间: ${TIMESTAMP}\n主机: ${HOSTNAME}\n原因: ${REASON}\n日志: ${LOG_FILE}"

# Webhook（企业微信/钉钉/Slack 等）
if [ -n "$BACKUP_ALERT_WEBHOOK" ]; then
  if command -v curl >/dev/null 2>&1; then
    # 通用 JSON 体（可按实际 webhook 格式调整）
    JSON="{\"msgtype\":\"text\",\"text\":{\"content\":\"${REASON}\n${TIMESTAMP}\n${HOSTNAME}\n${LOG_FILE}\"}}"
    curl -s -X POST "$BACKUP_ALERT_WEBHOOK" -H "Content-Type: application/json" -d "$JSON" 2>/dev/null || true
  fi
fi

# 本地告警日志（便于集中采集）
ALERT_LOG="${SCRIPT_DIR}/../backup/backup_alerts.log"
mkdir -p "$(dirname "$ALERT_LOG")"
echo "$TIMESTAMP [BACKUP_FAIL] $REASON host=$HOSTNAME log=$LOG_FILE" >> "$ALERT_LOG"
exit 0
