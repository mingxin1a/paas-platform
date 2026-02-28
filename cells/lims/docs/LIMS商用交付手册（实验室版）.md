# LIMS 商用交付手册（实验室版）

**版本**：1.0 | **细胞**：实验室信息管理系统（LIMS）| **行业**：实验室管理规范

## 1. 交付范围

### 1.1 核心行业功能

| 环节 | 说明 | 状态 |
|------|------|------|
| 样品管理 | 样品 CRUD，按操作员过滤 | 已实现 |
| 实验任务 | POST/GET /tasks，与样品关联 | 已实现 |
| 实验数据 | POST/GET /experiment-data，与任务/样品关联 | 已实现 |
| 实验报告 | POST/GET /reports | 已实现 |
| 数据溯源 | GET /trace?entityType=&entityId=，可审计 | 已实现 |

### 1.2 行业合规与数据安全

- 实验数据留存≥5年：LIMS_LAB_DATA_RETENTION_DAYS（默认 1825），GET /config/retention。
- 数据溯源可审计：任务/实验数据/报告创建时写入 trace，GET /trace 查询。
- 实验数据加密存储（应用层）；实验人员权限分级（X-User-Id 过滤样品/任务列表）。

## 2. 交付文档

- 本手册
- 《LIMS数据合规指南》
- 《LIMS实验管理操作指南》
