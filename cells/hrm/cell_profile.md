# HRM 细胞档案

**细胞代码**：hrm | **领域**：人力资源  
**网关前缀**：/api/v1/hrm | **注册服务名**：hrm-cell | **监控维度**：hrm.*

概述：人力资源管理系统（对标 OrangeHRM 等开源 HRM 的通用能力，用 SuperPaaS 架构重写）。员工、部门、请假、考勤、招聘等；经网关/注册中心/监控对接；跨细胞仅事件或异步 API。事件域 `hrm`。发布：hrm.employee.created, hrm.leave.submitted。订阅：oa.task.completed（示例）。
