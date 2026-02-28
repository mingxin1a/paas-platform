# LIMS 细胞档案

**细胞代码**：lims | **领域**：智慧医疗  
**网关前缀**：/api/v1/lims | **注册服务名**：lims-cell | **监控维度**：lims.*

概述：实验室信息管理，样品/检测任务、检测结果、方法/标准、仪器/校准。经网关/注册中心/监控对接；跨细胞仅事件或异步 API。遵守数据主权与抗抵赖。事件域 lims。发布：lims.sample.registered, lims.result.approved, lims.certificate.issued。订阅：erp.order.created, wms.inbound.completed（按业务配置）。
