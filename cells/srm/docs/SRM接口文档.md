# SRM 接口文档

**版本**：1.0（商用版） | **遵循**：《接口设计说明书》

## 1. 通用约定

- **BaseURL**：经 PaaS 网关为 `/api/v1/srm`；细胞直连为 `http://<host>:8008`。
- **请求头**：`Content-Type: application/json`、`X-Tenant-Id`、`X-Request-ID`（POST 必填，幂等）。
- **错误体**：`{"code":"ERROR_CODE","message":"描述","details":"详情","requestId":"请求ID"}`。

## 2. 供应商

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /suppliers | 列表 |
| GET | /suppliers/<supplier_id> | 详情 |
| POST | /suppliers | 创建，幂等；Body：name, code?, contact? |

## 3. 采购订单

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /purchase-orders | 列表 |
| GET | /purchase-orders/<order_id> | 详情 |
| POST | /purchase-orders | 创建，幂等 |
| PATCH | /purchase-orders/<order_id> | 更新状态，Body：status |

## 4. 询价单（RFQ）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /rfqs | 列表，分页 page、pageSize |
| POST | /rfqs | 创建，幂等；Body：demandId? |

## 5. 报价（Quote）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /quotes | 列表，可选 rfqId，分页 |
| POST | /quotes | 提交报价，幂等；Body：rfqId, supplierId, amountCents, currency?, validUntil?；询价单不存在时返回业务错误 |

## 6. 供应商评估

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /evaluations | 列表，可选 supplierId，分页 |
| POST | /evaluations | 创建评估，幂等；Body：supplierId, score, dimension?, comment?；供应商不存在时返回业务错误 |

## 7. 健康检查

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /health | 返回 {"status":"up","cell":"srm"} |

## 8. 错误码

- **NOT_FOUND**：资源不存在。
- **BAD_REQUEST**：参数缺失或格式错误。
- **IDEMPOTENT_CONFLICT**：幂等冲突。
- **BUSINESS_RULE_VIOLATION**：业务规则校验失败（如询价单不存在、供应商未准入）。
