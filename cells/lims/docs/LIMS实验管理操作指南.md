# LIMS 实验管理操作指南

**版本**：1.0 | **细胞**：LIMS

## 1. 样品与任务

- 创建样品：POST /samples，Body：sampleNo、batchId、testType、operatorId（可选）；请求头 X-User-Id 可自动带操作员。
- 查询样品：GET /samples，支持 operatorId 过滤（仅看本人负责）。
- 创建实验任务：POST /tasks，Body：sampleId、taskType、operatorId；创建时写入溯源记录。
- 查询任务：GET /tasks?sampleId=xxx&operatorId=xxx。

## 2. 实验数据与报告

- 记录实验数据：POST /experiment-data，Body：taskId、sampleId、dataValue；写入溯源。
- 查询实验数据：GET /experiment-data?taskId=xxx&sampleId=xxx。
- 创建实验报告：POST /reports，Body：sampleId、taskId、content。
- 查询报告：GET /reports?sampleId=xxx。

## 3. 数据溯源

- GET /trace?entityType=task|experiment_data|report&entityId=xxx，查看某实体的操作审计记录，符合实验室管理规范。
