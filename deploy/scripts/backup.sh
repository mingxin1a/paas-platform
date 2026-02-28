#!/usr/bin/env sh
# SuperPaaS 数据备份脚本（示例：需按实际 DB 与路径修改）
# 用途：商用化可运维——数据备份；恢复流程见 deploy/scripts/backup_example.md
# 用法: BACKUP_DIR=/backup/paas ./backup.sh

set -e
BACKUP_DIR="${BACKUP_DIR:-./backup}"
DATE=$(date +%Y%m%d_%H%M)
mkdir -p "$BACKUP_DIR"

# 配置备份（脱敏：仅保留 key，值替换为 ***）
if [ -f "${0%/*}/../.env" ]; then
  sed 's/=.*/=***/' "${0%/*}/../.env" > "$BACKUP_DIR/env_sample_${DATE}.txt" || true
fi

# 各 Cell 若使用 MySQL，需在此处按实际环境取消注释并填写 DB_* 变量
# 示例：全量 dump 单个库
# DB_HOST="${DB_HOST:-localhost}"
# DB_USER="${DB_USER:-root}"
# DB_NAME="${DB_NAME:-crm}"
# mysqldump -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" | gzip > "$BACKUP_DIR/${DB_NAME}_${DATE}.sql.gz"

echo "[backup] Backup finished: $BACKUP_DIR (date=$DATE)"
