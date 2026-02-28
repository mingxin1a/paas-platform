# PaaS 核心层高可用部署手册

本文档描述 API 网关、认证会话、治理中心的集群部署、负载均衡、故障转移、熔断降级、主备与异地容灾的完整步骤与配置示例。所有增强不修改 PaaS 核心架构，不引入业务逻辑。

---

## 一、能力总览

| 能力 | 说明 | 实现方式 |
|------|------|----------|
| 网关集群与无状态 | 多实例水平扩展，无本地会话 | 会话外置 Redis；LB 将流量分到多实例 |
| 负载均衡与故障转移 | 单实例宕机后流量切到健康实例 | Nginx/K8s Service 健康检查 + fail_timeout |
| 认证 Token 共享 | 多网关实例共享登录态 | GATEWAY_SESSION_STORE_URL=redis://... |
| 会话持久化 | 重启/故障后会话不丢 | Redis 持久化（AOF）或 Redis 主从 |
| 治理故障隔离 | 仅将流量转发到健康细胞 | 治理中心健康巡检，resolve 仅返回 healthy |
| 熔断降级 | 细胞异常率过高时快速失败 | 网关熔断器（可配置窗口与阈值） |
| 重试机制 | 临时 5xx 或网络抖动自动重试 | 网关代理重试 + 治理发现重试 |
| 健康巡检与自动恢复 | 细胞恢复后自动重新纳入 | 治理健康环成功一次即 set_healthy(True) |
| 主备切换 | 单点故障时 VIP 或流量切备机 | Keepalived 或云 SLB 健康检查 |
| 异地容灾与数据双活 | 会话与数据可跨机房 | Redis 主从/集群；备份与 DR 站点预案 |

---

## 二、单机部署

适用于开发与最小生产环境。

### 2.1 步骤

1. 安装依赖：Python 3.10+，或使用 Docker。
2. 配置环境变量：复制 `deploy/.env.example` 为 `.env`，按需设置 `GATEWAY_PORT`、`GOVERNANCE_URL`、`CELL_*_URL`。
3. 启动治理中心：`python deploy/run_governance.py`（或 `GOVERNANCE_PORT=8005`）。
4. 启动网关：`python deploy/run_gateway.py`（或 `GATEWAY_PORT=8000`）。
5. 校验：`curl http://localhost:8000/health` 返回 `{"status":"up"}`。

### 2.2 Docker 单机

```bash
cd deploy
docker-compose up -d governance gateway
curl http://localhost:8000/health
```

---

## 三、集群部署（多实例无状态）

### 3.1 网关多实例 + Redis 会话共享

- **目标**：多台网关实例共享 Token 存储，任意实例均可处理登录与 /api/auth/me；单实例宕机不影响已登录用户。
- **前提**：Redis 可用（单机或哨兵/集群）。

**环境变量（每台网关）：**

```bash
GATEWAY_PORT=8000
USE_REAL_FORWARD=1
GOVERNANCE_URL=http://governance:8005
GATEWAY_SESSION_STORE_URL=redis://<redis_host>:6379/0
GATEWAY_SESSION_TTL_SEC=86400
GATEWAY_PROXY_RETRY_COUNT=2
GATEWAY_PROXY_TIMEOUT_SEC=30
CELL_CRM_URL=...
```

**Docker Compose 示例（两实例 + Redis + Nginx LB）：**

```bash
cd deploy
docker-compose -f docker-compose-ha.yml up -d
# 对外端口 8000 由 nginx 负载到 gateway1、gateway2；会话存 Redis
```

配置文件：`deploy/config/high-availability/nginx-gateway-lb.conf`（upstream 为 gateway1:8000、gateway2:8000）。

### 3.2 治理中心多实例

- 治理中心当前为内存存储（注册表、健康、RED 指标），多实例间不共享状态。
- **推荐**：治理中心单实例或主备即可；网关通过 GOVERNANCE_URL 指向治理中心，治理中心可部署为 K8s Deployment 多副本 + Service，由 K8s 做 LB 与故障转移。
- 若需治理高可用，可将 GOVERNANCE_URL 配置为治理中心 LB 地址（如 Nginx 或 K8s Service）。

### 3.3 认证中心（网关内建认证）集群

- 登录与 /api/auth/me 由网关提供；Token 存 Redis 后，多网关实例即等效「认证中心集群」。
- 无需单独部署认证服务即可实现 Token 共享与会话持久化；若未来接入独立认证中心，可继续使用同一 Redis 存储会话。

---

## 四、负载均衡与故障自动转移

### 4.1 Nginx 负载均衡

- 使用 `deploy/config/high-availability/nginx-gateway-lb.conf`。
- 要点：`max_fails=2`、`fail_timeout=10s`，某台 gateway 连续失败 2 次后 10 秒内不再转发，实现故障转移。
- 将 `/api`、`/health` 等代理到 `gateway_backend`。

### 4.2 Kubernetes

- 网关：Deployment `replicas: 2` 或更多，Service 类型 ClusterIP 或 LoadBalancer；Ingress 指向该 Service。
- 健康检查：livenessProbe / readinessProbe 使用 `GET /health`。
- 示例见 `deploy/k8s/gateway-deploy.yaml`（可增加 replicas 与 resource limits）。

---

## 五、熔断、重试与健康巡检

### 5.1 熔断（网关）

- 按《接口设计说明书》3.3.1：时间窗内异常率 ≥ 阈值则熔断，半开探测成功后恢复。
- 环境变量（可选）：
  - `GATEWAY_CB_WINDOW_SEC`：时间窗（秒），默认 10
  - `GATEWAY_CB_FAILURE_RATIO`：异常率阈值，默认 0.5
  - `GATEWAY_CB_HALF_OPEN_PROBES`：半开探测次数，默认 3
  - `GATEWAY_CB_PROBE_SUCCESSES_TO_CLOSE`：连续成功次数后关闭熔断，默认 2

### 5.2 代理重试（网关）

- 对细胞转发时，遇 5xx 或网络异常自动重试。
- `GATEWAY_PROXY_RETRY_COUNT`：重试次数（默认 2）；`GATEWAY_PROXY_TIMEOUT_SEC`：单次超时（默认 30）。

### 5.3 治理发现重试

- 网关调用治理中心 discovery 时支持重试与退避。
- `GOVERNANCE_DISCOVERY_RETRY`：重试次数；`GOVERNANCE_DISCOVERY_TIMEOUT`：超时；`GOVERNANCE_DISCOVERY_BACKOFF_BASE`：退避基数。

### 5.4 健康巡检与故障自动恢复

- 治理中心周期性对细胞 `GET /health`；连续 N 次失败则标记不健康（不参与发现），任一次成功即恢复。
- 环境变量：`GOVERNANCE_HEALTH_INTERVAL_SEC`、`GOVERNANCE_HEALTH_FAILURE_THRESHOLD`、`GOVERNANCE_HEALTH_TIMEOUT_SEC`（见 `.env.example`）。

---

## 六、主备切换与异地容灾

### 6.1 主备（单 VIP）

- 适用：两台网关（或网关+ Nginx）主备，通过一个 VIP 对外。
- 方式一：Keepalived。示例配置见 `deploy/config/high-availability/keepalived-gateway-example.conf`。备节点 `state BACKUP`、`priority 90`；主节点故障后 VIP 漂移到备机。
- 方式二：云厂商 SLB/ELB 配置主备后端组，健康检查指向 `/health`。

### 6.2 异地容灾

- **RPO/RTO**：通过备份脚本（`deploy/scripts/backup_cells.sh`、`restore_cells.sh`）与对象存储异地备份降低 RPO；RTO 依赖演练与切换预案。
- **DR 站点准备**：在异地部署网关+治理+细胞，从对象存储恢复数据；切换 DNS 或 SLB 到 DR 站点。示例脚本：`deploy/scripts/dr_dual_active/prepare_dr_site.sh`（需按实际填写镜像与 S3 配置）。
- **配置示例**：`deploy/scripts/dr_dual_active/env.example`（DR_SITE_ID、BACKUP_S3_* 等）。

### 6.3 数据双活同步

- **会话**：Redis 主从或 Redis Cluster 部署在跨机房，网关各实例配置同一 Redis 地址（或通过代理访问），即实现会话双活。
- **治理**：治理中心为内存状态，DR 站点启动后从环境变量 `CELL_*_URL` 或配置重新拉取路由即可。
- **细胞数据**：由各细胞自身数据库主从/集群与备份策略保证，非本手册范围。

---

## 七、配置速查

| 变量 | 说明 | 默认 |
|------|------|------|
| GATEWAY_SESSION_STORE_URL | Redis URL，空则内存 | 空 |
| GATEWAY_SESSION_TTL_SEC | Token 过期时间（秒） | 86400 |
| GATEWAY_PROXY_RETRY_COUNT | 转发重试次数 | 2 |
| GATEWAY_PROXY_TIMEOUT_SEC | 转发超时（秒） | 30 |
| GATEWAY_CB_WINDOW_SEC | 熔断时间窗 | 10 |
| GATEWAY_CB_FAILURE_RATIO | 熔断异常率阈值 | 0.5 |
| GOVERNANCE_HEALTH_INTERVAL_SEC | 健康巡检间隔 | 30 |
| GOVERNANCE_HEALTH_FAILURE_THRESHOLD | 连续失败次数后标记不健康 | 3 |
| GOVERNANCE_DISCOVERY_RETRY | 发现重试次数 | 2 |

---

## 八、文件索引

- 高可用 Compose：`deploy/docker-compose-ha.yml`
- Nginx 网关 LB：`deploy/config/high-availability/nginx-gateway-lb.conf`
- Keepalived 示例：`deploy/config/high-availability/keepalived-gateway-example.conf`
- 主备切换示例脚本：`deploy/scripts/failover_example.sh`
- 异地容灾准备：`deploy/scripts/dr_dual_active/prepare_dr_site.sh`、`env.example`
- 环境变量示例：`deploy/.env.example`

---

**文档归属**：PaaS 核心层高可用 · 商用交付
