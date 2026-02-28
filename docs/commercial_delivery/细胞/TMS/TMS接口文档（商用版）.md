# TMS 接口文档（商用版）

**版本**：1.0 | **细胞**：TMS

## 访问与主要接口

- 经网关：`/api/v1/tms/<path>`。路径：/shipments、/vehicles、/drivers、/tracks、/delivery-confirm、/transport-costs、/reconciliations、/metrics 等。
- 司机信息接口返回脱敏；运单列表支持 owner_id 过滤。

**详细**：见 cells/tms 源码及《TMS与WMS对接手册》。
