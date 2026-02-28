# SRM 细胞档案

**细胞代码**：srm | **领域**：智慧供应链  
**网关前缀**：/api/v1/srm | **注册服务名**：srm-cell | **监控维度**：srm.*

概述：供应商关系管理，供应商、采购订单、询比价、评估。经网关/注册中心/监控对接；跨细胞仅事件或异步 API。事件域 srm。发布：srm.supplier.created, srm.purchase.order.created。订阅：erp.order.created, wms.stock.updated。
