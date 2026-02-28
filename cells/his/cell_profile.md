# HIS 细胞档案

**细胞代码**：his | **领域**：智慧医疗  
**网关前缀**：/api/v1/his | **注册服务名**：his-cell | **监控维度**：his.*

概述：医院信息系统，患者/就诊、医嘱/处方、挂号/收费。经网关/注册中心/监控对接；跨细胞仅事件或异步 API。遵守数据主权（宪法修正案#4）、抗抵赖与验签（#5）。事件域 his。发布：his.patient.registered, his.visit.started, his.order.created。订阅：lis.sample.received, lis.result.reported。
