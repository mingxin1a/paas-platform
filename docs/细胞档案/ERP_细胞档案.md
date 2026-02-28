# ERP 细胞档案

**文档版本**：V1.0  
**细胞名称**：ERP（企业资源计划）  
**所属领域**：通用企业管理  
**约束文档**：《01_【核心法律】基础与AI安全宪法_V3.0》《接口设计说明书_V2.0》《超级PaaS平台逻辑全景图》

---

## 1. 细胞标识

| 项 | 值 |
|----|-----|
| 细胞代码 | `erp` |
| 显示名称 | 企业资源计划（ERP） |
| 领域 | 通用企业管理 |
| 独立部署单元 | 是 |
| 独立数据库 | 是 |
| 档案状态 | 已归档 |

---

## 2. 与平台接口对接细节

### 2.1 API 契约（集装箱原则）

- **Base Path**：`/api/v1/erp`
- **协议**：HTTPS，JSON，UTF-8；请求头含 `Content-Type`、`Authorization`、`X-Request-ID`；响应头含 `Content-Type`、`X-Response-Time`。
- **认证**：OAuth 2.0 + JWT，多租户按平台约定。

### 2.2 核心资源与 URL 设计（示例）

| 资源 | 方法 | 路径示例 |
|------|------|----------|
| 订单 | GET/POST | `/api/v1/erp/orders`、`/api/v1/erp/orders/{id}` |
| 合同 | GET/POST | `/api/v1/erp/contracts` |
| 物料/产品 | GET/POST | `/api/v1/erp/products` |
| 财务单据 | GET/POST | `/api/v1/erp/financial-documents` |

金额遵循 Long(分)→BigDecimal(元)→String(传输)；错误响应符合《接口设计说明书》3.1.3。

### 2.3 事件命名与结构

- **事件域**：`erp`；格式 `erp.[Entity].[Action]`；结构含 eventId、eventType、timestamp、source、traceId、data。

#### 发布事件

| eventType | 说明 |
|-----------|------|
| `erp.order.created` | 订单创建 |
| `erp.order.updated` | 订单变更 |
| `erp.contract.signed` | 合同签约 |
| `erp.product.created` | 产品/物料创建 |

#### 订阅事件

| 订阅 eventType | 来源 | 用途 |
|----------------|------|------|
| `wms.stock.updated` | WMS | 库存变更后更新 ERP 可用量 |
| `crm.opportunity.closed` | CRM | 商机赢单后触达订单/合同 |
| `srm.purchase.order.created` | SRM | 采购单同步 |

---

## 3. 业务配置要点

| 配置项 | 说明 | 默认 |
|--------|------|------|
| 租户隔离 | Schema 或 tenant_id，与平台一致 | tenant_id |
| 金额与精度 | Long(分) 存储，禁止 float/double | 强制 |
| 敏感字段脱敏 | 身份证、银行账号等动态脱敏 | 启用 |
| 操作路径深度 | ≤3 次点击 | 必须满足 |
| 审计日志 | trace_id、人类可读、180 天 | 启用 |

---

## 4. 依赖与协作

- **依赖平台**：认证、API 网关、事件总线、租户、安全感知。
- **与其它细胞**：仅事件或平台转发的 HTTP；禁止跨细胞库直连；跨细胞仅异步。

---

## 5. 合规声明

- 遵守《01_核心法律》第七部分：细胞自治、跨细胞访问禁令、跨细胞同步调用禁令、事件语义冻结。
- 遵守《接口设计说明书》：集装箱、玻璃房、零心智负担；熔断、幂等。
- 接入/下线不修改平台级架构文档。

---

**编制**：SuperPaaS-God v8.0
