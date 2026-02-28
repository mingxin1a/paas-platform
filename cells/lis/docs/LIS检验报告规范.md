# LIS 检验报告规范

**版本**：1.0 | **细胞**：LIS

## 1. 报告状态

- 0：草稿（未审核）
- 1：已审核
- 2：已发布

## 2. 全流程闭环（检验申请→样本接收→结果录入→报告生成→审核→发布）

- 检验申请：POST /test-requests。
- 样本接收：POST /samples 创建样本，POST /samples/<sampleId>/receive 接收样本（记录 receivedAt）。
- 检验结果录入：POST /results。
- 报告生成：POST /reports。
- 报告审核：POST /reports/<reportId>/review。
- 报告发布：POST /reports/<reportId>/publish（需先审核）。
- 操作审计：GET /audit-logs，不可篡改操作日志，符合医疗检验规范。

## 3. 样本与结果

- 样本状态：0=待接收 1=已接收；带 technicianId，检验师仅能查看本人负责样本下的结果与报告。
- 结果项：sampleId、itemCode、value、unit。
