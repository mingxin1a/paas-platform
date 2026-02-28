# WMS 商用交付手册（仓储版）

**版本**：1.0 | **细胞**：仓库管理系统（WMS）| **场景**：工业仓储

## 1. 交付范围

本手册适用于 WMS 细胞按「工业场景商用可交付」标准的交付验收与运维说明。WMS 与 ERP/MES 严格解耦，独立部署，仅通过 PaaS 层交互。

### 1.1 核心工业功能

| 能力 | 说明 | 状态 |
|------|------|------|
| 库位管理 | 库位 CRUD、按仓库查询 | 已实现 |
| 入库 | typeCode：purchase/production/return；收货、幂等、支持序列号 | 已实现 |
| 出库 | typeCode：sales/picking/transfer；发货、防负库存、幂等 | 已实现 |
| 调拨 | 跨仓调拨、幂等 | 已实现 |
| 盘点 | 单次/批量盘点（支持 1000+ 物料） | 已实现 |
| 库存预警 | 效期预警 /alerts/expiry；安全库存预警 /alerts/stock | 已实现 |
| 批次/序列号追溯 | 批次列表、FIFO、GET /trace/serial/<sn> 序列号追溯 | 已实现 |
| 安全库存 | POST /safety-stock 设置；用于库存预警 | 已实现 |
| 扫码出入库 | /scan/inbound、/scan/outbound | 已实现 |
| 库存冻结/解冻 | 冻结、解冻接口 | 已实现 |
| 审计日志 | GET /audit-logs | 已实现 |
| 批量导出 | GET /inbound-orders/export、/outbound-orders/export（CSV） | 已实现 |

### 1.2 数据安全与可运维

- **数据安全**：库存数据可加密存储（应用层/KMS）；库位权限（location_permission 表，库管员仅操作指定库位）由权限服务扩展。
- **出入库日志**：人性化审计，可审计。
- **可靠性**：出入库收货/发货支持幂等；库存操作防负库存；效期预警 GET /alerts/expiry。
- **监控**：/metrics 提供 transferCount、cycleCountTotal、expiryAlertCount。
- **备份**：库存数据定时备份（每日）由持久化与运维脚本配置。

## 2. 部署与配置

### 2.1 Docker 部署

```bash
cd cells/wms && docker build -t wms-cell:latest .
docker run -d -p 8003:8003 -e PORT=8003 wms-cell:latest
curl http://localhost:8003/health
```

### 2.2 环境变量

| 环境变量 | 说明 | 默认 |
|----------|------|------|
| PORT | 服务端口 | 8003 |
| CELL_VERIFY_SIGNATURE | 网关验签 | 0 |

## 3. 接口清单（主要）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /health | 健康检查 |
| POST | /inbound-orders | 创建入库单（body.typeCode: purchase/production/return） |
| POST | /outbound-orders | 创建出库单（body.typeCode: sales/picking/transfer） |
| GET | /alerts/stock | 库存预警（低于安全库存） |
| POST | /safety-stock | 设置安全库存 |
| GET | /trace/serial/<sn> | 序列号追溯 |
| GET | /audit-logs | 审计日志 |
| GET | /inbound-orders/export | 入库单导出 CSV |
| GET | /outbound-orders/export | 出库单导出 CSV |

通用请求头：X-Tenant-Id、X-Warehouse-Id（仓库权限）。

## 4. 交付物清单

- 本手册（WMS商用交付手册（仓储版）.md）
- 《WMS库管员操作指南》
- 《WMS与ERP/MES对接手册》
- 工业级测试报告（功能/性能/追溯性）
- database_schema.sql、Dockerfile、api_contract.yaml
