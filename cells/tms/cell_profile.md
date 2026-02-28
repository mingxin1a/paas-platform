# TMS 细胞档案

**细胞代码**：tms | **领域**：智慧供应链  
**网关前缀**：/api/v1/tms | **注册服务名**：tms-cell | **监控维度**：tms.*

概述：运输管理，运单、运输任务、车辆/司机、轨迹/签收。经网关/注册中心/监控对接；跨细胞仅事件或异步 API。事件域 tms。发布：tms.shipment.created, tms.shipment.dispatched, tms.shipment.delivered。订阅：wms.outbound.completed, erp.order.created。
