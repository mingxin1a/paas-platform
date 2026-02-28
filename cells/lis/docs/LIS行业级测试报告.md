# LIS 行业级测试报告

**版本**：1.0 | **细胞**：LIS | **测试类型**：合规 / 功能 / 安全

## 1. 合规测试

| 用例 | 说明 | 预期 |
|------|------|------|
| 检验报告可追溯 | 报告与 sampleId、requestId 关联，可回溯申请与样本 | 通过 |
| 样本信息加密 | 样本敏感信息加密存储（应用层） | 通过 |
| 报告修改可审计 | POST /reports/<id>/review 后 GET /reports/<id>/audits 有记录 | 通过 |
| 检验数据规范 | 结果项 itemCode、value、unit 完整 | 通过 |

## 2. 功能测试

| 用例 | 说明 | 预期 |
|------|------|------|
| 检验申请 | POST/GET /test-requests，与 patientId、visitId 关联 | 通过 |
| 样本管理 | 样本 CRUD，technicianId 关联 | 通过 |
| 检验结果 | 结果 CRUD，按 sampleId/technicianId 过滤 | 通过 |
| 报告生成与审核 | POST /reports 生成，POST /reports/<id>/review 审核 | 通过 |
| 检验师权限 | X-User-Id 下样本/结果列表仅本人负责 | 通过 |

## 3. 安全测试

| 用例 | 说明 | 预期 |
|------|------|------|
| 结果权限 | 检验师仅看本人负责样本下的结果 | 通过 |
| 租户隔离 | 多租户数据隔离 | 通过 |
| 创建幂等 | 样本/结果/报告创建支持 X-Request-ID | 通过 |
