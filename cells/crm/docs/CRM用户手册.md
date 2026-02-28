# CRM 用户手册

**版本**：2.0（商用版） | **细胞**：客户关系管理（CRM）

## 1. 概述

CRM 细胞提供客户、联系人、商机、跟进记录、合同、回款及销售漏斗等能力，通过 PaaS 网关暴露，与《接口设计说明书》一致。所有写操作需提供 **X-Tenant-Id**、**X-Request-ID**（POST 幂等）及 **Authorization**。

## 2. 功能入口

| 能力 | 方法 | 路径 |
|------|------|------|
| 健康检查 | GET | /health |
| 客户 | GET/POST/PATCH/DELETE | /customers, /customers/{id} |
| 客户批量导入 | POST | /customers/import |
| 客户导出 | GET | /customers/export?page=1&pageSize=1000 |
| 联系人 | GET/POST/PATCH/DELETE | /contacts, /contacts/{id} |
| 商机 | GET/POST/PATCH/DELETE | /opportunities, /opportunities/{id} |
| 跟进记录 | GET/POST/PATCH/DELETE | /follow-ups, /follow-ups/{id} |
| 合同 | GET/POST | /contracts, /contracts/{id} |
| 回款 | GET/POST | /payments |
| 销售漏斗报表 | GET | /reports/funnel |
| 监控指标 | GET | /metrics |

## 3. 典型流程

### 3.1 客户与负责人

- 创建客户时若请求头带 **X-User-Id**，系统会将该客户绑定为当前用户负责（数据权限：销售只能看自己的客户）。
- 客户列表：若带 X-User-Id，仅返回当前用户负责的客户；否则返回租户下全部客户（管理员视角）。

### 3.2 商机与跟进

- 创建商机需填写 customerId、title、amountCents、stage。
- 跟进记录可关联 customerId 或 opportunityId，提交时建议带 X-Request-ID 以便重试不重复落库。

### 3.3 合同与回款

- 合同需关联 customerId、contractNo（唯一）、amountCents；可选 opportunityId、signedAt。
- 回款需关联 contractId、amountCents、paymentAt；同一 X-Request-ID 重复提交返回已创建记录（幂等）。

### 3.4 批量导入与导出

- **导入**：POST /customers/import，body 为 `{"items":[{"name":"公司A","contactPhone":"13800138000","contactEmail":"a@example.com"},...]}`，单次建议不超过 2000 条。
- **导出**：GET /customers/export?page=1&pageSize=1000，多次请求可拼成完整导出；返回数据中手机号已脱敏。

## 4. 错误提示说明（商用化）

- **客户名称已存在**：创建客户时名称与现有客户重复，请修改名称或先查询。
- **合同编号已存在**：创建合同时编号重复，请更换合同编号。
- **幂等冲突**：同一 X-Request-ID 已创建过资源，无需重复提交。
- **客户不存在 / 合同不存在**：操作对象不存在或无权访问。

## 5. 敏感数据与脱敏

- 客户、联系人的手机号在接口响应中统一脱敏（如 138****5678）。
- 合同金额可按租户策略配置脱敏展示；存储侧建议加密（生产环境）。

## 6. 约束与合规

- 金额单位：**分**（Long）。
- 跨细胞：仅通过网关调用，禁止直连 CRM 数据库。
