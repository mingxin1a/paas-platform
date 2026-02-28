# ERP 测试报告（商用级）

**版本**：1.0 | **细胞**：ERP | **测试类型**：功能、接口、幂等、错误格式

## 1. 测试环境

- 细胞：ERP（Flask），端口 8002
- 请求头：X-Tenant-Id、X-Request-ID（POST）、Authorization（按环境配置）

## 2. 测试范围

| 模块 | 用例类型 | 说明 |
|------|----------|------|
| 健康检查 | 接口 | GET /health 返回 200，body 含 status、cell |
| 订单 | CRUD、幂等、软删除 | POST 幂等、DELETE 软删除、错误体格式 |
| GL | 科目、分录、过账、余额 | 创建、列表、过账、余额查询 |
| AR/AP | 发票 CRUD、幂等 | 创建、列表、详情、软删除、幂等 |
| MM | 物料、采购订单 CRUD、幂等 | 同上 |
| PP | BOM、工单 CRUD、幂等 | 同上 |
| 错误格式 | 统一错误体 | 404/400/409 返回 code、message、details、requestId |
| 审计 | 人性化审计 | 写操作有审计日志（谁、何时、何操作、trace_id） |

## 3. 通过标准（商用级）

- 所有 POST 写操作支持 X-Request-ID 幂等：同一 request_id 二次提交返回 409 或返回已创建资源。
- 所有错误响应为 JSON，且包含 code、message、requestId；业务错误含 details。
- 列表接口支持分页（page、pageSize），返回 data、total。
- 软删除接口（DELETE）不物理删除，可查询时过滤已删除数据。
- /health 可用于网关健康巡检。

## 4. 测试结果记录（示例）

| 用例 | 预期 | 结果 |
|------|------|------|
| GET /health | 200, cell=erp | 待执行 |
| POST /orders 幂等 | 201 首次，409 或 200 重复 | 待执行 |
| POST /orders 缺参 | 400，VALIDATION_ERROR | 待执行 |
| GET /orders?page=1&pageSize=20 | 200，data、total | 待执行 |
| GL 过账 | 200，状态变为已过账 | 待执行 |
| AR/AP 创建 | 201，幂等 | 待执行 |

（实际执行时请填写日期、执行人、通过/失败及备注。）

## 5. 遗留与建议

- 当前为内存存储，重启数据丢失；商用需切换持久化并做备份与高可用。
- 监控指标（/metrics）可后续增加：采购订单量、库存周转率、应收账龄等，与 PaaS 监控打通。
