# PLM 行业合规指南

**版本**：1.0 | **细胞**：PLM | **适用**：研发数据管理规范

## 文档版本与变更追溯

- **产品文档**：图纸、工艺文件带 version；变更时记录 change_record（entityType/entityId），可审计。
- **研发数据权限**：产品与负责人（ownerId）关联；列表按 X-User-Id 过滤，研发工程师仅看本人负责产品。

## 配置与接口

- BOM 按 productId、version 查询；变更记录按 entityType、entityId 查询。
- 文档类型：drawing（产品图纸）、process_file（工艺文件）；存储路径可加密。

**详细**：见 `cells/plm/docs/PLM商用交付手册（研发版）.md`、`PLM BOM管理指南.md`、`PLM文档管理规范.md`。
