# K8s 生产级高可用部署

## 资源清单

| 文件 | 说明 |
|------|------|
| 00-namespace.yaml | Namespace `paas` |
| 01-configmap.yaml | 非敏感环境变量（细胞 URL、端口等） |
| 02-secret.yaml | 敏感配置（Token 等），部署前务必修改 |
| 10-redis-statefulset.yaml | Redis StatefulSet + Service（可选，网关会话共享） |
| 20-paas-core.yaml | 治理中心、网关、监控 Deployment + Service |
| 30-cells.yaml | 全部 13 细胞 Deployment + Service |
| 40-frontend.yaml | 客户端/管理端前端 Deployment + Service |
| 50-ingress.yaml | Ingress 统一入口（需 Ingress Controller） |
| 60-hpa.yaml | HPA 自动扩缩容（需 metrics-server） |

## 一键部署顺序

```bash
# 从项目根执行
./deploy/scripts/k8s_apply_all.sh
# 或手动按序
kubectl apply -f deploy/k8s/00-namespace.yaml
kubectl apply -f deploy/k8s/01-configmap.yaml
kubectl apply -f deploy/k8s/02-secret.yaml
kubectl apply -f deploy/k8s/10-redis-statefulset.yaml   # 可选
kubectl apply -f deploy/k8s/20-paas-core.yaml
kubectl apply -f deploy/k8s/30-cells.yaml
kubectl apply -f deploy/k8s/40-frontend.yaml
kubectl apply -f deploy/k8s/50-ingress.yaml
kubectl apply -f deploy/k8s/60-hpa.yaml
```

## 前置条件

- kubectl 已配置且可访问集群
- 镜像已构建并推送到仓库（如 superpaas/gateway:latest、superpaas/cell-crm:latest 等）
- 若使用 Ingress：集群已安装 Ingress Controller（如 nginx-ingress）
- 若使用 HPA：集群已安装 metrics-server

## 多环境

可通过 Kustomize 或不同 overlay 覆盖镜像标签、副本数、ConfigMap。参见《生产级部署运维手册》。
