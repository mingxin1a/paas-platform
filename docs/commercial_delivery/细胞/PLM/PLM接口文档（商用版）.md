# PLM 接口文档（商用版）

**版本**：1.0 | **细胞**：PLM

## 访问与主要接口

- 经网关：`/api/v1/plm/<path>`。路径：/products、/boms、/change-records、/documents、/products/import 等。
- 产品列表支持 ownerId/X-User-Id 过滤；BOM 支持 productId、version 查询。

**详细**：见 cells/plm 源码及《PLM BOM管理指南》《PLM文档管理规范》。
