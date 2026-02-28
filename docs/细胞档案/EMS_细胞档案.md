# EMS 细胞档案

**文档版本**：V1.0  
**细胞名称**：EMS（能源管理系统）  
**所属领域**：智能制造与工业物联  
**约束文档**：《01_【核心法律】基础与AI安全宪法_V3.0》《接口设计说明书_V2.0》《超级PaaS平台逻辑全景图》

---

## 1. 细胞标识

| 项 | 值 |
|----|-----|
| 细胞代码 | `ems` |
| 显示名称 | 能源管理系统（EMS） |
| 领域 | 智能制造与工业物联 |
| 独立部署单元 | 是 |
| 独立数据库 | 是 |
| 档案状态 | 已归档 |

---

## 2. 与平台接口对接细节

### 2.1 API 契约（集装箱原则）

- **Base Path**：`/api/v1/ems`
- **协议**：HTTPS，JSON，UTF-8；请求头 `Content-Type`、`Authorization`、`X-Request-ID`；响应头 `Content-Type`、`X-Response-Time`。
- **认证**：OAuth 2.0 + JWT，多租户按平台约定。

### 2.2 核心资源与 URL 设计（示例）

| 资源 | 方法 | 路径示例 |
|------|------|----------|
| 能耗数据/计量点 | GET/POST | `/api/v1/ems/meters`、`/api/v1/ems/consumption-records` |
| 能效分析 | GET | `/api/v1/ems/analytics` |
| 告警/阈值 | GET/POST | `/api/v1/ems/alerts`、`/api/v1/ems/thresholds` |

错误响应符合《接口设计说明书》3.1.3。

### 2.3 事件命名与结构

- **事件域**：`ems`；格式 `ems.[Entity].[Action]`；结构含 eventId、eventType、timestamp、source、traceId、data。

#### 发布事件

| eventType | 说明 |
|-----------|------|
| `ems.consumption.recorded` | 能耗数据上报 |
| `ems.alert.triggered` | 能耗告警触发 |
| `ems.threshold.breached` | 阈值超限 |

#### 订阅事件

| 订阅 eventType | 来源 | 用途 |
|----------------|------|------|
| `mes.work_order.started` | MES | 工单开工关联能耗计量 |
| `mes.equipment.status_changed` | MES | 设备状态与能耗关联 |

---

## 3. 业务配置要点

| 配置项 | 说明 | 默认 |
|--------|------|------|
| 租户隔离 | 与平台一致 | tenant_id |
| 操作路径深度 | ≤3 次点击 | 必须满足 |
| 审计日志 | trace_id、人类可读、180 天 | 启用 |

---

## 4. 依赖与协作

- **依赖平台**：认证、API 网关、事件总线、租户、安全感知。
- **与其它细胞**：仅事件或平台转发 HTTP；禁止跨细胞库直连；跨细胞仅异步。

---

## 5. 合规声明

- 遵守《01_核心法律》第七部分及《接口设计说明书》；接入/下线不修改平台级架构文档。

---

**编制**：SuperPaaS-God v8.0
