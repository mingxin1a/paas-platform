# LIS 行业合规指南

**版本**：1.0 | **细胞**：LIS | **适用**：检验数据规范

## 报告可追溯与样本安全

- **检验报告**：与 sampleId、requestId 关联，可回溯申请与样本；报告审核记录可查（GET /reports/<id>/audits）。
- **样本信息**：加密存储（应用层）；检验师仅能查看本人负责样本下的结果与报告。

## 与 HIS 对接

- HIS 发起检验申请：调用 LIS POST /test-requests（patientId、visitId、items）；样本创建时关联 patientId、requestId；报告生成/审核后 HIS 可拉取报告。

**详细**：见 `cells/lis/docs/LIS商用交付手册（检验版）.md`、`LIS检验报告规范.md`、`LIS与HIS对接手册.md`。
