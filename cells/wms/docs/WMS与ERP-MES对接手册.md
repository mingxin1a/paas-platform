# WMS 与 ERP/MES 对接手册

**版本**：1.0 | **细胞**：WMS、ERP、MES

## 1. 对接原则

- WMS 与 ERP、MES 严格解耦，仅通过 PaaS 层标准化接口交互。
- 数据格式：JSON（工业场景可扩展 XML）。

## 2. 典型对接场景

### 2.1 采购入库（ERP → WMS）

- ERP 创建采购入库单后，调用 WMS POST /inbound-orders（warehouseId），再 POST /inbound-orders/<id>/lines 添加物料行；收货时调用 POST /inbound-orders/<id>/receive（幂等）。

### 2.2 生产入库（MES → WMS）

- MES 生产入库完成后，驱动 WMS 入库：调用 WMS 创建入库单并收货，或由集成层将 MES 生产入库单转换为 WMS 入库单并执行收货。

### 2.3 销售/领料出库（ERP/MES → WMS）

- ERP 销售出库单或 MES 领料需求下发后，调用 WMS POST /outbound-orders 及行、POST /outbound-orders/<id>/ship（防负库存、幂等）。

### 2.4 库存查询与调拨

- ERP/MES 查询库存：GET /inventory?warehouseId=&skuId=。
- 调拨：POST /transfers（fromWarehouseId、toWarehouseId、skuId、quantity）。

## 3. 接口清单（WMS 侧供 ERP/MES/网关调用）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /inventory | 库存查询 |
| GET/POST | /inbound-orders | 入库单列表/创建 |
| POST | /inbound-orders/<id>/lines | 入库行 |
| POST | /inbound-orders/<id>/receive | 收货（幂等） |
| GET/POST | /outbound-orders | 出库单列表/创建 |
| POST | /outbound-orders/<id>/lines | 出库行 |
| POST | /outbound-orders/<id>/ship | 发货（幂等、防负库存） |
| GET/POST | /transfers | 调拨列表/创建 |
| GET | /lots、/lots/fifo | 批次、FIFO |
| GET | /alerts/expiry | 效期预警 |

## 4. 安全与审计

- 所有调用经 PaaS 网关，携带 X-Tenant-Id、X-Request-ID、Authorization。
- 出入库操作有人性化审计日志，可留存≥1 年（配置）。
