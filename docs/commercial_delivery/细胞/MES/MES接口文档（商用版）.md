# MES 接口文档（商用版）

**版本**：1.0 | **细胞**：MES

## 访问与主要接口

- 经网关：`/api/v1/mes/<path>`。路径：/boms、/production-plans、/production-orders、/material-issues、/work-reports、/production-inbounds、/metrics、/config/retention 等。
- 工单列表支持 X-Workshop-Id 过滤；入库支持幂等。

**详细**：见 cells/mes 源码及《MES与ERP对接手册》。
