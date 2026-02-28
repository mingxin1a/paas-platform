# ERP 细胞档案

**细胞代码**：erp | **领域**：智慧商业  
**网关前缀**：/api/v1/erp | **注册服务名**：erp-cell | **监控维度**：erp.*

概述：企业资源计划，订单、合同、产品、财务单据。与平台经网关/注册中心/监控对接；跨细胞仅事件或异步 API。遵守《01_核心法律》第七部分与《接口设计说明书》。

事件域：`erp`。发布：erp.order.created, erp.contract.signed, erp.product.created。订阅：wms.stock.updated, crm.opportunity.closed, srm.purchase.order.created。
