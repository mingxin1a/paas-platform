# LIMS 细胞档案

**文档版本**：V1.0  
**细胞名称**：LIMS（实验室信息管理系统）  
**所属领域**：专业垂直行业  
**约束文档**：《01_【核心法律】基础与AI安全宪法_V3.0》《接口设计说明书_V2.0》《超级PaaS平台逻辑全景图》

---

## 1. 细胞标识

| 项 | 值 |
|----|-----|
| 细胞代码 | `lims` |
| 显示名称 | 实验室信息管理系统（LIMS） |
| 领域 | 专业垂直行业 |
| 独立部署单元 | 是 |
| 独立数据库 | 是 |
| 档案状态 | 已归档 |

---

## 2. 与平台接口对接细节

### 2.1 API 契约（集装箱原则）

- **Base Path**：`/api/v1/lims`
- **协议**：HTTPS，JSON，UTF-8；请求头 `Content-Type`、`Authorization`、`X-Request-ID`；响应头 `Content-Type`、`X-Response-Time`。
- **认证**：OAuth 2.0 + JWT，多租户按平台约定；实验室数据可能含敏感信息，需脱敏与审计。

### 2.2 核心资源与 URL 设计（示例）

| 资源 | 方法 | 路径示例 |
|------|------|----------|
| 样品/检测任务 | GET/POST | `/api/v1/lims/samples`、`/api/v1/lims/test-requests` |
| 检测结果 | GET/POST | `/api/v1/lims/results` |
| 方法/标准 | GET/POST | `/api/v1/lims/methods`、`/api/v1/lims/standards` |
| 仪器/校准 | GET/POST | `/api/v1/lims/instruments`、`/api/v1/lims/calibrations` |

错误响应符合《接口设计说明书》3.1.3。

### 2.3 事件命名与结构

- **事件域**：`lims`；格式 `lims.[Entity].[Action]`；结构含 eventId、eventType、timestamp、source、traceId、data。

#### 发布事件

| eventType | 说明 |
|-----------|------|
| `lims.sample.registered` | 样品登记 |
| `lims.sample.received` | 样品接收 |
| `lims.result.recorded` | 检测结果录入 |
| `lims.result.approved` | 结果审核通过 |
| `lims.certificate.issued` | 报告/证书签发 |

#### 订阅事件

| 订阅 eventType | 来源 | 用途 |
|----------------|------|------|
| `erp.order.created` | ERP | 来料检验任务（若与 ERP 集成） |
| `wms.inbound.completed` | WMS | 入库批次驱动质检任务（若与 WMS 集成） |

---

## 3. 业务配置要点

| 配置项 | 说明 | 默认 |
|--------|------|------|
| 租户隔离 | 与平台一致 | tenant_id |
| 敏感数据脱敏 | 委托方、样品关联方等按策略脱敏 | 启用 |
| 审计与合规 | 操作日志 180 天、可追溯（trace_id） | 启用 |
| 操作路径深度 | ≤3 次点击 | 必须满足 |

---

## 4. 依赖与协作

- **依赖平台**：认证、API 网关、事件总线、租户、安全感知。
- **与其它细胞**：仅事件或平台转发 HTTP；禁止跨细胞库直连；跨细胞仅异步；跨系统交互需数字签名与验签（宪法修正案 #5）。

---

## 5. 合规声明

- 遵守《01_核心法律》第七部分及《接口设计说明书》；遵守宪法修正案 #4（数据主权）、#5（抗抵赖）；接入/下线不修改平台级架构文档。

---

**编制**：SuperPaaS-God v8.0
