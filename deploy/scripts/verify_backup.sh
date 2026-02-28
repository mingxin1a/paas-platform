#!/usr/bin/env sh
# 备份校验：完整性（解压成功、meta.json 存在）、可用性（meta 含 backed_at）；可选校验和
# 备份完成后由 backup_runner 自动调用；失败时 exit 1 触发告警
# 用法: BACKUP_DIR=/backup/paas ./verify_backup.sh [date_prefix]
# 示例: ./verify_backup.sh 20250101_0200

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
[ -f "${SCRIPT_DIR}/backup_config.env" ] && . "${SCRIPT_DIR}/backup_config.env" 2>/dev/null || true
BACKUP_DIR="${BACKUP_DIR:-./backup}"
DATE_PREFIX="${1:-}"
CELLS="${BACKUP_CELLS:-crm erp oa srm wms mes tms plm ems his lis lims hrm}"
OK=0
FAIL=0

for cell in $CELLS; do
  [ -d "${SCRIPT_DIR}/../../cells/${cell}" ] || continue
  if [ -n "$DATE_PREFIX" ]; then
    arc="$BACKUP_DIR/cell_${cell}_${DATE_PREFIX}.tar.gz"
  else
    arc=$(ls -t "$BACKUP_DIR"/cell_${cell}_*.tar.gz 2>/dev/null | head -1)
  fi
  if [ -z "$arc" ] || [ ! -f "$arc" ]; then
    echo "[verify_backup] FAIL: no archive for $cell"
    FAIL=$((FAIL+1))
    continue
  fi
  # 完整性：可解压
  tmpdir=$(mktemp -d)
  if ! tar -xzf "$arc" -C "$tmpdir" 2>/dev/null; then
    echo "[verify_backup] FAIL: corrupt or unreadable $arc"
    FAIL=$((FAIL+1))
    rm -rf "$tmpdir"
    continue
  fi
  dir=$(ls -d "$tmpdir"/cell_* 2>/dev/null | head -1)
  if [ -z "$dir" ] || [ ! -f "$dir/meta.json" ]; then
    echo "[verify_backup] FAIL: $cell missing meta.json"
    FAIL=$((FAIL+1))
    rm -rf "$tmpdir"
    continue
  fi
  # 可用性：meta 含 backed_at
  if ! grep -q "backed_at" "$dir/meta.json" 2>/dev/null; then
    echo "[verify_backup] FAIL: $cell meta.json invalid (no backed_at)"
    FAIL=$((FAIL+1))
    rm -rf "$tmpdir"
    continue
  fi
  echo "[verify_backup] OK: $cell"
  OK=$((OK+1))
  rm -rf "$tmpdir"
done
echo "[verify_backup] Result: OK=$OK FAIL=$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
