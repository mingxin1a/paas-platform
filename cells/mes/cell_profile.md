# MES 细胞档案

**细胞代码**：mes | **领域**：智慧供应链  
**网关前缀**：/api/v1/mes | **注册服务名**：mes-cell | **监控维度**：mes.*

概述：制造执行，工单、工序报工、设备状态、工艺路线。经网关/注册中心/监控对接；跨细胞仅事件或异步 API。事件域 mes。发布：mes.work_order.created, mes.work_order.completed, mes.operation.reported。订阅：erp.order.created, plm.bom.updated, wms.stock.updated。
