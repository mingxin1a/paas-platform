# WMS 细胞档案

**细胞代码**：wms | **领域**：智慧供应链  
**网关前缀**：/api/v1/wms | **注册服务名**：wms-cell | **监控维度**：wms.*

概述：仓储管理，库存、入库/出库单、库位、盘点。经网关/注册中心/监控对接；跨细胞仅事件或异步 API。事件域 wms。发布：wms.stock.updated, wms.inbound.completed, wms.outbound.completed。订阅：erp.order.created, mes.work_order.started, tms.shipment.dispatched。
