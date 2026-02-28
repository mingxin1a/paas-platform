# 微服务治理与治理中心 API

基于细胞化架构，在 **platform_core** 下提供注册发现、健康巡检、故障隔离、链路追踪与 RED 指标能力，**不侵入业务细胞代码**，全部通过标准化 API 提供。

---

## 1. 能力概览

| 能力 | 说明 | 实现方式 |
|------|------|----------|
| **注册与发现** | 细胞注册、注销、服务发现（仅返回健康实例） | 治理中心 API + 网关可选从治理中心解析 |
| **健康巡检** | 定时对已注册细胞 GET /health，失败 N 次标记不健康 | 治理中心后台线程 |
| **故障隔离** | 发现接口仅返回健康细胞；网关熔断器按请求失败率熔断 | 治理中心 resolve + 网关 CircuitBreaker |
| **链路追踪** | trace_id/span_id 透传，治理中心存储 span，按 trace_id 查询 | 网关上报 POST /api/governance/ingest |
| **RED 指标** | 请求量、成功率、响应时间（含 P50/P99） | 同上 ingest，GET /api/governance/metrics 查询 |

---

## 2. 治理中心 API

基础路径：治理中心服务根地址，如 `http://localhost:8005`。

### 2.1 注册与发现

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/governance/register | 注册细胞。body: `{"cell":"crm","base_url":"http://crm-cell:8001"}` |
| DELETE | /api/governance/register/<cell> | 注销细胞 |
| GET | /api/governance/cells | 细胞列表及健康状态 |
| GET | /api/governance/discovery/<cell> | 服务发现：仅健康返回 200 + base_url，否则 503 |

### 2.2 数据上报（网关调用）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/governance/ingest | 网关上报 span + RED。body: `trace_id, span_id, cell, path, status_code, duration_ms` |

### 2.3 链路追踪

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/governance/traces?trace_id=xxx | 按 trace_id 查询链路 span 列表 |

### 2.4 RED 指标（对齐全量化体系）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/governance/metrics | 全部细胞 RED 指标 |
| GET | /api/governance/metrics?cell=crm | 单细胞 RED：request_total, success_rate, duration_ms_avg, duration_ms_p50, duration_ms_p99 |

### 2.5 健康

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/governance/health | 治理中心自身健康 |
| GET | /api/governance/health/cells | 各细胞健康状态摘要 |

---

## 3. 配置

### 3.1 环境变量

| 变量 | 说明 | 默认 |
|------|------|------|
| GOVERNANCE_PORT | 治理中心监听端口 | 8005 |
| GOVERNANCE_HEALTH_INTERVAL_SEC | 健康巡检间隔（秒） | 30 |
| GOVERNANCE_HEALTH_FAILURE_THRESHOLD | 连续失败次数后标记不健康 | 3 |
| GOVERNANCE_HEALTH_TIMEOUT_SEC | 单次 /health 请求超时（秒） | 5 |
| CELL_*_URL | 预填注册表（与网关一致） | - |
| GOVERNANCE_URL | 网关侧：治理中心地址，设则启用发现与上报 | - |

### 3.2 网关接入治理中心

网关配置 `GOVERNANCE_URL=http://governance:8005` 后：

- **解析**：优先从治理中心 GET /api/governance/discovery/<cell> 获取 base_url（仅健康）；失败则回退到环境变量/路由文件。
- **上报**：每次代理请求结束后 POST /api/governance/ingest 上报 span 与 RED 指标。

无需修改业务细胞代码。

---

## 4. 与现有组件打通

- **网关**：`deploy/run_gateway.py` 已支持 GOVERNANCE_URL，解析与 monitor_emit 自动对接治理中心。
- **docker-compose**：已增加 `governance` 服务，网关 `depends_on: governance` 并注入 GOVERNANCE_URL。
- **自检**：`scripts/self_check.py`（或 `./run.sh self_check`）可将治理中心健康与指标纳入报告（见项目自检说明）。

---

## 5. 与全量化体系规范对齐

- **黄金指标**：RED（Request total、Error rate、Duration）与 `超级PaaS平台全量化系统架构设计说明书` 一致。
- **链路**：trace_id、span_id 在网关与治理中心间传递，支持按 trace_id 定位请求链。
- **健康与巡检**：治理中心定时巡检细胞 /health，故障自动隔离（发现接口不返回不健康实例）。
