# CRM 接口文档（商用版）

**版本**：2.0 | **遵循**：《接口设计说明书_V2.0》

## 1. 通用约定

- **BaseURL**：经 PaaS 网关为 `/api/v1/crm`（细胞直连为 `http://<host>:8001`）。
- **请求头**：`Content-Type: application/json`、`Authorization: Bearer <token>`、`X-Tenant-Id`、`X-Request-ID`（POST/PATCH 必填）。
- **响应头**：`X-Response-Time`（毫秒）。
- **错误体**：`{"code":"ERROR_CODE","message":"描述","details":"详情","requestId":"请求ID"}`。

## 2. 客户

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /customers | 列表，支持 page、pageSize；带 X-User-Id 时仅返回本人负责客户 |
| GET | /customers/{customer_id} | 详情（手机号脱敏） |
| POST | /customers | 创建，幂等；重复名称返回「客户名称已存在」 |
| PATCH | /customers/{customer_id} | 更新 |
| DELETE | /customers/{customer_id} | 删除 |
| POST | /customers/import | 批量导入，body.items 数组，单次≤2000 |
| GET | /customers/export | 导出分页，page、pageSize（最大 1000） |

## 3. 联系人

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /contacts | 列表，可选 customerId |
| GET | /contacts/{contact_id} | 详情（手机号脱敏） |
| POST | /contacts | 创建，幂等 |
| PATCH | /contacts/{contact_id} | 更新 |
| DELETE | /contacts/{contact_id} | 删除 |

## 4. 商机

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /opportunities | 列表，可选 customerId |
| GET | /opportunities/{opportunity_id} | 详情 |
| POST | /opportunities | 创建，幂等 |
| PATCH | /opportunities/{opportunity_id} | 更新 |
| DELETE | /opportunities/{opportunity_id} | 删除 |

## 5. 跟进记录

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /follow-ups | 列表，可选 customerId、opportunityId |
| GET | /follow-ups/{follow_up_id} | 详情 |
| POST | /follow-ups | 创建，幂等，支持重试 |
| PATCH | /follow-ups/{follow_up_id} | 更新 |
| DELETE | /follow-ups/{follow_up_id} | 删除 |

## 6. 合同

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /contracts | 列表，可选 customerId |
| GET | /contracts/{contract_id} | 详情 |
| POST | /contracts | 创建，幂等；重复 contractNo 返回「合同编号已存在」 |

## 7. 回款

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /payments | 列表，可选 contractId |
| POST | /payments | 登记回款，幂等；contractId 必填 |

## 8. 报表与监控

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /reports/funnel | 销售漏斗（按阶段/状态汇总） |
| GET | /metrics | CRM 监控指标（客户总量、商机总量、转化率、漏斗明细） |
| GET | /health | 健康检查 |

## 9. 商用版 OpenAPI

完整 Schema 见 `api_contract.yaml`；Swagger 商用版可通过 `/docs`、`/redoc` 查看（细胞直连时）。
