# PLM 商用交付手册（研发版）

**版本**：1.0 | **细胞**：产品生命周期管理（PLM）| **行业**：研发数据管理规范

## 1. 交付范围

- 产品设计：产品 CRUD、按负责人过滤（研发工程师只能看自己负责的产品）。
- BOM 版本管理：BOM 创建带 version，按 productId/version 查询。
- 工艺管理：工艺定义（Schema 支持），可扩展接口。
- 变更管理：变更记录 POST/GET，entityType/entityId 可审计。
- 文档管理：产品图纸/工艺文件（drawing|process_file），版本追溯。
- 批量导入：POST /products/import，items≤500。
- 交付文档：本手册、《PLM BOM管理指南》、《PLM文档管理规范》。

## 2. 数据安全与合规

- 产品图纸加密存储（应用层）；设计数据权限（X-User-Id 过滤产品列表）。
- 变更记录可审计；文档版本追溯。

## 3. 配置与部署

- PORT 默认 8009；CELL_VERIFY_SIGNATURE 可选。
