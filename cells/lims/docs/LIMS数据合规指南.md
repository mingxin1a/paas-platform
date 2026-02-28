# LIMS 数据合规指南

**版本**：1.0 | **细胞**：LIMS

## 1. 实验室管理规范适配

- **数据留存**：实验数据保留不少于 5 年，由配置项 labDataRetentionDays（默认 1825）保障（模拟）；持久化后由备份与归档策略实现。
- **数据溯源**：样品→任务→实验数据→报告全链路可追溯；创建/接收/审核/归档等操作写入 trace，GET /trace 可查询审计记录。
- **全流程闭环**：样品接收→实验任务分配→实验数据录入→报告生成→审核→归档，均通过 PaaS 标准化接口，无跨细胞代码耦合。

## 2. 数据安全

- 实验数据加密存储（应用层/KMS）；多租户隔离（X-Tenant-Id）。
- 实验人员权限：列表接口支持按 X-User-Id（operatorId）过滤，仅看本人负责样品/任务。

## 3. 接口说明

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /config/retention | 数据留存天数（≥5年） |
| GET/POST | /samples | 样品列表、创建；POST /samples/:id/receive 样品接收 |
| GET/POST | /tasks | 实验任务列表、创建 |
| GET/POST | /experiment-data | 实验数据列表、录入 |
| GET/POST | /reports | 报告列表、创建；POST /reports/:id/review 审核；POST /reports/:id/archive 归档 |
| GET | /trace | 按 entityType、entityId 查询溯源记录 |
