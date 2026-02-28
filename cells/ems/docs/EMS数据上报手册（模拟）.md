# EMS 数据上报手册（模拟）

**版本**：1.0 | **细胞**：EMS

## 1. 上报数据来源

- 能耗采集：POST /consumption-records（meterId、value、unit、recordTime），头带 X-Request-ID 幂等。
- 统计结果：GET /stats?period=month&fromDate=&toDate= 可作月度/年度上报数据源。
- 导出数据：GET /export?fromDate=&toDate= 导出原始记录，用于监管报送（模拟）。

## 2. 模拟上报流程

1. 按监管要求确定上报周期（如月度）。
2. 调用 GET /export 或 GET /stats 获取对应周期数据。
3. 按监管格式转换后提交（具体格式由当地监管要求定义）；本细胞仅提供数据导出接口。

## 3. 安全与审计

- 导出操作记录审计日志；数据经 PaaS 网关访问，租户隔离。
