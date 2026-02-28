# ERP 接口文档（商用版）

**版本**：1.0 | **细胞**：ERP | **对象**：对接开发

## 访问与规范

- 经网关：`/api/v1/erp/<path>`；请求头：Content-Type、Authorization、X-Tenant-Id、X-Request-ID（POST/PUT）。
- 错误体：`{"code","message","requestId"}`；金额单位：分。

## 主要接口（节选）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /health | 健康 |
| GET/POST | /orders | 订单 |
| GET/POST | /gl/accounts | 科目 |
| GET/POST | /gl/journal-entries | 凭证 |
| GET/POST | /ar/invoices | 应收发票 |
| GET/POST | /ap/invoices | 应付发票 |
| GET/POST | /mm/materials | 物料 |
| GET/POST | /mm/purchase-orders | 采购订单 |
| GET/POST | /pp/boms | BOM |
| GET/POST | /pp/work-orders | 工单 |
| GET | /audit-logs | 操作审计日志（分页、resourceType 筛选） |
| POST | /orders/import | 订单批量导入（body.items） |
| GET | /export/orders?format=csv | 销售订单导出 |
| GET | /export/ar/invoices?format=csv | 应收发票导出 |
| GET | /export/ap/invoices?format=csv | 应付发票导出 |
| GET | /export/mm/materials?format=csv | 物料导出 |

**完整列表与示例**：见 `cells/erp` 源码及《接口设计说明书》；Swagger 若细胞提供则经网关 `/api/admin/cells/erp/docs` 访问。
