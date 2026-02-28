# LIMS 接口文档（商用版）

**版本**：1.0 | **细胞**：LIMS

## 访问与主要接口

- 经网关：`/api/v1/lims/<path>`。路径：/samples、/results、/tasks、/experiment-data、/reports、/trace、/config/retention 等。
- 样品/任务列表支持 operatorId/X-User-Id 过滤；任务/数据/报告创建写入溯源。

**详细**：见 cells/lims 源码及《LIMS数据合规指南》《LIMS实验管理操作指南》。
