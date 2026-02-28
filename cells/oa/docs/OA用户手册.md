# OA 用户手册

**版本**：1.0 | **细胞**：办公自动化（OA）

## 1. 概述

OA 细胞提供任务、审批（采购/报销/请假）、公告等能力，通过 PaaS 网关暴露。所有写操作需提供 **X-Tenant-Id**、**X-Request-ID**（POST 幂等）；审批列表建议带 **X-User-Id** 以仅查看本人数据。

## 2. 功能入口

| 能力 | 方法 | 路径 |
|------|------|------|
| 健康检查 | GET | /health |
| 任务 | GET/POST/PATCH | /tasks、/tasks/<id> |
| 审批列表 | GET | /approvals?page=1&pageSize=20&status= |
| 创建审批 | POST | /approvals |
| 提交审批 | POST | /approvals/<instance_id>/submit |
| 公告列表 | GET | /announcements?page=1&pageSize=20 |
| 发布公告 | POST | /announcements |

## 3. 典型流程

### 3.1 任务

- 创建任务：POST /tasks，Body：`{"title":"待办标题","assigneeId":"","priority":0}`。
- 更新状态：PATCH /tasks/<task_id>，Body：`{"status":1}`。

### 3.2 审批

- 创建审批单：POST /approvals，Body：`{"typeCode":"leave","formData":{"reason":"事假","days":2}}`，头带 X-Request-ID、X-User-Id。
- 提交审批：POST /approvals/<instance_id>/submit，头带 X-Request-ID（支持重试幂等）。
- 查看我的审批：GET /approvals，请求头带 X-User-Id，可选 status=draft|pending。

### 3.3 公告

- 查看公告：GET /announcements，分页参数 page、pageSize。
- 发布公告：POST /announcements，Body：`{"title":"标题","content":"正文"}`，头带 X-Request-ID。

## 4. 错误说明

- **NOT_FOUND**：任务/审批单/公告不存在。
- **IDEMPOTENT_CONFLICT**：同一 X-Request-ID 已创建过资源。
- **BAD_REQUEST**：必填参数缺失（如 title、typeCode）。

## 5. 约束与合规

- 审批流程数据权限：仅能查看自己发起的审批（通过 X-User-Id 过滤）。
- 文件上传防病毒：当前为元数据 Schema；实际上传与病毒扫描由扩展实现。
