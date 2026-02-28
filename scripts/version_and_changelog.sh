#!/usr/bin/env sh
# 版本管理与更新日志：自动生成版本号、写入 CHANGELOG、打 tag
# 用法:
#   ./scripts/version_and_changelog.sh next-patch   # 生成下一 patch 版本并打 tag
#   ./scripts/version_and_changelog.sh next-minor  # 下一 minor
#   ./scripts/version_and_changelog.sh show        # 仅显示当前/下一版本，不写入
# 依赖: git，可选 jq

set -e
ROOT="${0%/*}/.."
cd "$ROOT"
CHANGELOG="${ROOT}/CHANGELOG.md"
VERSION_FILE="${ROOT}/deploy/VERSION"

# 从 tag 取最新版本，格式 v1.2.3
get_latest_tag() {
  git describe --tags --abbrev=0 2>/dev/null | sed 's/^v//' || echo "0.0.0"
}

# 解析版本号
parse_ver() {
  echo "$1" | awk -F. '{print $1, $2, $3}'
}

next_patch() {
  read -r major minor patch <<EOF
$(parse_ver "$1")
EOF
  echo "${major}.${minor}.$((patch + 1))"
}

next_minor() {
  read -r major minor patch <<EOF
$(parse_ver "$1")
EOF
  echo "${major}.$((minor + 1)).0"
}

next_major() {
  read -r major minor patch <<EOF
$(parse_ver "$1")
EOF
  echo "$((major + 1)).0.0"
}

show() {
  LATEST=$(get_latest_tag)
  echo "当前版本: ${LATEST}"
  echo "下一 patch: $(next_patch "$LATEST")"
  echo "下一 minor: $(next_minor "$LATEST")"
  echo "下一 major: $(next_major "$LATEST")"
}

write_version_file() {
  VER="$1"
  SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
  FULL_SHA=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
  mkdir -p "$(dirname "$VERSION_FILE")"
  echo "$VER" > "$VERSION_FILE"
  echo "$SHA" >> "$VERSION_FILE"
  echo "$FULL_SHA" >> "$VERSION_FILE"
  echo "Written $VERSION_FILE: $VER $SHA"
}

append_changelog() {
  VER="$1"
  DATE=$(date +%Y-%m-%d)
  if [ ! -f "$CHANGELOG" ]; then
    echo "# Changelog" > "$CHANGELOG"
    echo "" >> "$CHANGELOG"
  fi
  if ! grep -q "## \[$VER\]" "$CHANGELOG" 2>/dev/null; then
    sed -i.bak "/^# Changelog/a\\
\\
## [$VER] - $DATE\\
- 自动生成版本 $VER\\
" "$CHANGELOG" 2>/dev/null || {
      echo "" >> "$CHANGELOG"
      echo "## [$VER] - $DATE" >> "$CHANGELOG"
      echo "- 自动生成版本 $VER" >> "$CHANGELOG"
    }
    echo "Updated CHANGELOG.md for $VER"
  fi
}

CMD="${1:-show}"
LATEST=$(get_latest_tag)
case "$CMD" in
  show)
    show
    ;;
  next-patch)
    NEW=$(next_patch "$LATEST")
    write_version_file "$NEW"
    append_changelog "$NEW"
    echo "Next version: $NEW (use: git tag v$NEW && git push origin v$NEW)"
    ;;
  next-minor)
    NEW=$(next_minor "$LATEST")
    write_version_file "$NEW"
    append_changelog "$NEW"
    echo "Next version: $NEW (use: git tag v$NEW && git push origin v$NEW)"
    ;;
  next-major)
    NEW=$(next_major "$LATEST")
    write_version_file "$NEW"
    append_changelog "$NEW"
    echo "Next version: $NEW (use: git tag v$NEW && git push origin v$NEW)"
    ;;
  *)
    echo "用法: $0 show | next-patch | next-minor | next-major"
    exit 1
    ;;
esac
