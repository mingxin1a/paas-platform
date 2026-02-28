# PLM BOM 管理指南

**版本**：1.0 | **细胞**：PLM

## 1. BOM 版本

- 创建 BOM：POST /boms，Body：productId、parentId、quantity、version（默认 1）。
- 查询：GET /boms?productId=xxx&version=1（按产品、版本查询，索引支持）。
- 详情：GET /boms/<bom_id>。

## 2. 与 MES 对接

- PLM 下发 BOM 版本至 MES：MES 调用 PLM GET /boms 或网关转发；PLM 与 MES 解耦，仅通过 PaaS 交互。

## 3. 变更与追溯

- 产品/BOM 变更时记录：POST /change-records，entityType=product|bom，entityId=xxx，变更描述可审计。
