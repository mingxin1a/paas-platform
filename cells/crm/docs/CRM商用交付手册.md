# CRM 商用交付手册

**版本**：1.0（商用可交付） | **细胞**：客户关系管理（CRM）

## 1. 交付范围

本手册适用于 CRM 细胞按「商用可交付」标准的交付验收与运维说明。

### 1.1 功能清单

| 能力 | 说明 | 状态 |
|------|------|------|
| 客户生命周期管理 | 客户创建/编辑/状态、负责人关联 | 已实现 |
| 销售漏斗 | 商机按阶段/状态汇总，/reports/funnel、/metrics | 已实现 |
| 商机跟进 | 商机 CRUD、跟进记录（follow-ups） | 已实现 |
| 合同管理 | 合同 CRUD、合同编号唯一、幂等创建 | 已实现 |
| 回款管理 | 回款记录登记、按合同查询、幂等创建 | 已实现 |
| 客户画像（基础） | 客户+联系人+商机+合同+回款关联展示 | 通过接口组合实现 |
| 数据安全 | 手机号/合同金额脱敏、客户负责人数据权限 | 已实现 |
| 性能 | 客户/商机列表索引、批量导入/导出（1000+） | 已实现 |
| 可靠性 | 合同/回款幂等、跟进记录可重试、商用化错误提示 | 已实现 |
| 可运维 | /metrics、/health、健康检查脚本 | 已实现 |

### 1.2 约束与依赖

- **解耦**：CRM 独立数据库（SQLite/MySQL 可选），独立部署，仅通过 PaaS 网关调用标准化接口。
- **接口规范**：遵循《接口设计说明书》，请求头 X-Tenant-Id、X-Request-ID、Authorization；错误格式 code/message/details/requestId。
- **监控**：/metrics 提供 customer_total、opportunity_total、conversion_rate_pct、funnel_by_stage，可与 PaaS 监控打通。

## 2. 部署与配置

### 2.1 环境变量

| 变量 | 说明 | 默认 |
|------|------|------|
| CRM_DATABASE_URL | 数据库连接（如 sqlite:///./data/crm.db） | sqlite:///./crm_cell.db |
| PORT | 服务端口 | 8001 |
| DEFAULT_TENANT_ID | 默认租户 | default |
| PLATFORM_AUTH_URL | 平台鉴权地址（可选） | - |
| CRM_AUTH_STRICT | 是否严格鉴权 | 0 |

### 2.2 Docker 部署

```bash
cd paas-platform/cells/crm
docker build -t crm-cell:latest .
docker run -p 8001:8001 -e CRM_DATABASE_URL=sqlite:///./data/crm.db -v $(pwd)/data:/app/data crm-cell:latest
```

### 2.3 健康检查

- **HTTP**：`GET /health` 返回 `{"status":"up","cell":"crm"}`。
- **脚本**：执行 `scripts/health_check_crm.sh`，需设置 `CRM_BASE_URL`（默认 http://localhost:8001）。

## 3. 数据安全与权限

- **敏感信息**：客户/联系人手机号在接口响应中脱敏展示（如 138****5678）；合同金额可按策略脱敏。
- **数据权限**：请求头携带 `X-User-Id` 时，客户列表仅返回该负责人名下的客户（customer_owner 表）。
- **存储**：生产环境建议对 contact_phone、合同金额等字段加密存储，密钥由 KMS 管理；当前版本为脱敏展示，存储可后续升级加密。

## 4. 验收要点

- 客户创建重复名称返回「客户名称已存在」而非数据库错误。
- 合同创建重复编号返回「合同编号已存在」。
- 合同/回款 POST 带相同 X-Request-ID 返回 409 或原资源。
- /metrics 返回 JSON 含 customer_total、conversion_rate_pct 等。
- 批量导入 POST /customers/import 支持 1000+ 条；导出 GET /customers/export 支持 pageSize=1000 分页。

## 5. 交付物清单

- 本手册（CRM商用交付手册.md）
- 《CRM用户手册》
- 《CRM接口文档（商用版）》
- 健康检查脚本：scripts/health_check_crm.sh
- Dockerfile、docker-compose.yml
- api_contract.yaml（OpenAPI 3.0）
