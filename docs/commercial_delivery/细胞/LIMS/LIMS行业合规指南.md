# LIMS 行业合规指南

**版本**：1.0 | **细胞**：LIMS | **适用**：实验室管理规范

## 数据留存与溯源

- **数据留存**：实验数据保留不少于 5 年，由配置项 labDataRetentionDays（默认 1825）保障；持久化后由备份与归档落实。
- **数据溯源**：样品→任务→实验数据→报告全链路可追溯；创建/修改等操作写入 data_trace，GET /trace?entityType=task&entityId=xxx 可查审计记录。

## 数据安全

- 实验数据加密存储（应用层/KMS）；多租户隔离（X-Tenant-Id）。
- 实验人员权限：列表按 X-User-Id（operatorId）过滤，仅看本人负责样品/任务。

**详细**：见 `cells/lims/docs/LIMS数据合规指南.md`、`LIMS实验管理操作指南.md`。
