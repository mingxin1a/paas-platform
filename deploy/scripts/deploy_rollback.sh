#!/usr/bin/env sh
# 版本回滚：Docker 单机回滚到上一版本镜像；K8s 回滚 Deployment 到上一 Revision
# 用法:
#   Docker: ./deploy/scripts/deploy_rollback.sh docker [SERVICE]
#   K8s:    ./deploy/scripts/deploy_rollback.sh k8s [DEPLOYMENT_NAME]
# 不传 SERVICE/DEPLOYMENT_NAME 时，Docker 回滚所有服务拉取前一次镜像；K8s 回滚 gateway 与 governance

set -e
ROOT="${0%/*}/../.."
cd "$ROOT"
DEPLOY_DIR="${ROOT}/deploy"
COMPOSE_FILE="${DEPLOY_DIR}/docker-compose.yml"
ENV_FILE="${DEPLOY_DIR}/.env"

log() { echo "[rollback] $*"; }
ok() { echo "[rollback]   [OK] $*"; }
fail() { echo "[rollback]   [FAIL] $*"; exit 1; }

rollback_docker() {
  log "=== Docker 回滚 ==="
  COMPOSE="docker compose"
  $COMPOSE version >/dev/null 2>&1 || COMPOSE="docker-compose"
  [ ! -f "$COMPOSE_FILE" ] && fail "未找到 docker-compose.yml"
  [ ! -f "$ENV_FILE" ] && fail "未找到 .env"
  TARGET="${1:-}"
  if [ -n "$TARGET" ]; then
    log "回滚服务: $TARGET（拉取前一次镜像并重启）"
    $COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull "$TARGET" 2>/dev/null || true
    $COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d "$TARGET" || fail "up -d $TARGET"
  else
    log "回滚全部服务：拉取镜像并重启（无版本标签时仅重启）"
    $COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull 2>/dev/null || true
    $COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d || fail "up -d"
  fi
  ok "Docker 回滚完成"
}

rollback_k8s() {
  log "=== K8s 回滚 ==="
  if ! command -v kubectl >/dev/null 2>&1; then
    fail "未找到 kubectl"
  fi
  TARGET="${1:-}"
  if [ -n "$TARGET" ]; then
    log "回滚 Deployment: $TARGET"
    kubectl rollout undo deployment/"$TARGET" -n paas || fail "rollout undo $TARGET"
    kubectl rollout status deployment/"$TARGET" -n paas --timeout=120s || true
  else
    for d in gateway governance; do
      log "回滚 Deployment: $d"
      kubectl rollout undo deployment/"$d" -n paas 2>/dev/null || true
      kubectl rollout status deployment/"$d" -n paas --timeout=120s 2>/dev/null || true
    done
  fi
  ok "K8s 回滚完成. 查看: kubectl get pods -n paas"
}

MODE="${1:-}"
shift || true
case "$MODE" in
  docker) rollback_docker "$@" ;;
  k8s)    rollback_k8s "$@" ;;
  *)      echo "用法: $0 docker [SERVICE] | $0 k8s [DEPLOYMENT_NAME]"; exit 1 ;;
esac
exit 0
