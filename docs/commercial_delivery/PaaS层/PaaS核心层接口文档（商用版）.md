# PaaS 核心层接口文档（商用版）

**版本**：1.0  
**适用对象**：对接方开发、运维  
**规范**：遵循《接口设计说明书》；本文档仅描述 **PaaS 层自身暴露的接口**（网关、治理、认证、管理端 API）。

---

## 一、通用约定

| 项目 | 说明 |
|------|------|
| 协议 | HTTP/HTTPS |
| 数据格式 | JSON，UTF-8 |
| 请求头 | Content-Type: application/json；POST/PUT/PATCH 建议 X-Request-ID；业务请求建议 Authorization、X-Tenant-Id |
| 错误响应 | `{"code":"ERROR_CODE","message":"描述","details":"可选","requestId":"请求ID"}` |

---

## 二、网关接口

### 2.1 健康检查

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /health | 网关存活，返回 `{"status":"up"}` |

### 2.2 业务转发（经网关访问细胞）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST/PUT/PATCH/DELETE | /api/v1/\<cell\>/\<path\> | 转发到对应细胞；\<cell\> 如 crm、erp、wms 等，\<path\> 为细胞内路径（如 customers、orders） |

**请求头**：Authorization、Content-Type（POST/PUT 时）、X-Request-ID（POST/PUT/PATCH 时建议）、X-Tenant-Id、X-Trace-Id（可选）。

**响应**：由下游细胞返回；网关透传状态码与响应体。若转发失败返回 502/503 及统一错误体。

### 2.3 认证接口（网关提供）

| 方法 | 路径 | 请求体 | 响应 |
|------|------|--------|------|
| POST | /api/auth/login | `{"username":"xxx","password":"xxx"}` | `{"token":"xxx","user":{"username","role","allowedCells"}}` |
| GET | /api/auth/me | 无（需 Header Authorization: Bearer \<token\>） | 当前用户信息 |

### 2.4 管理端接口（均需 Authorization）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/admin/cells | 细胞列表及启用状态、baseUrl |
| PATCH | /api/admin/cells/\<cell_id\> | 启用/停用细胞，body：`{"enabled":true\|false}` |
| GET | /api/admin/routes | 当前网关路由配置（细胞→base_url） |
| GET | /api/admin/health-summary | 网关 + 各细胞健康汇总 |
| GET | /api/admin/cells/\<cell_id\>/docs | 代理细胞接口文档（如 Swagger） |
| GET | /api/admin/governance/\<path\> | 代理治理中心只读 API |
| GET | /api/admin/users | 用户列表（当前可为 Mock） |
| PATCH | /api/admin/users/\<user_id\> | 更新用户（如 allowedCells） |

---

## 三、治理中心接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/governance/health | 治理中心健康 |
| GET | /api/governance/health/cells | 各细胞健康巡检结果（若实现） |

---

## 四、错误码（PaaS 层）

| code | HTTP 状态 | 说明 |
|------|-----------|------|
| MISSING_HEADER | 400 | 缺少必须请求头（Content-Type/Authorization/X-Request-ID 等） |
| MISSING_TENANT_ID | 400 | 缺少 X-Tenant-Id（生产开启强制租户时） |
| BAD_REQUEST | 400 | 请求参数错误 |
| UNAUTHORIZED | 401 | 未登录或 token 无效 |
| NOT_FOUND | 404 | 资源不存在（如细胞未配置） |
| CELL_NOT_FOUND | 503 | 细胞未注册或未配置 URL |
| CELL_UNREACHABLE | 502 | 转发到细胞时网络/超时错误 |
| CIRCUIT_OPEN | 503 | 细胞熔断打开 |
| RED_LIGHT | 503 | 系统负载过高，仅允许只读（若启用红绿灯） |
| SIGNATURE_INVALID | 403 | 验签失败（若启用加签） |

---

## 五、请求/响应示例

**登录**：

```http
POST /api/auth/login HTTP/1.1
Content-Type: application/json

{"username":"admin","password":"admin"}
```

```json
{"token":"a1b2c3...","user":{"username":"admin","role":"admin","allowedCells":[]}}
```

**经网关访问 CRM 客户列表**：

```http
GET /api/v1/crm/customers?page=1&pageSize=20 HTTP/1.1
Authorization: Bearer <token>
X-Tenant-Id: tenant-001
Content-Type: application/json
```

```json
{"data":[...],"total":10,"page":1,"pageSize":20}
```

**健康汇总**：

```http
GET /api/admin/health-summary HTTP/1.1
Authorization: Bearer <token>
```

```json
{"gateway":"up","cells":[{"id":"crm","name":"客户关系","status":"up"},...]}
```

---

**文档归属**：商用交付文档包 · PaaS 层  
**维护**：随接口变更更新。
