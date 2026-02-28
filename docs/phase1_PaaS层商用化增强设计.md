# 阶段 1：PaaS 层商用化增强设计

**目标**：在不动业务 Cell 的前提下，先加固 PaaS 地基——多租户隔离、数据与传输安全、高可用与可观测。

---

## 1. 多租户隔离增强

### 1.1 现状

- 网关转发时已携带 `X-Tenant-Id`（若客户端传入），下游 Cell（如 ERP）按该头做租户过滤。
- 认证层为 Mock 用户，无租户绑定；路由配置为全局，非按租户。

### 1.2 设计

| 项 | 方案 | 落地位置 |
|----|------|----------|
| 租户必传 | 生产模式可选：对 `/api/v1/<cell>/...` 要求请求头带 `X-Tenant-Id`，缺失则 400，错误码 `MISSING_TENANT_ID` | 网关 `platform_core/core/gateway/app.py` |
| 租户传递 | 保持现有逻辑：将 `X-Tenant-Id` 列入 `headers_to_forward`，确保传递给 Cell | 已满足 |
| 租户与用户绑定 | 后续对接认证中心：登录返回 `tenantId`，前端/网关在请求中注入；当前 Mock 可增加 `tenantId` 字段 | auth_center / 网关 |
| 配置按租户 | 远期：路由/限流等按 tenant 配置；阶段 1 仅预留设计，不做实现 | 设计预留 |

### 1.3 实现要点

- 环境变量 `GATEWAY_REQUIRE_TENANT_ID=1` 时，代理请求校验 `X-Tenant-Id` 非空。
- 错误响应符合《接口设计说明书》：`code`、`message`、`details`、`requestId`。

---

## 2. 数据与传输安全

### 2.1 传输安全

| 项 | 方案 |
|----|------|
| HTTPS | 生产环境由接入层（Nginx/Ingress）终结 TLS，网关与 Cell 可内网 HTTP；文档与部署说明中明确「对外 HTTPS」 |
| 签名与验签 | 已有：网关 `GATEWAY_SIGNING_SECRET`、Cell `CELL_VERIFY_SIGNATURE`；保持现有实现 |

### 2.2 存储加密与脱敏

| 项 | 方案 |
|----|------|
| 敏感字段加密 | Cell 层实现：对手机号、身份证等落库前 AES 加密，密钥来自环境变量或密钥服务；PaaS 层不存业务数据 |
| 展示脱敏 | Cell 层或前端：列表/日志中手机号、身份证等脱敏展示；在《接口设计说明书》与各 Cell 交付手册中约定 |
| 密钥管理 | 禁止硬编码；密钥仅环境变量或 K8s Secret / 云 KMS；文档中说明 |

阶段 1 在 PaaS 层不做存储加密实现，仅在总手册与本文档中明确规范，由各 Cell 与前端落地。

---

## 3. 高可用能力

### 3.1 现状

- 网关无状态，可多实例；治理中心支持健康巡检；有熔断与红绿灯。

### 3.2 设计

| 项 | 方案 |
|----|------|
| 集群部署 | 网关、治理中心支持多副本；负载均衡由 Docker/K8s 或 Nginx 完成；在 deploy 文档中说明 |
| 故障转移 | 依赖 K8s 或 Docker 健康检查与重启；网关调用 Cell 失败时已有 503/熔断 |
| 配置中心 | 远期可选：路由/限流从配置中心拉取；阶段 1 仍使用环境变量与 `GATEWAY_ROUTES_PATH` |

阶段 1 交付：在 `deploy/` 中补充「高可用部署说明」小节（多实例、健康检查、无状态）。

---

## 4. 监控 / 告警 / 日志聚合

### 4.1 监控

| 项 | 方案 |
|----|------|
| 指标暴露 | 网关、治理中心、各 Cell 暴露 Prometheus 格式 `/metrics` 或由 sidecar 采集；已有 monitor 黄金指标时可对接 |
| Grafana | 提供示例 dashboard 的 JSON 或配置说明（服务健康、请求延迟、错误率） |
| 告警 | 提供示例 Prometheus AlertManager 规则（如 5xx 率、超时、健康检查失败） |

阶段 1 交付：`deploy/monitoring/` 下示例配置（如 `prometheus.yml` 片段、`alerts.example.yaml`）、`deploy/docs/监控与告警说明.md`。

### 4.2 日志

| 项 | 方案 |
|----|------|
| 格式 | 统一 JSON，含 `level`、`message`、`trace_id`、`tenant_id`（若有）、`timestamp` |
| 分级 | INFO/WARN/ERROR；错误必打 ERROR 并带 requestId/traceId |
| 聚合 | 部署侧用 Filebeat/Fluentd 等采集至 ELK 或云日志；文档说明 |

阶段 1 不实现日志后端，仅规范格式与级别，并在网关/治理中心现有日志上对齐。

---

## 5. 健康检查与故障检测

| 项 | 方案 |
|----|------|
| 网关 | 已有 `/health`；可增加「下游 Cell 健康聚合」只读接口（如 `/api/admin/health-summary`），供 K8s 或监控探测 |
| Cell | 各 Cell 提供 `/health`；治理中心已巡检；保持 |
| 故障检测 | 熔断 + 健康巡检已具备；阶段 1 可增加「健康汇总」接口，便于运维一眼看到各 Cell 状态 |

---

## 6. 阶段 1 交付物清单

| 交付物 | 说明 |
|--------|------|
| 本文档 | phase1_PaaS层商用化增强设计.md |
| 网关租户校验 | `GATEWAY_REQUIRE_TENANT_ID=1` 时校验 `X-Tenant-Id` |
| 健康汇总 API | 网关或治理中心提供 `/api/admin/health-summary`（可选，依赖治理中心） |
| 部署与监控文档 | `deploy/docs/监控与告警说明.md`，`deploy/monitoring/` 示例配置 |
| 备份脚本示例 | `deploy/scripts/backup_example.sh` 或说明，供 DBA/运维扩展 |
| 阶段 1 交付报告 | 完成项/未完成项/风险点 |

---

**维护**：实现时若与本文档有偏差，请同步更新本文档并保留设计决策说明。
