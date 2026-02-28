# WMS 库管员操作指南

**版本**：1.0 | **细胞**：WMS

## 1. 入库

- **创建入库单**：POST /inbound-orders，Body：warehouseId；头带 X-Request-ID。
- **添加行**：POST /inbound-orders/<order_id>/lines，Body：skuId、quantity、lotNumber。
- **收货**：POST /inbound-orders/<order_id>/receive，Body：lineId、receivedQuantity、warehouseId、lotNumber；头带 X-Request-ID（幂等）。
- **扫码入库（模拟）**：POST /scan/inbound，Body：orderId、barcode、quantity。

## 2. 出库

- **创建出库单**：POST /outbound-orders，Body：warehouseId。
- **添加行**：POST /outbound-orders/<order_id>/lines，Body：skuId、quantity。
- **发货**：POST /outbound-orders/<order_id>/ship，Body：lineId、pickedQuantity、warehouseId；头带 X-Request-ID（幂等）。若可用库存不足返回「出库数量超出可用库存」。
- **扫码出库（模拟）**：POST /scan/outbound，Body：orderId、barcode、quantity。

## 3. 调拨

- **列表**：GET /transfers。
- **创建调拨**：POST /transfers，Body：fromWarehouseId、toWarehouseId、skuId、quantity；头带 X-Request-ID（幂等）。源仓库库存不足时返回「源仓库可用库存不足」。

## 4. 盘点

- **列表**：GET /cycle-counts?warehouseId=xxx。
- **批量盘点**：POST /cycle-counts/batch，Body：warehouseId、items：[{skuId, locationId?, bookQuantity, countQuantity}, ...]，单次不超过 2000 条。

## 5. 库存冻结与效期预警

- **冻结**：POST /inventory/freeze，Body：warehouseId、skuId、quantity、reason。
- **解冻**：POST /inventory/freeze/<freeze_id>/release。
- **效期预警**：GET /alerts/expiry?daysAhead=30。

## 6. 库位与批次

- **库位**：GET /locations?warehouseId=xxx；POST /locations（locationId、warehouseId、zoneCode 等）。
- **批次**：GET /lots?skuId=&lotNumber=&warehouseId=；GET /lots/fifo?warehouseId=&skuId=&quantity=。

## 7. 监控

- GET /metrics：库存周转相关指标、盘点总数、效期预警数。
