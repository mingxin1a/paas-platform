# PLM 文档管理规范

**版本**：1.0 | **细胞**：PLM

## 1. 文档类型

- drawing：产品图纸。
- process_file：工艺文件。

## 2. 接口

- 列表：GET /documents?productId=xxx&docType=drawing。
- 上传：POST /documents，Body：productId、docType、version、storagePath（存储路径可加密）。
- 产品文档版本追溯：通过 version 与 change-records 关联审计。

## 3. 安全

- 产品图纸加密存储（storage_path_encrypted 或应用层加密）；访问控制与租户隔离。
