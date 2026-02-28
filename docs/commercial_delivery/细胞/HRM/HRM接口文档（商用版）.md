# 人力资源 接口文档（商用版）

**版本**：1.0 | **细胞**：HRM

## 访问说明

- 经网关：`/api/v1/hrm/<path>`
- 请求头：`Authorization`、`X-Tenant-Id`、`X-Request-ID`

## 路由列表

| 路径 | 方法 | 说明 |
|------|------|------|
| /health | GET | — |
| /employees | GET | — |
| /employees | POST | — |
| /departments | GET | — |
| /departments | POST | — |
| /leave-requests | GET | — |
| /leave-requests | POST | — |
| /employees/<employee_id> | GET | — |
| /departments/<department_id> | GET | — |
| /leave-requests/<request_id> | GET | — |
| /leave-requests/<request_id> | PATCH | — |

---
由 `scripts/generate_docs.py` 根据 app.py 自动生成。