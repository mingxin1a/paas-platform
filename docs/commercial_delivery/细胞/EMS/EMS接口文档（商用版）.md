# EMS 接口文档（商用版）

**版本**：1.0 | **细胞**：EMS

## 访问与主要接口

- 经网关：`/api/v1/ems/<path>`。路径：/consumption-records（GET/POST）、/stats?period=day|week|month|year、/alerts、/export、/config/retention。
- 采集 POST 支持 X-Request-ID 幂等。

**详细**：见 cells/ems 源码及《EMS能耗合规指南》。
