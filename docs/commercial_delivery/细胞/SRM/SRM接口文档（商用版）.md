# SRM 接口文档（商用版）

**版本**：1.0 | **细胞**：SRM

## 访问与接口

- 经网关：`/api/v1/srm/<path>`。主要接口：供应商、采购订单、RFQ、报价、评估、招投标项目。
- **商用级新增**：GET /audit-logs（操作审计）；POST /suppliers/import（供应商批量导入，body.items）；GET /export/purchase-orders?format=csv（采购订单导出）。
- 规范与错误体见《接口设计说明书》；敏感字段（如 contact）返回脱敏。

**详细**：见 `cells/srm/docs/SRM接口文档.md`。
