# MES 与 ERP 对接手册

**版本**：1.0 | **细胞**：MES、ERP

## 1. 对接原则

- MES 与 ERP 严格解耦，仅通过 PaaS 层标准化接口交互，不直连对方数据库。
- 数据格式：JSON（工业场景可扩展 XML）；金额/数量单位与 ERP 约定一致（如数量为基本单位、金额为分）。

## 2. 典型对接场景

### 2.1 生产订单来源

- ERP 下发生产计划/订单至 MES：调用 MES 的 POST /production-plans、POST /production-orders（需带 X-Tenant-Id、X-Request-ID）。
- MES 生产订单状态回写 ERP：由 MES 在状态变更时通过事件或 PaaS 网关回调 ERP 接口（具体由集成方案约定）。

### 2.2 领料与物料

- MES 领料消耗：MES 记录领料；库存扣减在 WMS 或 ERP 侧执行，通过 PaaS 调用 WMS 出库或 ERP 物料扣减接口。
- BOM 主数据：可由 ERP 同步至 MES（调用 MES POST /boms），或 MES 从主数据服务获取。

### 2.3 生产入库

- MES 生产入库完成后，需驱动 WMS 入库或 ERP 入库单：调用 WMS 入库接口（采购/生产入库类型）或 ERP 入库接口，传递订单号、物料、数量、批次/序列号。

## 3. 接口清单（MES 侧供 ERP/网关调用）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /production-plans | 生产计划列表 |
| POST | /production-plans | 创建生产计划（幂等） |
| GET | /production-orders | 生产订单列表（可按 workshopId 过滤） |
| POST | /production-orders | 创建生产订单（幂等） |
| GET | /trace/order/<order_id> | 生产追溯（订单维度） |
| GET | /trace/lot/<lot_number> | 生产追溯（批次维度） |

## 4. 安全与审计

- 所有调用经 PaaS 网关，携带 X-Tenant-Id、X-Request-ID、Authorization。
- 操作日志在 MES 侧留存≥1 年，便于工业追溯与审计。
