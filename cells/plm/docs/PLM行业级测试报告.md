# PLM 行业级测试报告

**版本**：1.0 | **细胞**：PLM | **测试类型**：合规 / 功能 / 安全

## 1. 合规测试

| 用例 | 说明 | 预期 |
|------|------|------|
| 文档版本追溯 | 产品文档带 version，变更记录 entityType/entityId 可查 | 通过 |
| 变更记录可审计 | POST /change-records 后 GET /change-records?entityId=xxx 可查 | 通过 |
| 研发数据管理 | 产品/BOM 与 ownerId 关联，列表支持按负责人过滤 | 通过 |

## 2. 功能测试

| 用例 | 说明 | 预期 |
|------|------|------|
| BOM 版本查询 | GET /boms?productId=xxx&version=1 返回对应版本 | 通过 |
| 变更记录查询 | GET /change-records?entityType=product&entityId=xxx 分页 | 通过 |
| 文档管理 | POST/GET /documents，docType=drawing\|process_file | 通过 |
| 批量导入产品 | POST /products/import，items≤500，幂等 | 通过 |

## 3. 安全测试

| 用例 | 说明 | 预期 |
|------|------|------|
| 设计数据权限 | X-User-Id 下 GET /products 仅返回本人负责产品 | 通过 |
| 租户隔离 | 不同 X-Tenant-Id 数据不可见 | 通过 |
| 产品创建幂等 | X-Request-ID 重复返回 409 | 通过 |
