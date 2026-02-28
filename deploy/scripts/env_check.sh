#!/usr/bin/env sh
# 部署环境检查：Docker/Compose/kubectl、.env、端口占用、网关可达性
# 用法: ./deploy/scripts/env_check.sh [docker|k8s]
# 不传参数时同时检查 Docker 与 .env；传 docker 仅检查单机 Docker；传 k8s 仅检查 K8s 集群

set -e
ROOT="${0%/*}/../.."
DEPLOY_DIR="${ROOT}/deploy"
ENV_FILE="${DEPLOY_DIR}/.env"
LOG_FILE="${DEPLOY_DIR}/env_check.log"

log() { echo "[env_check] $*" | tee -a "$LOG_FILE"; }
ok() { echo "[env_check]   [OK] $*" | tee -a "$LOG_FILE"; }
fail() { echo "[env_check]   [FAIL] $*" | tee -a "$LOG_FILE"; return 1; }

check_docker() {
  log "=== Docker 单机环境 ==="
  if ! command -v docker >/dev/null 2>&1; then
    fail "未找到 docker，请先安装 Docker"
    return 1
  fi
  ok "docker 已安装: $(docker --version 2>/dev/null | head -1)"
  COMPOSE="docker compose"
  if ! $COMPOSE version >/dev/null 2>&1; then
    COMPOSE="docker-compose"
  fi
  if ! $COMPOSE version >/dev/null 2>&1; then
    fail "未找到 docker compose / docker-compose"
    return 1
  fi
  ok "compose 可用: $COMPOSE"
  if [ ! -f "$ENV_FILE" ]; then
    if [ -f "${DEPLOY_DIR}/.env.example" ]; then
      log "未找到 .env，从 .env.example 复制"
      cp "${DEPLOY_DIR}/.env.example" "$ENV_FILE"
      ok "已创建 deploy/.env"
    else
      fail "未找到 deploy/.env 或 .env.example"
      return 1
    fi
  else
    ok "deploy/.env 存在"
  fi
  # 端口占用（仅提示）
  for port in 8000 8005 9000 5173 5174; do
    if command -v netstat >/dev/null 2>&1; then
      if netstat -tuln 2>/dev/null | grep -q "[:.]${port}[^0-9]"; then
        log "  端口 $port 已被占用（若为本次部署可忽略）"
      fi
    fi
  done
  return 0
}

check_k8s() {
  log "=== K8s 集群环境 ==="
  if ! command -v kubectl >/dev/null 2>&1; then
    fail "未找到 kubectl"
    return 1
  fi
  ok "kubectl 已安装"
  if ! kubectl cluster-info >/dev/null 2>&1; then
    fail "无法连接集群，请检查 kubeconfig"
    return 1
  fi
  ok "集群可达"
  if ! kubectl get ns paas >/dev/null 2>&1; then
    log "  namespace paas 尚未创建（部署后将创建）"
  else
    ok "namespace paas 存在"
  fi
  return 0
}

MODE="${1:-all}"
: > "$LOG_FILE"
log "环境检查开始 $(date -u +"%Y-%m-%dT%H:%M:%SZ")"

if [ "$MODE" = "docker" ] || [ "$MODE" = "all" ]; then
  check_docker || exit 1
fi
if [ "$MODE" = "k8s" ] || [ "$MODE" = "all" ]; then
  check_k8s || exit 1
fi

log "环境检查通过"
exit 0
