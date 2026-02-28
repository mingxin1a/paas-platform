# OA 审批流程配置指南

**版本**：1.0 | **细胞**：OA

## 1. 审批类型

当前支持的流程类型（typeCode）：

| typeCode | 说明 |
|----------|------|
| purchase | 采购审批 |
| reimburse | 报销审批 |
| leave | 请假审批 |

## 2. 审批状态

| status | 说明 |
|--------|------|
| draft | 草稿（创建后初始状态） |
| pending | 待审批（提交后） |
| approved | 已通过（后续节点可扩展） |
| rejected | 已驳回（后续节点可扩展） |

## 3. 接口说明

### 3.1 创建审批单

- **POST /approvals**
- 请求头：X-Tenant-Id、X-Request-ID（幂等）、X-User-Id（申请人）
- Body：`{"typeCode":"leave","formData":{"reason":"事假","days":2}}`
- 创建后状态为 draft。

### 3.2 提交审批

- **POST /approvals/<instance_id>/submit**
- 请求头：X-Request-ID（幂等）
- 将 draft 转为 pending；同一 X-Request-ID 重复调用返回 200 及当前单（幂等）。

### 3.3 查询审批列表

- **GET /approvals?page=1&pageSize=20&status=pending**
- 请求头：X-User-Id 可选；若携带则仅返回该申请人发起的单（数据权限：只能看自己发起/待审批的流程）。

## 4. 流程节点与扩展

- 当前为单节点（草稿→待审批）；多级审批、节点配置（node_config）可基于 approval_definition、approval_instance 表扩展。
- 流程节点异常时，可对接通知服务（如邮件/站内信）通知管理员；实现细节见运维与监控文档。
