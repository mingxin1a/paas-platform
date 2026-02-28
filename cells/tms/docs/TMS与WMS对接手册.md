# TMS 与 WMS 对接手册

**版本**：1.0 | **细胞**：TMS、WMS

## 1. 对接原则

- TMS 与 WMS 严格解耦，仅通过 PaaS 层标准化接口交互。
- 数据格式：JSON（工业场景可扩展 XML）。

## 2. 典型对接场景

### 2.1 出库驱动运输

- WMS 出库单发货完成后，可触发创建 TMS 运输订单：调用 TMS POST /shipments（origin、destination、trackingNo 等），并将出库单号或单号关联至 trackingNo/扩展字段。

### 2.2 到货驱动入库

- TMS 到货确认后，可驱动 WMS 入库：调用 WMS 创建入库单并收货，或由集成层将「到货」事件转换为 WMS 入库单。

### 2.3 物流节点提醒

- TMS 运输轨迹节点（POST /tracks）可与通知服务对接，在关键节点（如发车、在途、到货）推送提醒给仓库或客户。

## 3. 接口清单（TMS 侧供 WMS/网关调用）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /shipments | 运单列表（可选 ownerId 过滤） |
| POST | /shipments | 创建运单（幂等） |
| GET | /shipments/<id> | 运单详情 |
| PATCH | /shipments/<id> | 更新状态 |
| POST | /tracks | 记录轨迹 |
| POST | /delivery-confirm | 到货确认 |

## 4. 安全与审计

- 所有调用经 PaaS 网关，携带 X-Tenant-Id、X-Request-ID、Authorization。
- 操作日志可留存≥1 年，符合工业可追溯要求。
