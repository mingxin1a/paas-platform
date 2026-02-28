# ERP 管理员手册

**版本**：1.0 | **细胞**：企业资源计划（ERP）

## 1. 概述

ERP 细胞提供总账（GL）、应收（AR）、应付（AP）、物料（MM）、采购订单、生产（BOM/工单）及销售订单等能力，通过 PaaS 网关暴露。管理员需配置租户、网关路由、可选验签与审计。

## 2. 接口与路由

- **BaseURL**：经网关为 `/api/v1/erp`；细胞直连为 `http://<host>:8002`。
- **健康检查**：`GET /health`，用于网关注册与巡检。
- **主要路径**：
  - 订单：`/orders`（GET/POST），`/orders/<id>`（GET/DELETE 软删除）
  - 总账：`/gl/accounts`、`/gl/entries`、`/gl/balance`、`/gl/post`
  - 应收：`/ar/invoices`、`/ar/invoices/<id>`
  - 应付：`/ap/invoices`、`/ap/invoices/<id>`
  - 物料：`/mm/materials`、`/mm/materials/<id>`
  - 采购订单：`/mm/purchase-orders`、`/mm/purchase-orders/<id>`
  - 生产：`/pp/boms`、`/pp/work-orders`

## 3. 配置项

| 配置/环境变量 | 说明 |
|---------------|------|
| PORT | 服务端口，默认 8002 |
| CELL_VERIFY_SIGNATURE | 设为 1 时开启网关验签，需与 PaaS 密钥一致 |
| X-Tenant-Id | 请求头，租户隔离，必填 |
| X-Request-ID | 请求头，POST 必填，用于幂等 |

## 4. 安全与审计

- 所有写操作记录人性化审计（租户、用户、时间、操作描述、trace_id）。
- 可选：审计落库（当前实现见 store 的 audit_append）；生产环境建议接入统一日志/审计中心。
- 财务数据：生产环境建议加密存储；密钥由 KMS 管理。

## 5. 监控与备份

- **监控**：/health 可用；商用级可增加 /metrics（采购订单量、库存周转率、应收账龄等），与 PaaS 监控对接。
- **备份**：持久化存储启用后，需配置每日全量备份与实时增量（如 MySQL binlog），由运维脚本执行。

## 6. 故障与运维

- 细胞无状态，重启后内存数据丢失；启用持久化后需保证数据库高可用。
- 网关超时、断路器：遵循 PaaS 流量治理规范；ERP 细胞建议响应时间 &lt; 2s。
