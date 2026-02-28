# LIS 接口文档（商用版）

**版本**：1.0 | **细胞**：LIS

## 访问与主要接口

- 经网关：`/api/v1/lis/<path>`。路径：/test-requests、/samples、/results、/reports、/reports/<id>/review、/reports/<id>/audits 等。
- 样本/结果列表支持 technicianId/X-User-Id 过滤；报告审核写入审计。

**详细**：见 cells/lis 源码及《LIS检验报告规范》《LIS与HIS对接手册》。
