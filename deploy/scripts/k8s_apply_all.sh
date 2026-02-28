#!/usr/bin/env sh
# K8s 生产级一键部署：Namespace、ConfigMap、Secret、Redis(可选)、PaaS 核心、全部细胞、前端、Ingress、HPA
# 用法: ./deploy/scripts/k8s_apply_all.sh [--no-redis] [--no-ingress] [--no-hpa]
# 从项目根执行；前置: kubectl 已配置、镜像已构建并推送

set -e
ROOT="${0%/*}/../.."
cd "$ROOT"
K8S_DIR="${ROOT}/deploy/k8s"

APPLY_REDIS=1
APPLY_INGRESS=1
APPLY_HPA=1
for arg in "$@"; do
  case "$arg" in
    --no-redis)   APPLY_REDIS=0 ;;
    --no-ingress) APPLY_INGRESS=0 ;;
    --no-hpa)     APPLY_HPA=0 ;;
  esac
done

log() { echo "[k8s] $*"; }
log_ok() { echo "[k8s]   [OK] $*"; }
log_fail() { echo "[k8s]   [FAIL] $*"; exit 1; }

log "=== 1/9 Namespace ==="
kubectl apply -f "${K8S_DIR}/00-namespace.yaml" || log_fail "00-namespace"
log_ok "namespace paas"

log "=== 2/9 ConfigMap ==="
kubectl apply -f "${K8S_DIR}/01-configmap.yaml" || log_fail "01-configmap"
log_ok "paas-env"

log "=== 3/9 Secret ==="
kubectl apply -f "${K8S_DIR}/02-secret.yaml" || log_fail "02-secret"
log_ok "paas-secret"

if [ "$APPLY_REDIS" = "1" ]; then
  log "=== 4/9 Redis (StatefulSet) ==="
  kubectl apply -f "${K8S_DIR}/10-redis-statefulset.yaml" || log_fail "10-redis"
  log_ok "redis"
else
  log "=== 4/9 Redis (跳过 --no-redis) ==="
fi

log "=== 5/9 PaaS 核心 (governance, gateway, monitor) ==="
kubectl apply -f "${K8S_DIR}/20-paas-core.yaml" || log_fail "20-paas-core"
log_ok "paas-core"

log "=== 6/9 Cells (13 细胞) ==="
kubectl apply -f "${K8S_DIR}/30-cells.yaml" || log_fail "30-cells"
log_ok "cells"

log "=== 7/9 Frontend ==="
kubectl apply -f "${K8S_DIR}/40-frontend.yaml" || log_fail "40-frontend"
log_ok "frontend"

if [ "$APPLY_INGRESS" = "1" ]; then
  log "=== 8/9 Ingress ==="
  kubectl apply -f "${K8S_DIR}/50-ingress.yaml" || log_fail "50-ingress"
  log_ok "ingress"
else
  log "=== 8/9 Ingress (跳过 --no-ingress) ==="
fi

if [ "$APPLY_HPA" = "1" ]; then
  log "=== 9/9 HPA ==="
  kubectl apply -f "${K8S_DIR}/60-hpa.yaml" || log_fail "60-hpa"
  log_ok "hpa"
else
  log "=== 9/9 HPA (跳过 --no-hpa) ==="
fi

log "Done. 检查: kubectl get pods -n paas"
