# PaaS 核心层商用运维手册

**版本**：1.0  
**适用对象**：运维人员、系统管理员  
**范围**：网关、认证中心、微服务治理、监控（数据湖若存在则一并说明）

---

## 一、组件概览

| 组件 | 端口（默认） | 作用 |
|------|--------------|------|
| 网关（Gateway） | 8000 | 统一入口、路由转发、认证校验、请求头透传、熔断 |
| 治理中心（Governance） | 8005 | 细胞注册与发现、健康巡检、配置下发（可选） |
| 监控中心（Monitor） | 9000 | 健康汇总、黄金指标、与 Prometheus 对接 |

认证能力当前由**网关**提供（登录、Token、用户与细胞权限）；独立认证中心可后续扩展。

---

## 二、网关

### 2.1 配置要点

| 环境变量 | 说明 | 示例 |
|----------|------|------|
| GATEWAY_PORT | 监听端口 | 8000 |
| USE_REAL_FORWARD | 是否真实转发到细胞 | 1 |
| GOVERNANCE_URL | 治理中心地址 | http://governance:8005 |
| CELL_*_URL | 各细胞地址 | CELL_CRM_URL=http://crm-cell:8001 |
| GATEWAY_REQUIRE_TENANT_ID | 是否强制 X-Tenant-Id | 生产建议 1 |
| GATEWAY_SIGNING_SECRET | 网关加签密钥（可选） | 与细胞验签配合 |

### 2.2 监控与健康

- **健康**：`GET /health` 返回 200 表示网关存活。
- **管理端**：`GET /api/admin/health-summary`（需 Authorization）可查看网关自身及各细胞健康汇总。
- **日志**：网关会记录请求转发、熔断、缺失请求头等，建议输出到标准输出或集中日志，便于排查 502/503。

### 2.3 故障处理

| 现象 | 处理 |
|------|------|
| 502 Cell Unreachable | 检查对应 CELL_*_URL 是否可达、细胞是否启动；网络与防火墙。 |
| 400 Missing Header | 请求缺少 Content-Type/Authorization/X-Request-ID（POST/PUT 时），补全请求头。 |
| 400 Missing Tenant | 生产开启 GATEWAY_REQUIRE_TENANT_ID 后未传 X-Tenant-Id，在请求头中携带。 |
| 503 Circuit Open | 该细胞熔断打开，等恢复或重启细胞后重试。 |

---

## 三、认证中心（当前由网关实现）

| 能力 | 说明 |
|------|------|
| 登录 | POST /api/auth/login，body：username、password；返回 token、user（含 allowedCells）。 |
| 当前用户 | GET /api/auth/me，Header：Authorization: Bearer \<token\>。 |
| 用户与细胞权限 | 管理端可配置用户与 allowedCells；网关转发时可根据 token 校验是否允许访问某细胞。 |

运维注意：生产应替换为独立认证服务（如 OAuth2/OIDC），并更新网关配置。

---

## 四、微服务治理（治理中心）

### 4.1 配置

- 治理中心通过环境变量获取各细胞 URL（CELL_CRM_URL 等），并定期对细胞做健康巡检。
- 网关可从治理中心拉取细胞列表与健康状态（若配置 GOVERNANCE_URL），或直接使用环境变量中的 CELL_*_URL。

### 4.2 监控与健康

- **健康**：`GET /api/governance/health`。
- **细胞健康**：`GET /api/governance/health/cells`（若实现）返回各细胞健康结果，供网关或监控中心聚合。

### 4.3 故障处理

- 治理中心不可用时，网关若已配置 CELL_*_URL 仍可直连细胞，仅影响「从治理中心动态发现」能力。
- 治理中心日志可排查：注册失败、健康检查超时等。

---

## 五、监控中心（Monitor）

- **健康**：`GET /health`。
- **指标**：可暴露 Prometheus 格式指标，供 `deploy/monitoring/prometheus.example.yml` 抓取。
- 运维建议：将 Prometheus + Grafana 与监控中心、网关、各细胞 /health 或 /metrics 一起配置，并设置告警规则（见《超级PaaS平台商用交付总手册》监控告警配置）。

---

## 六、数据湖（若存在）

若平台侧提供数据湖或日志汇聚，运维需关注：存储容量、保留策略、访问权限与审计。具体配置与故障处理以实际数据湖组件文档为准。

---

**文档归属**：商用交付文档包 · PaaS 层  
**维护**：随版本更新。
