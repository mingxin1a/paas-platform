#!/usr/bin/env sh
# SuperPaaS 一键部署脚本（全量化体系规范）
# 能力：环境检查、依赖就绪、PaaS 核心 + 网关 + 细胞批量 + 双端前端、冒烟测试；支持增量部署与失败回滚
# 用法:
#   全量部署: ./deploy/deploy.sh  或  sh deploy/deploy.sh
#   增量部署: ./deploy/deploy.sh --only gateway,crm-cell
#   仅启动不构建: ./deploy/deploy.sh --skip-build
#   跳过冒烟: ./deploy/deploy.sh --no-smoke
# 配置: DEPLOY_MODE=docker（默认），后续可扩展 DEPLOY_MODE=k8s；所有端口与路由见 deploy/.env

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEPLOY_DIR="${ROOT}/deploy"
COMPOSE_FILE="${DEPLOY_DIR}/docker-compose.yml"
ENV_FILE="${DEPLOY_DIR}/.env"
LOG_FILE="${DEPLOY_DIR}/deploy.log"
SMOKE_SCRIPT="${DEPLOY_DIR}/smoke_test.py"

# 服务分组（与 docker-compose.yml 一致，配置解耦便于扩展 K8s）
PAAS_CORE_SERVICES="governance monitor gateway"
CELL_SERVICES="crm-cell erp-cell wms-cell hrm-cell oa-cell mes-cell tms-cell srm-cell plm-cell ems-cell his-cell lis-cell lims-cell"
FRONTEND_SERVICES="frontend frontend-admin"
ALL_SERVICES="${PAAS_CORE_SERVICES} ${CELL_SERVICES} ${FRONTEND_SERVICES}"

# 本次启动的服务（用于回滚）
STARTED_SERVICES=""

log() {
  echo "[deploy] $*" | tee -a "$LOG_FILE"
}

log_step() {
  echo "[deploy] === $* ===" | tee -a "$LOG_FILE"
}

log_ok() {
  echo "[deploy]   [OK] $*" | tee -a "$LOG_FILE"
}

log_fail() {
  echo "[deploy]   [FAIL] $*" | tee -a "$LOG_FILE"
}

# 解析参数
SKIP_BUILD=""
ONLY_SERVICES=""
NO_SMOKE=""
ROLLBACK_ON_FAIL="${ROLLBACK_ON_FAIL:-1}"
DEPLOY_MODE="${DEPLOY_MODE:-docker}"
DEPLOY_ENV="${DEPLOY_ENV:-}"

for arg in "$@"; do
  case "$arg" in
    --skip-build)   SKIP_BUILD=1 ;;
    --no-smoke)     NO_SMOKE=1 ;;
    --only=*)       ONLY_SERVICES="${arg#--only=}" ;;
    --only)         ONLY_SERVICES="" ;;
    --no-rollback)  ROLLBACK_ON_FAIL="" ;;
    --env=*)        DEPLOY_ENV="${arg#--env=}" ;;
  esac
done
# 规范化：逗号改空格
if [ -n "$ONLY_SERVICES" ]; then
  ONLY_SERVICES="$(echo "$ONLY_SERVICES" | tr ',' ' ')"
fi
# 多环境：若指定 --env=dev|test|staging|prod，使用 deploy/env/.env.<env> 作为本次部署的 .env
if [ -n "$DEPLOY_ENV" ]; then
  ENV_OVERRIDE="${DEPLOY_DIR}/env/.env.${DEPLOY_ENV}"
  if [ -f "$ENV_OVERRIDE" ]; then
    log "环境: $DEPLOY_ENV，使用 $ENV_OVERRIDE"
    ENV_FILE="$ENV_OVERRIDE"
    export DEPLOY_ENV
  else
    log "未找到 ${ENV_OVERRIDE}，使用默认 .env"
  fi
fi

# Docker Compose 命令
COMPOSE="docker compose"
if ! $COMPOSE version >/dev/null 2>&1; then
  COMPOSE="docker-compose"
fi

# ---------- 0. 环境检查 ----------
env_check() {
  log_step "0/6 环境检查"
  if ! command -v docker >/dev/null 2>&1; then
    log_fail "未找到 docker，请先安装 Docker"
    return 1
  fi
  log_ok "docker 已安装"
  if ! $COMPOSE -f "$COMPOSE_FILE" config >/dev/null 2>&1; then
    log_fail "docker compose 配置无效或未安装 docker-compose"
    return 1
  fi
  log_ok "docker compose 可用"
  if [ ! -f "$ENV_FILE" ]; then
    if [ -f "${DEPLOY_DIR}/.env.example" ]; then
      log "未找到 .env，从 .env.example 复制"
      cp "${DEPLOY_DIR}/.env.example" "$ENV_FILE"
      log_ok "已创建 deploy/.env"
    else
      log_fail "未找到 deploy/.env 或 .env.example"
      return 1
    fi
  else
    log_ok "deploy/.env 存在"
  fi
  if [ "$DEPLOY_MODE" = "k8s" ]; then
    log "DEPLOY_MODE=k8s（当前脚本仅实现 docker，K8s 为预留扩展）"
  fi
  return 0
}

# ---------- 1. 依赖就绪（Docker 模式下仅校验镜像可构建） ----------
deps_ready() {
  log_step "1/6 依赖就绪"
  if [ -n "$SKIP_BUILD" ]; then
    log_ok "跳过构建（--skip-build）"
    return 0
  fi
  log "校验 compose 配置可解析..."
  if ! $COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" config -q 2>/dev/null; then
    log_fail "compose 配置解析失败"
    return 1
  fi
  log_ok "compose 配置有效"
  return 0
}

# 检查服务名是否在增量列表内（整词匹配）
service_in_only() {
  local s="$1"
  for o in $ONLY_SERVICES; do
    [ "$o" = "$s" ] && return 0
  done
  return 1
}

# ---------- 2. PaaS 核心服务启动 ----------
start_paas_core() {
  log_step "2/6 PaaS 核心服务（governance, monitor, gateway）"
  if [ -n "$ONLY_SERVICES" ]; then
    need=""
    for s in governance monitor gateway; do
      service_in_only "$s" && need="${need} $s"
    done
    [ -z "$need" ] && { log_ok "增量部署未包含 PaaS 核心，跳过"; return 0; }
    BUILD_ARG=""
    [ -z "$SKIP_BUILD" ] && BUILD_ARG="--build"
    if ! $COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d $BUILD_ARG $need 2>>"$LOG_FILE"; then
      log_fail "PaaS 核心启动失败"
      return 1
    fi
    STARTED_SERVICES="${STARTED_SERVICES} $need"
  else
    BUILD_ARG=""
    [ -z "$SKIP_BUILD" ] && BUILD_ARG="--build"
    if ! $COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d $BUILD_ARG governance monitor gateway 2>>"$LOG_FILE"; then
      log_fail "PaaS 核心启动失败"
      return 1
    fi
    STARTED_SERVICES="${STARTED_SERVICES} governance monitor gateway"
  fi
  log_ok "PaaS 核心已启动（governance:8005, gateway:8000, monitor:9000）"
  return 0
}

# ---------- 3. 网关就绪（依赖治理健康后网关才 healthy） ----------
wait_gateway() {
  log_step "3/6 等待网关就绪"
  GATEWAY_URL="${GATEWAY_URL:-http://localhost:8000}"
  export GATEWAY_URL
  max=30
  i=0
  while [ $i -lt $max ]; do
    if python3 "${SMOKE_SCRIPT}" 2>/dev/null || python "${SMOKE_SCRIPT}" 2>/dev/null; then
      log_ok "网关已就绪"
      return 0
    fi
    i=$((i + 1))
    log "  等待网关... $i/$max"
    sleep 3
  done
  log_fail "网关在预期时间内未就绪"
  return 1
}

# ---------- 4. 细胞模块批量启动 ----------
start_cells() {
  log_step "4/6 细胞模块批量启动"
  if [ -n "$ONLY_SERVICES" ]; then
    need=""
    for s in $CELL_SERVICES; do
      service_in_only "$s" && need="${need} $s"
    done
    [ -z "$need" ] && { log_ok "增量部署未包含细胞，跳过"; return 0; }
    BUILD_ARG=""
    [ -z "$SKIP_BUILD" ] && BUILD_ARG="--build"
    if ! $COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d $BUILD_ARG $need 2>>"$LOG_FILE"; then
      log_fail "细胞服务启动失败"
      return 1
    fi
    STARTED_SERVICES="${STARTED_SERVICES} $need"
  else
    BUILD_ARG=""
    [ -z "$SKIP_BUILD" ] && BUILD_ARG="--build"
    if ! $COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d $BUILD_ARG $CELL_SERVICES 2>>"$LOG_FILE"; then
      log_fail "细胞服务启动失败"
      return 1
    fi
    STARTED_SERVICES="${STARTED_SERVICES} $CELL_SERVICES"
  fi
  log_ok "细胞模块已启动"
  return 0
}

# ---------- 5. 双端前端启动 ----------
start_frontends() {
  log_step "5/6 双端前端启动"
  if [ -n "$ONLY_SERVICES" ]; then
    need=""
    for s in frontend frontend-admin; do
      service_in_only "$s" && need="${need} $s"
    done
    [ -z "$need" ] && { log_ok "增量部署未包含前端，跳过"; return 0; }
    BUILD_ARG=""
    [ -z "$SKIP_BUILD" ] && BUILD_ARG="--build"
    if ! $COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d $BUILD_ARG $need 2>>"$LOG_FILE"; then
      log_fail "前端启动失败"
      return 1
    fi
    STARTED_SERVICES="${STARTED_SERVICES} $need"
  else
    BUILD_ARG=""
    [ -z "$SKIP_BUILD" ] && BUILD_ARG="--build"
    if ! $COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d $BUILD_ARG frontend frontend-admin 2>>"$LOG_FILE"; then
      log_fail "前端启动失败"
      return 1
    fi
    STARTED_SERVICES="${STARTED_SERVICES} frontend frontend-admin"
  fi
  log_ok "双端前端已启动（client:5173, admin:5174）"
  return 0
}

# ---------- 6. 冒烟测试 ----------
run_smoke() {
  log_step "6/6 冒烟测试"
  if [ -n "$NO_SMOKE" ]; then
    log_ok "已跳过（--no-smoke）"
    return 0
  fi
  export GATEWAY_URL="${GATEWAY_URL:-http://localhost:8000}"
  if python3 "$SMOKE_SCRIPT" 2>>"$LOG_FILE" || python "$SMOKE_SCRIPT" 2>>"$LOG_FILE"; then
    log_ok "冒烟测试通过"
    return 0
  fi
  log_fail "冒烟测试未通过"
  return 1
}

# ---------- 回滚：停止本次启动的服务 ----------
rollback() {
  log "回滚：停止本次启动的服务..."
  for s in $STARTED_SERVICES; do
    [ -z "$s" ] && continue
    $COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" stop "$s" 2>>"$LOG_FILE" || true
  done
  log "回滚完成（已 stop 本次启动的服务）；可手动执行 docker compose down 做全量停止"
}

# ---------- 主流程 ----------
main() {
  cd "$ROOT"
  : > "$LOG_FILE"
  log "$(date -u +"%Y-%m-%dT%H:%M:%SZ") 部署开始 DEPLOY_MODE=$DEPLOY_MODE DEPLOY_ENV=${DEPLOY_ENV:-default} ONLY=${ONLY_SERVICES:-全量} SKIP_BUILD=${SKIP_BUILD:-0}"
  log "日志文件: $LOG_FILE"

  if ! env_check; then
    log "部署终止：环境检查未通过"
    exit 1
  fi
  if ! deps_ready; then
    log "部署终止：依赖就绪未通过"
    exit 1
  fi

  # 若指定 --only，则只启动指定服务；仅当包含 gateway 时等待并就绪后做冒烟
  if [ -n "$ONLY_SERVICES" ]; then
    if service_in_only "governance" || service_in_only "monitor" || service_in_only "gateway"; then
      if ! start_paas_core; then
        [ -n "$ROLLBACK_ON_FAIL" ] && rollback
        exit 1
      fi
      if ! wait_gateway; then
        [ -n "$ROLLBACK_ON_FAIL" ] && rollback
        exit 1
      fi
    fi
    need_cells=""
    for s in $CELL_SERVICES; do service_in_only "$s" && need_cells=1; done
    [ -n "$need_cells" ] && if ! start_cells; then
      [ -n "$ROLLBACK_ON_FAIL" ] && rollback
      exit 1
    fi
    if service_in_only "frontend" || service_in_only "frontend-admin"; then
      if ! start_frontends; then
        [ -n "$ROLLBACK_ON_FAIL" ] && rollback
        exit 1
      fi
    fi
    if [ -z "$NO_SMOKE" ] && service_in_only "gateway"; then
      if ! run_smoke; then
        [ -n "$ROLLBACK_ON_FAIL" ] && rollback
        exit 1
      fi
    else
      [ -z "$NO_SMOKE" ] && log_ok "增量部署未含 gateway，跳过冒烟"
    fi
  else
    if ! start_paas_core; then
      [ -n "$ROLLBACK_ON_FAIL" ] && rollback
      exit 1
    fi
    if ! wait_gateway; then
      [ -n "$ROLLBACK_ON_FAIL" ] && rollback
      exit 1
    fi
    if ! start_cells; then
      [ -n "$ROLLBACK_ON_FAIL" ] && rollback
      exit 1
    fi
    if ! start_frontends; then
      [ -n "$ROLLBACK_ON_FAIL" ] && rollback
      exit 1
    fi
    if ! run_smoke; then
      [ -n "$ROLLBACK_ON_FAIL" ] && rollback
      exit 1
    fi
  fi

  log "$(date -u +"%Y-%m-%dT%H:%M:%SZ") 部署成功"
  echo ""
  echo "  SuperPaaS 平台已就绪（autonomous mode）"
  echo "  网关:    http://localhost:8000  健康: http://localhost:8000/health"
  echo "  治理:    http://localhost:8005  监控: http://localhost:9000"
  echo "  客户端:  http://localhost:5173  管理端: http://localhost:5174"
  echo "  部署日志: $LOG_FILE"
  echo ""
  exit 0
}

main "$@"
