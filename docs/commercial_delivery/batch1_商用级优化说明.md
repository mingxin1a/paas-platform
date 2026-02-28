# 批次1 核心细胞（CRM/ERP/OA/SRM）商用级优化说明

本文档说明对 CRM、ERP、OA、SRM 四个核心细胞实施的商用级精细化优化，严格遵循细胞化架构，**不修改 PaaS 层代码**，**不与其他 Cell 产生代码耦合**。

---

## 一、功能闭环与高级功能

### CRM
- **审计**：`audit_log` 表 + `GET /audit-logs`（分页、按 resourceType 筛选）；客户/商机创建、更新、删除自动落审计。
- **高级查询**：客户列表支持 `keyword` 参数（名称/电话/邮箱模糊查询）；行级权限下同样支持 keyword。
- **批量**：`POST /customers/import`、`GET /customers/export?format=csv`（已有）；新增 `POST /opportunities/import`、`GET /opportunities/export?format=csv`。
- **索引**：`idx_opportunities_stage_status` 用于漏斗/报表查询；审计表 `idx_audit_tenant_time`、`idx_audit_trace`。

### ERP
- **审计**：内存审计列表 + `GET /audit-logs`（分页、resourceType 筛选）。
- **批量**：`POST /orders/import`（body.items：customerId、totalAmountCents、currency）；单次建议 ≤2000 条。
- **导出**：`GET /export/orders?format=csv`（已有）；新增 `GET /export/ar/invoices?format=csv`、`GET /export/ap/invoices?format=csv`、`GET /export/mm/materials?format=csv`。

### OA
- **审计**：内存审计 + `GET /audit-logs`；任务创建/更新、公告创建落审计。
- **批量**：`POST /tasks/batch-complete`（body.taskIds 数组，单次最多 200 条）。
- **提醒**：`GET /reminders`（未完成任务 + 待审批数量；可选 assigneeId 或 X-User-Id 仅查本人）。
- **公告**：`GET /announcements/<announcement_id>` 公告详情。

### SRM
- **审计**：内存审计 + `GET /audit-logs`；供应商创建落审计。
- **批量**：`POST /suppliers/import`（body.items：name、code?、contact?）；单次建议 ≤2000 条。
- **敏感数据**：供应商 contact 脱敏（已有）；错误提示商用友好化。

---

## 二、体验与异常话术

- **统一错误体**：所有接口保持 `code`、`message`、`details`、`requestId`；`details` 使用商用友好说明（如“请检查客户编号或刷新列表后重试”、“该客户可能已被删除，请刷新列表”）。
- **分页上限**：列表/导出 pageSize 有上限（如 CRM 客户 500、导出 5000；OA 批量办结 200），避免单次过大请求影响性能。

---

## 三、性能与 10 万级数据

- **CRM**：使用 SQLite + 索引（customers、opportunities、follow_ups、contracts、audit_log 等）；列表分页 + keyword 使用 LIKE 与索引组合；单次导入/导出建议 ≤2000/5000 条。
- **ERP/OA/SRM**：当前为内存存储；列表均为分页，导出限制 pageSize；若需 10 万级持久化，可替换为 DB 并在对应表建索引（tenant_id、created_at、resource_type 等），**仅在细胞内部扩展**，不依赖 PaaS。

---

## 四、安全与审计

- **操作审计**：四细胞均支持审计日志写入与 `GET /audit-logs` 查询，便于追溯“谁在何时对何资源做了何操作”。
- **敏感数据**：CRM 客户脱敏、SRM 供应商 contact 脱敏（已有）；审计日志不记录敏感内容。
- **数据权限**：CRM 行级（X-Data-Scope=self + X-User-Id）；OA 审批/任务按申请人/负责人；ERP/SRM 按 tenant_id 隔离。

---

## 五、测试与文档

- **单元测试**：各细胞现有单元测试通过；新增接口已纳入回归（audit-logs、batch-complete、reminders、import/export）。
- **文档**：各细胞商用交付手册、用户操作手册、接口文档需同步更新以下内容：
  - **CRM**：`/audit-logs`、`/customers?keyword=`、`/opportunities/import`、`/opportunities/export`。
  - **ERP**：`/audit-logs`、`/orders/import`、`/export/ar/invoices`、`/export/ap/invoices`、`/export/mm/materials`。
  - **OA**：`/audit-logs`、`/tasks/batch-complete`、`/reminders`、`/announcements/<id>`。
  - **SRM**：`/audit-logs`、`/suppliers/import`。

---

## 六、接口速查（新增/变更）

| 细胞 | 方法 | 路径 | 说明 |
|------|------|------|------|
| CRM | GET | /audit-logs | 审计日志分页，query: page, pageSize, resourceType |
| CRM | GET | /customers?keyword= | 客户列表高级查询 |
| CRM | POST | /opportunities/import | 商机批量导入 |
| CRM | GET | /opportunities/export?format=csv | 商机导出 CSV |
| ERP | GET | /audit-logs | 审计日志分页 |
| ERP | POST | /orders/import | 订单批量导入 |
| ERP | GET | /export/ar/invoices?format=csv | 应收发票导出 |
| ERP | GET | /export/ap/invoices?format=csv | 应付发票导出 |
| ERP | GET | /export/mm/materials?format=csv | 物料导出 |
| OA | GET | /audit-logs | 审计日志分页 |
| OA | POST | /tasks/batch-complete | 任务批量办结 |
| OA | GET | /reminders | 待办与待审批数量 |
| OA | GET | /announcements/<id> | 公告详情 |
| SRM | GET | /audit-logs | 审计日志分页 |
| SRM | POST | /suppliers/import | 供应商批量导入 |

所有接口均需 `X-Tenant-Id`；写操作建议带 `X-Request-ID`、`X-User-Id`（审计记录用）。
