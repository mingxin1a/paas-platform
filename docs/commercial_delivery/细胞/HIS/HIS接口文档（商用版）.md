# HIS 接口文档（商用版）

**版本**：1.0 | **细胞**：HIS

## 访问与主要接口

- 经网关：`/api/v1/his/<path>`。路径：/patients、/visits、/registration、/prescriptions、/charges、/charges/<id>/pay、/inpatients、/medical-records、/orders 等。
- 患者接口返回脱敏（姓名、身份证）；挂号/收费支持幂等；处方同就诊同内容返回 409。

**详细**：见 cells/his 源码及《HIS医疗数据合规指南》。
