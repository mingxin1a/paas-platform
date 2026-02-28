# PLM 细胞档案

**细胞代码**：plm | **领域**：智慧供应链  
**网关前缀**：/api/v1/plm | **注册服务名**：plm-cell | **监控维度**：plm.*

概述：产品生命周期管理，产品/BOM、文档、变更/版本。经网关/注册中心/监控对接；跨细胞仅事件或异步 API。事件域 plm。发布：plm.product.created, plm.bom.updated, plm.document.released。订阅：erp.product.created, mes.work_order.completed。
