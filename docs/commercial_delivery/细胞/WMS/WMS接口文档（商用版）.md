# WMS 接口文档（商用版）

**版本**：1.0 | **细胞**：WMS

## 访问与主要接口

- 经网关：`/api/v1/wms/<path>`。路径：/inventory、/inbound/receive、/outbound/ship、/transfers、/cycle-count、/freeze、/expiry-alerts、/scan/inbound、/scan/outbound、/metrics 等。
- 入库/出库支持 idempotentKey；防负库存返回商用错误。

**详细**：见 cells/wms 源码及《WMS与ERP-MES对接手册》。
