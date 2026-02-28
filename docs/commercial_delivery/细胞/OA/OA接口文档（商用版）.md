# OA 接口文档（商用版）

**版本**：1.0 | **细胞**：OA

## 访问与主要接口

- 经网关：`/api/v1/oa/<path>`；请求头规范同《接口设计说明书》。
- 主要路径：/tasks（任务）、/approvals（审批）、/announcements（公告）。
- **商用级新增**：GET /audit-logs（操作审计）；POST /tasks/batch-complete（批量办结，body.taskIds）；GET /reminders（待办与待审批数量）；GET /announcements/<id>（公告详情）。

**详细**：见 `cells/oa/docs` 及网关代理 `/api/admin/cells/oa/docs`（若提供）。
