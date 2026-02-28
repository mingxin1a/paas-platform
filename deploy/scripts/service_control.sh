#!/usr/bin/env sh
# 服务启停：Docker 单机 start/stop/restart；K8s  scale deployment 到 0 或原副本数
# 用法:
#   Docker: ./deploy/scripts/service_control.sh docker start|stop|restart [SERVICE1,SERVICE2]
#   K8s:    ./deploy/scripts/service_control.sh k8s start|stop [DEPLOYMENT1,DEPLOYMENT2]
# 不传服务列表时，Docker 操作全部；K8s stop 将 gateway/governance 等 scale 到 0，start 恢复到 2 或 1

set -e
ROOT="${0%/*}/../.."
cd "$ROOT"
DEPLOY_DIR="${ROOT}/deploy"
COMPOSE_FILE="${DEPLOY_DIR}/docker-compose.yml"
ENV_FILE="${DEPLOY_DIR}/.env"

log() { echo "[control] $*"; }

control_docker() {
  ACTION="${1:-}"
  ONLY="${2:-}"
  COMPOSE="docker compose"
  $COMPOSE version >/dev/null 2>&1 || COMPOSE="docker-compose"
  [ ! -f "$COMPOSE_FILE" ] && { echo "[control] [FAIL] 未找到 docker-compose.yml"; exit 1; }
  [ ! -f "$ENV_FILE" ] && { echo "[control] [FAIL] 未找到 .env"; exit 1; }
  case "$ACTION" in
    start)
      if [ -n "$ONLY" ]; then
        log "启动服务: $ONLY"
        $COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d $ONLY
      else
        log "启动全部服务"
        $COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d
      fi
      ;;
    stop)
      if [ -n "$ONLY" ]; then
        log "停止服务: $ONLY"
        $COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" stop $ONLY
      else
        log "停止全部服务"
        $COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" stop
      fi
      ;;
    restart)
      if [ -n "$ONLY" ]; then
        log "重启服务: $ONLY"
        $COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" restart $ONLY
      else
        log "重启全部服务"
        $COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" restart
      fi
      ;;
    *)
      echo "用法: $0 docker start|stop|restart [SERVICE1 SERVICE2 ...]"; exit 1
      ;;
  esac
  echo "[control]   [OK] 完成"
}

control_k8s() {
  ACTION="${1:-}"
  ONLY="${2:-}"
  if ! command -v kubectl >/dev/null 2>&1; then
    echo "[control] [FAIL] 未找到 kubectl"; exit 1
  fi
  # 默认副本数
  scale_gateway=2
  scale_governance=1
  scale_monitor=1
  scale_cell=2
  scale_frontend=1
  case "$ACTION" in
    start)
      if [ -n "$ONLY" ]; then
        for d in $(echo "$ONLY" | tr ',' ' '); do
          log "扩容: $d"
          kubectl scale deployment/"$d" -n paas --replicas=2 2>/dev/null || \
          kubectl scale deployment/"$d" -n paas --replicas=1 2>/dev/null || true
        done
      else
        kubectl scale deployment/gateway -n paas --replicas=$scale_gateway
        kubectl scale deployment/governance -n paas --replicas=$scale_governance
        kubectl scale deployment/monitor -n paas --replicas=$scale_monitor
        for c in cell-crm cell-erp cell-wms cell-hrm cell-oa cell-mes cell-tms cell-srm cell-plm cell-ems cell-his cell-lis cell-lims; do
          kubectl scale deployment/$c -n paas --replicas=$scale_cell 2>/dev/null || true
        done
        kubectl scale deployment/frontend -n paas --replicas=$scale_frontend 2>/dev/null || true
        kubectl scale deployment/frontend-admin -n paas --replicas=$scale_frontend 2>/dev/null || true
        log "全部 Deployment 已扩容"
      fi
      ;;
    stop)
      if [ -n "$ONLY" ]; then
        for d in $(echo "$ONLY" | tr ',' ' '); do
          log "缩容: $d -> 0"
          kubectl scale deployment/"$d" -n paas --replicas=0
        done
      else
        log "缩容核心与细胞至 0（仅保留 namespace）"
        for d in gateway governance monitor frontend frontend-admin cell-crm cell-erp cell-wms cell-hrm cell-oa cell-mes cell-tms cell-srm cell-plm cell-ems cell-his cell-lis cell-lims; do
          kubectl scale deployment/$d -n paas --replicas=0 2>/dev/null || true
        done
      fi
      ;;
    *)
      echo "用法: $0 k8s start|stop [DEPLOYMENT1,DEPLOYMENT2]"; exit 1
      ;;
  esac
  echo "[control]   [OK] 完成"
}

MODE="${1:-}"
ACTION="${2:-}"
shift 2 || true
LIST="$*"
case "$MODE" in
  docker) control_docker "$ACTION" $LIST ;;
  k8s)    control_k8s "$ACTION" "$LIST" ;;
  *)      echo "用法: $0 docker|k8s start|stop|restart [服务列表]"; exit 1 ;;
esac
exit 0
