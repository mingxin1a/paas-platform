# TMS 物流管理员操作指南

**版本**：1.0 | **细胞**：TMS

## 1. 运输订单

- **列表**：GET /shipments?page=1&pageSize=20；带 X-User-Id 时仅返回当前用户负责的订单。
- **创建**：POST /shipments，Body：trackingNo、origin、destination；头带 X-Request-ID（幂等）；X-User-Id 为负责人。
- **详情**：GET /shipments/<shipment_id>。
- **更新状态**：PATCH /shipments/<shipment_id>，Body：status。
- **批量导入**：POST /shipments/import，Body：items：[{trackingNo, origin, destination}, ...]，单次≤500；头带 X-User-Id 作为负责人。

## 2. 车辆与司机

- **车辆**：GET /vehicles；POST /vehicles（plateNo、model）。
- **司机**：GET /drivers（返回手机号/身份证脱敏）；POST /drivers（name、phone、idNo，存储后可加密）。

## 3. 运输轨迹与到货确认

- **轨迹**：GET /tracks?shipmentId=xxx；POST /tracks（shipmentId、lat、lng、nodeName），运单不存在时返回业务错误。
- **到货确认**：POST /delivery-confirm，Body：shipmentId、status；运单不存在时返回「运单不存在，无法对不存在的运单做到货确认」。

## 4. 费用与对账

- **运输费用**：GET /transport-costs?shipmentId=xxx；POST /transport-costs（shipmentId、amountCents、costType）。
- **物流对账**：GET /reconciliations；POST /reconciliations（periodStart、periodEnd、totalAmountCents）。

## 5. 监控

- GET /metrics：运输准时率（模拟）、运单总量、已确认数、运输费用汇总。
