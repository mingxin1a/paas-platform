# WMS 细胞档案

**文档版本**：V1.0  
**细胞名称**：WMS（仓储管理系统）  
**所属领域**：智能制造与工业物联  
**约束文档**：《01_【核心法律】基础与AI安全宪法_V3.0》《接口设计说明书_V2.0》《超级PaaS平台逻辑全景图》

---

## 1. 细胞标识

| 项 | 值 |
|----|-----|
| 细胞代码 | `wms` |
| 显示名称 | 仓储管理系统（WMS） |
| 领域 | 智能制造与工业物联 |
| 独立部署单元 | 是 |
| 独立数据库 | 是 |
| 档案状态 | 已归档 |

---

## 2. 与平台接口对接细节

### 2.1 API 契约（集装箱原则）

- **Base Path**：`/api/v1/wms`
- **协议**：HTTPS，JSON，UTF-8；请求头 `Content-Type`、`Authorization`、`X-Request-ID`；响应头 `Content-Type`、`X-Response-Time`。
- **认证**：OAuth 2.0 + JWT，多租户按平台约定。

### 2.2 核心资源与 URL 设计（示例）

| 资源 | 方法 | 路径示例 |
|------|------|----------|
| 库存/库存流水 | GET/POST | `/api/v1/wms/inventory`、`/api/v1/wms/inventory-transactions` |
| 入库单/出库单 | GET/POST | `/api/v1/wms/inbound-orders`、`/api/v1/wms/outbound-orders` |
| 库位/仓库 | GET/POST | `/api/v1/wms/warehouses`、`/api/v1/wms/locations` |
| 盘点 | GET/POST | `/api/v1/wms/stock-takes` |

错误响应符合《接口设计说明书》3.1.3；库存数量使用整数或 Long，金额用 Long(分)→String。

### 2.3 事件命名与结构

- **事件域**：`wms`；格式 `wms.[Entity].[Action]`；结构含 eventId、eventType、timestamp、source、traceId、data。

#### 发布事件

| eventType | 说明 |
|-----------|------|
| `wms.stock.updated` | 库存变更（《接口设计说明书》示例） |
| `wms.inbound.completed` | 入库完成 |
| `wms.outbound.completed` | 出库完成 |
| `wms.stock_take.completed` | 盘点完成 |

#### 订阅事件

| 订阅 eventType | 来源 | 用途 |
|----------------|------|------|
| `erp.order.created` | ERP | 销售/采购订单驱动出库/入库 |
| `mes.work_order.started` | MES | 工单开工驱动领料出库 |
| `tms.shipment.dispatched` | TMS | 发货单驱动出库 |

---

## 3. 业务配置要点

| 配置项 | 说明 | 默认 |
|--------|------|------|
| 租户隔离 | 与平台一致 | tenant_id |
| 事件溯源 | 核心库存可采用事件溯源，禁止 UPDATE 核心流水（《数据库设计说明书》） | 建议 |
| 边缘/弱网 | 支持离线入库/出库、断网续传 | 可选 |
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
