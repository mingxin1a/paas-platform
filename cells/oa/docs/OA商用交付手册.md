# OA 商用交付手册

**版本**：1.0（商用可交付） | **细胞**：办公自动化（OA）

## 1. 交付范围

本手册适用于 OA 细胞按「商用可交付」标准的交付验收与运维说明。OA 与 CRM/ERP/SRM 严格解耦，独立部署，仅通过 PaaS 层标准化接口对外服务。

### 1.1 功能闭环

| 能力 | 说明 | 状态 |
|------|------|------|
| 组织架构 | 部门、用户（Schema 已定义） | Schema 就绪，接口可扩展 |
| 用户权限 | 与组织架构、审批数据权限结合 | 审批列表按 X-User-Id 过滤 |
| 审批流程 | 采购/报销/请假，草稿→提交（幂等） | 已实现 |
| 公告通知 | 公告列表、发布、分页 | 已实现 |
| 日程管理 | Schema 已定义 | 可扩展接口 |
| 文件管理 | 基础元数据 Schema | 可扩展上传与校验 |
| 数据安全 | 审批仅看本人发起/待审批 | 列表按 applicantId 过滤 |
| 可靠性 | 审批提交幂等 | 已实现 |
| 可运维 | /health；可扩展 /metrics（审批处理效率、公告阅读率） | 健康检查已实现 |

### 1.2 约束与依赖

- **解耦**：独立存储（当前内存），独立部署；仅经网关暴露接口。
- **接口**：遵循《接口设计说明书》；POST 写操作幂等（X-Request-ID）。
- **监控**：可与 PaaS 监控打通，扩展审批处理效率、公告阅读率等指标。

## 2. 部署与配置

### 2.1 环境变量

| 变量 | 说明 | 默认 |
|------|------|------|
| PORT | 服务端口 | 8005 |
| CELL_VERIFY_SIGNATURE | 是否开启网关验签 | 0 |

### 2.2 Docker 部署

```bash
cd paas-platform/cells/oa
docker build -t oa-cell:latest .
docker run -p 8005:8005 oa-cell:latest
```

### 2.3 健康检查

- `GET /health` 返回 `{"status":"up","cell":"oa"}`。

## 3. 验收要点

- 审批创建：POST /approvals，typeCode 为 purchase|reimburse|leave；带 X-Request-ID 幂等。
- 审批提交：POST /approvals/<id>/submit，同一 X-Request-ID 重复提交返回 200 及已提交单。
- 审批列表：带 X-User-Id 时仅返回当前用户发起的单（数据权限）。
- 公告列表：分页、分页参数 page、pageSize。

## 4. 交付物清单

- 本手册（OA商用交付手册.md）
- 《OA审批流程配置指南》
- 《OA用户手册》
- Dockerfile、docker-compose.yml
- database_schema.sql（含组织、审批、公告、日程、文件表）
