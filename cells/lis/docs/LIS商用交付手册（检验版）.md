# LIS 商用交付手册（检验版）

**版本**：1.0 | **细胞**：检验信息系统（LIS）| **行业**：检验数据规范

## 1. 交付范围

### 1.1 核心行业功能

| 环节 | 说明 | 状态 |
|------|------|------|
| 检验申请 | POST/GET /test-requests | 已实现 |
| 样本管理 | 样本 CRUD，按检验师过滤 | 已实现 |
| 检验结果 | 结果 CRUD，按检验师/样本过滤 | 已实现 |
| 报告生成 | POST/GET /reports | 已实现 |
| 报告审核 | POST /reports/<id>/review，审核记录可审计 | 已实现 |

### 1.2 医疗合规与数据安全

- 检验报告可追溯（reportId、sampleId、requestId 关联）。
- 样本信息加密存储（应用层）；检验结果权限：检验师仅能查看本人负责样本（X-User-Id 过滤）。
- 报告修改/审核记录可审计：GET /reports/<id>/audits。

## 2. 与 HIS 对接

- HIS 可调用 LIS POST /test-requests 发起检验申请（patientId、visitId、items）；LIS 样本/结果/报告与 patientId、visitId 关联，便于 HIS 查询。

## 3. 交付文档

- 本手册
- 《LIS与HIS对接手册》
- 《LIS检验报告规范》
