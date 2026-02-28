# ERP 用户操作指南

**版本**：1.0 | **细胞**：企业资源计划（ERP）

## 1. 通用约定

- 所有请求需带请求头：**X-Tenant-Id**、**Authorization**；POST 写操作需带 **X-Request-ID**（幂等）。
- 金额单位统一为 **分**（Long）。
- 错误时响应体为：`{"code":"ERROR_CODE","message":"描述","details":"详情","requestId":"请求ID"}`。

## 2. 销售订单

- **列表**：`GET /orders?page=1&pageSize=20`
- **详情**：`GET /orders/<order_id>`
- **创建**：`POST /orders`，Body：`{"customerId":"","totalAmountCents":10000,"currency":"CNY"}`，头带 X-Request-ID。
- **删除**：`DELETE /orders/<order_id>`（软删除）。

## 3. 总账（GL）

- **科目列表**：`GET /gl/accounts?page=1&pageSize=20`
- **新增科目**：`POST /gl/accounts`，Body：`{"accountCode":"1001","name":"库存现金","accountType":1}`。
- **分录列表**：`GET /gl/entries?page=1&pageSize=20`
- **新增分录**：`POST /gl/entries`，Body：含 documentNo、postingDate、lines（accountCode、debitCents、creditCents）。
- **余额**：`GET /gl/balance?accountCode=1001&asOfDate=2024-01-15`
- **过账**：`POST /gl/post`，Body：`{"entryId":""}`。

## 4. 应收（AR）

- **发票列表**：`GET /ar/invoices?page=1&pageSize=20`
- **发票详情**：`GET /ar/invoices/<invoice_id>`
- **创建发票**：`POST /ar/invoices`，Body：`{"customerId":"","documentNo":"AR001","amountCents":10000,"currency":"CNY","dueDate":"2024-02-01"}`。

## 5. 应付（AP）

- **发票列表**：`GET /ap/invoices?page=1&pageSize=20`
- **创建发票**：`POST /ap/invoices`，Body：`{"supplierId":"","documentNo":"AP001","amountCents":5000,"currency":"CNY","dueDate":"2024-02-01"}`。

## 6. 物料（MM）

- **物料列表**：`GET /mm/materials?page=1&pageSize=20`
- **创建物料**：`POST /mm/materials`，Body：`{"materialCode":"M001","name":"原料A","unit":"KG"}`。

## 7. 采购订单（MM）

- **列表**：`GET /mm/purchase-orders?page=1&pageSize=20`
- **创建**：`POST /mm/purchase-orders`，Body：`{"supplierId":"","documentNo":"PO001","totalAmountCents":8000}`。

## 8. 生产（PP）

- **BOM 列表/创建**：`GET /pp/boms`、`POST /pp/boms`（productMaterialId、version）。
- **工单列表/创建**：`GET /pp/work-orders`、`POST /pp/work-orders`（bomId、productMaterialId、plannedQuantity）。

## 9. 常见错误

- **NOT_FOUND**：资源不存在或已软删除。
- **IDEMPOTENT_CONFLICT**：同一 X-Request-ID 已创建过资源，无需重复提交。
- **VALIDATION_ERROR**：必填参数缺失或格式错误，见 details。
