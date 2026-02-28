# LIMS 行业级测试报告

**版本**：1.0 | **细胞**：LIMS | **测试类型**：合规 / 功能 / 安全

## 1. 合规测试

| 用例 | 说明 | 预期 |
|------|------|------|
| 实验数据留存≥5年 | GET /config/retention 返回 labDataRetentionDays=1825 | 通过 |
| 数据溯源可审计 | 任务/实验数据/报告创建写入 trace，GET /trace 可查 | 通过 |
| 实验室管理规范 | 样品→任务→数据→报告链路完整，可追溯 | 通过 |

## 2. 功能测试

| 用例 | 说明 | 预期 |
|------|------|------|
| 样品与任务 | 样品 CRUD；任务与样品关联，按 operatorId 过滤 | 通过 |
| 实验数据 | POST/GET /experiment-data，与 taskId、sampleId 关联 | 通过 |
| 实验报告 | POST/GET /reports，与 sampleId、taskId 关联 | 通过 |
| 溯源查询 | GET /trace?entityType=task&entityId=xxx 返回该实体操作记录 | 通过 |
| 操作员权限 | X-User-Id 下样品/任务列表仅本人 | 通过 |

## 3. 安全测试

| 用例 | 说明 | 预期 |
|------|------|------|
| 实验人员权限分级 | 列表按 operatorId 过滤 | 通过 |
| 租户隔离 | 多租户数据隔离 | 通过 |
| 实验数据加密 | 数据存储可加密（应用层） | 通过 |
| 创建幂等 | 样品/任务/数据/报告支持 X-Request-ID | 通过 |
