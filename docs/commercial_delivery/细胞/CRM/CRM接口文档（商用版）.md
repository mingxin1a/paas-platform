# CRM 接口文档（商用版）

**版本**：1.0  
**细胞名称**：客户关系管理（CRM）  
**适用对象**：对接方开发、集成测试

---

## 一、访问方式与规范

- **经网关访问**：`GET|POST|PATCH|DELETE https://<网关地址>/api/v1/crm/<path>`。
- **请求头**：`Content-Type: application/json`、`Authorization: Bearer <token>`、`X-Tenant-Id: <租户ID>`；POST/PATCH 建议带 `X-Request-ID` 实现幂等。
- **响应**：成功为 200/201， body 为 JSON；错误为 4xx/5xx，body 格式：`{"code":"ERROR_CODE","message":"描述","requestId":"请求ID"}`。

---

## 二、主要接口一览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /health | 健康检查 |
| GET | /metrics | 监控指标（客户数、商机转化率、漏斗） |
| GET | /customers | 客户列表（分页、keyword 高级查询、按负责人过滤） |
| POST | /customers | 创建客户（幂等） |
| GET | /customers/{id} | 客户详情 |
| PATCH | /customers/{id} | 更新客户 |
| DELETE | /customers/{id} | 删除客户 |
| POST | /customers/import | 批量导入客户 |
| GET | /customers/export | 导出客户（format=csv 或 JSON 分页） |
| GET | /customers/{id}/360 | 客户 360 视图 |
| GET | /contacts | 联系人列表 |
| POST | /contacts | 创建联系人 |
| GET | /opportunities | 商机列表 |
| POST | /opportunities | 创建商机 |
| POST | /opportunities/import | 批量导入商机 |
| GET | /opportunities/export | 导出商机（format=csv 或 JSON 分页） |
| GET | /opportunities/forecast | 商机预测 |
| GET | /audit-logs | 操作审计日志（分页、resourceType 筛选） |
| GET | /pipeline/summary | 管道汇总 |
| GET | /pipeline/funnel | 销售漏斗 |
| GET | /contracts | 合同列表 |
| POST | /contracts | 创建合同 |
| GET | /payments | 回款列表 |
| POST | /payments | 登记回款 |
| GET | /reports/funnel | 漏斗报表 |

---

## 三、请求/响应示例

**创建客户**：

```http
POST /api/v1/crm/customers HTTP/1.1
Content-Type: application/json
Authorization: Bearer <token>
X-Tenant-Id: tenant-001
X-Request-ID: req-uuid-001

{"name":"某某公司","contactPhone":"13800138000","contactEmail":"contact@example.com"}
```

```json
{"customerId":"xxx","tenantId":"tenant-001","name":"某某公司","contactPhone":"138****8000",...}
```

**客户列表（脱敏）**：

```http
GET /api/v1/crm/customers?page=1&pageSize=20 HTTP/1.1
Authorization: Bearer <token>
X-Tenant-Id: tenant-001
X-User-Id: user-001
```

```json
{"data":[...],"total":10,"page":1,"pageSize":20}
```

列表中 `contactPhone`、金额等为脱敏后内容。

---

## 四、错误码

| code | 说明 |
|------|------|
| BAD_REQUEST | 参数错误（如 name 为空） |
| NOT_FOUND | 客户/商机/合同等不存在 |
| IDEMPOTENT_CONFLICT | 同一 X-Request-ID 已处理过（幂等冲突） |
| DUPLICATE_NAME | 客户名称已存在（创建时） |

---

## 五、Swagger / OpenAPI

- CRM 为 FastAPI 实现，提供 Swagger UI：经网关代理访问 `GET /api/admin/cells/crm/docs`（需 Authorization），或直连细胞 `GET http://<crm-cell>:8001/docs`。
- 完整 OpenAPI 规范可从 `/openapi.json` 获取。

---

**文档归属**：商用交付文档包 · 细胞 · CRM  
**关联**：`cells/crm/docs/CRM接口文档（商用版）.md`
