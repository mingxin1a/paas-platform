# TMS 商用交付手册（物流版）

**版本**：1.0 | **细胞**：运输管理系统（TMS）| **场景**：工业物流

## 1. 交付范围

本手册适用于 TMS 细胞按「工业场景商用可交付」标准的交付验收与运维说明。TMS 与 WMS/ERP 严格解耦，独立部署，仅通过 PaaS 层与 WMS 等交互。

### 1.1 核心工业功能

| 能力 | 说明 | 状态 |
|------|------|------|
| 运输订单 | 运单 CRUD、车辆/司机分配（PATCH vehicleId/driverId）、状态流转、行级权限（X-User-Id） | 已实现 |
| 车辆管理 | 车辆列表、创建 | 已实现 |
| 司机管理 | 司机列表、创建；手机号/身份证脱敏展示 | 已实现 |
| 运输轨迹 | 轨迹记录、按运单查询（模拟） | 已实现 |
| 到货确认 | 到货确认、运单状态更新 | 已实现 |
| 运输费用 | 费用登记、结算（POST /transport-costs/<id>/settle）、status draft/settled | 已实现 |
| 物流对账 | 对账单创建、确认（/confirm）、完成（/complete）、status draft/confirmed/completed | 已实现 |
| 批量导入/导出 | 运单批量导入（≤500 条）、运单/费用 CSV 导出 | 已实现 |
| 审计日志 | GET /audit-logs | 已实现 |

### 1.2 数据安全与可运维

- **数据安全**：司机手机号/身份证加密存储（Schema 支持 phone_encrypted、id_no_encrypted）；接口返回脱敏（138****5678 等）。运输订单数据权限：请求头 X-User-Id 时仅返回该负责人订单。
- **可靠性**：运输订单创建幂等（X-Request-ID）；到货确认时运单不存在返回「运单不存在，无法对不存在的运单做到货确认」。
- **可运维**：/metrics 提供 shipmentOnTimeRatePct（模拟）、totalShipments、confirmedShipments、totalTransportCostCents；运输数据备份由持久化与运维配置。

## 2. 部署与配置

### 2.1 Docker 部署

```bash
cd cells/tms && docker build -t tms-cell:latest .
docker run -d -p 8007:8007 -e PORT=8007 tms-cell:latest
curl http://localhost:8007/health
```

### 2.2 环境变量

| 环境变量 | 说明 | 默认 |
|----------|------|------|
| PORT | 服务端口 | 8007 |
| CELL_VERIFY_SIGNATURE | 网关验签 | 0 |

## 3. 接口清单（主要）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /health | 健康检查 |
| PATCH | /shipments/<id> | 更新运单（status、vehicleId、driverId） |
| POST | /transport-costs/<id>/settle | 运费结算 |
| POST | /reconciliations/<id>/confirm | 对账确认 |
| POST | /reconciliations/<id>/complete | 对账完成 |
| GET | /audit-logs | 审计日志 |
| GET | /shipments/export | 运单导出 CSV |
| GET | /transport-costs/export | 运输费用导出 CSV |

通用请求头：X-Tenant-Id、X-User-Id（物流专员行级权限）。

## 4. 交付物清单

- 本手册（TMS商用交付手册（物流版）.md）
- 《TMS物流管理员操作指南》
- 《TMS与WMS对接手册》
- 工业级测试报告（功能/性能/追溯性）
- database_schema.sql、Dockerfile、api_contract.yaml
