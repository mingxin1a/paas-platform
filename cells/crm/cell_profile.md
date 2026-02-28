# CRM 细胞档案

**细胞代码**：crm  
**显示名称**：客户关系管理（CRM）  
**所属领域**：智慧商业  
**约束文档**：《01_【核心法律】基础与AI安全宪法_V3.0》《接口设计说明书_V2.0》《超级PaaS平台逻辑全景图》

---

## 1. 模块概述

CRM 细胞负责**客户管理、联系人管理、商机管理、跟进记录**四类核心资源的独立存储与业务逻辑，使用 **Python FastAPI** 实现，通过 PaaS 标准化网关暴露 API。模块完全独立：独立数据库配置（SQLite/环境变量）、独立业务逻辑与 Dockerfile，**不直接依赖 platform_core**，仅通过标准化 HTTP 接口调用平台认证与网关能力。经注册中心被发现，健康检查接口符合网关自动注册与健康巡检规范。

---

## 2. 技术栈与接口契约

| 项 | 约定 |
|----|------|
| 实现框架 | Python 3.11 + FastAPI |
| 网关路径前缀 | `/api/v1/crm`（由网关转发，细胞根路径为 `/`） |
| 协议与格式 | HTTPS/JSON/UTF-8 |
| 必须请求头 | `Content-Type`、`Authorization`、`X-Request-ID`（POST/PUT/PATCH 幂等） |
| 必须响应头 | `Content-Type`、`X-Response-Time` |
| 错误响应格式 | `{"code","message","details","requestId"}`（《接口设计说明书》3.1.3） |
| 认证 | 平台 OAuth 2.0 + JWT；可选 `PLATFORM_AUTH_URL` 通过 HTTP 校验 Token |
| 多租户 | 请求头 `X-Tenant-Id` |

---

## 3. 核心资源与 URL 设计

| 资源 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 客户 | GET | /customers | 列表（分页 page, pageSize） |
| 客户 | POST | /customers | 创建（幂等 X-Request-ID） |
| 客户 | GET | /customers/{customerId} | 详情 |
| 客户 | PATCH | /customers/{customerId} | 更新 |
| 客户 | DELETE | /customers/{customerId} | 删除 |
| 联系人 | GET | /contacts | 列表（可选 customerId） |
| 联系人 | POST | /contacts | 创建 |
| 联系人 | GET | /contacts/{contactId} | 详情 |
| 联系人 | PATCH | /contacts/{contactId} | 更新 |
| 联系人 | DELETE | /contacts/{contactId} | 删除 |
| 商机 | GET | /opportunities | 列表（可选 customerId） |
| 商机 | POST | /opportunities | 创建 |
| 商机 | GET | /opportunities/{opportunityId} | 详情 |
| 商机 | PATCH | /opportunities/{opportunityId} | 更新 |
| 商机 | DELETE | /opportunities/{opportunityId} | 删除 |
| 跟进记录 | GET | /follow-ups | 列表（可选 customerId, opportunityId） |
| 跟进记录 | POST | /follow-ups | 创建 |
| 跟进记录 | GET | /follow-ups/{followUpId} | 详情 |
| 跟进记录 | PATCH | /follow-ups/{followUpId} | 更新 |
| 跟进记录 | DELETE | /follow-ups/{followUpId} | 删除 |
| 健康检查 | GET | /health | 符合网关注册与巡检规范 |

---

## 4. 独立配置

| 配置项 | 说明 | 默认 |
|--------|------|------|
| CRM_DATABASE_URL | 数据库连接（SQLite） | sqlite:///./crm_cell.db |
| PORT | 服务端口 | 8001 |
| PLATFORM_AUTH_URL | 平台认证地址（可选，HTTP 校验 Token） | - |
| CRM_AUTH_STRICT | 未配置认证地址时是否拒绝请求 | 0 |
| DEFAULT_TENANT_ID | 默认租户 | default |

---

## 5. 发布/订阅事件（可选扩展）

**发布**：`crm.customer.created`, `crm.customer.updated`, `crm.opportunity.created`, `crm.opportunity.closed`  
**订阅**：`erp.contract.signed`, `oa.task.completed`（按实际业务配置）

---

## 6. 合规声明

本细胞遵守《01_核心法律》细胞自治、跨细胞仅事件/接口、禁止跨细胞库直连；遵守《接口设计说明书》集装箱原则、玻璃房原则、零心智负担原则、POST/PUT 幂等（X-Request-ID）。接入/下线不修改平台级架构文档。
