# MES 车间操作指南

**版本**：1.0 | **细胞**：MES | **受众**：车间主任、班组长、操作工

## 1. 接口与权限

- **BaseURL**：经网关 `/api/v1/mes`；细胞直连 `http://<host>:8006`。
- **请求头**：X-Tenant-Id、X-Request-ID（POST 必填）、X-Workshop-Id（车间数据权限：车间主任只查本车间订单时必填）。

## 2. 工单

- **列表**：GET /work-orders?page=1&pageSize=20&workshopId=xxx（按车间过滤）
- **创建**：POST /work-orders，Body：orderNo、productCode、qty、workshopId
- **更新状态**：PATCH /work-orders/<id>，Body：status

## 3. 生产计划与生产订单

- **生产计划**：GET /production-plans；POST /production-plans（planNo、productSku、plannedQty、planDate）
- **生产订单**：GET /production-orders?workshopId=xxx（车间主任只传本车间 ID）；POST /production-orders（workshopId、orderNo、productSku、quantity、planId）

## 4. 领料

- **领料单列表**：GET /material-issues?orderId=xxx
- **创建领料单**：POST /material-issues，Body：orderId、materialSku、requiredQty
- **执行领料**：POST /material-issues/<issue_id>/issue，Body：issueQty  
  - 防超领：已领+本次不得超过应领；否则返回「领料数量超过应领数量或领料单不存在」

## 5. 报工

- **报工列表**：GET /work-reports?orderId=xxx
- **批量报工**：POST /work-reports/batch，Body：orderId、items：[{operationCode, completedQty}, ...]，单次不超过 200 条工序

## 6. 生产入库

- **生产入库**：POST /production-inbounds，Body：orderId、warehouseId、quantity、lotNumber、serialNumbers；头带 X-Request-ID（幂等，重复提交返回 200 及原记录）

## 7. 生产追溯

- **按批次**：GET /trace/lot/<lot_number>
- **按订单**：GET /trace/order/<order_id>

## 8. 监控与配置

- **监控指标**：GET /metrics（生产完成率、领料准确率、设备稼动率）
- **日志留存**：GET /config/retention（operationLogRetentionDays，≥1 年）
