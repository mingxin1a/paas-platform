# MES 商用交付手册（工业版）

**版本**：1.0 | **细胞**：制造执行系统（MES）| **场景**：工业智能制造

## 1. 交付范围

本手册适用于 MES 细胞按「工业场景商用可交付」标准的交付验收与运维说明。MES 与 ERP/WMS 严格解耦，独立部署，仅通过 PaaS 层与 ERP/WMS 交互。

### 1.1 核心工业功能闭环

| 环节 | 说明 | 状态 |
|------|------|------|
| BOM 管理 | BOM 创建（含明细行 lines）、按产品查询、GET /boms/<id>/lines | 已实现 |
| 物料需求计算 | GET /production-orders/<id>/material-requirements 根据 BOM 计算物料需求 | 已实现 |
| 生产计划 | 计划创建、列表分页 | 已实现 |
| 生产订单 | 订单创建、状态更新（PATCH）、按车间过滤（X-Workshop-Id 数据权限） | 已实现 |
| 领料 | 领料单创建、领料执行（防超领） | 已实现 |
| 报工 | 单条/批量报工（支持 100+ 工序） | 已实现 |
| 质检 | 质检记录创建、按订单/批次查询 | 已实现 |
| 生产入库 | 生产入库登记、幂等、支持序列号（serialNumbers） | 已实现 |
| 生产追溯 | 按批次号/订单号/序列号追溯（GET /trace/serial/<sn>） | 已实现 |
| 审计日志 | GET /audit-logs 查询操作审计 | 已实现 |
| 批量导出 | GET /production-orders/export、/work-reports/export（CSV） | 已实现 |

### 1.2 工业适配

- **生产数据采集**：模拟设备对接（工序进度 _order_progress）；生产进度随报工实时更新。
- **产能统计**：/metrics 提供生产完成率、领料准确率、设备稼动率（模拟）。
- **数据安全**：生产工艺数据可加密存储（BOM 表 routing_encrypted）；生产订单数据权限（请求头 X-Workshop-Id，车间主任只看本车间订单）。
- **可靠性**：生产入库接口幂等；领料防超领（已领+本次≤应领）；生产异常（超领）返回商用提示「领料数量超过应领数量或领料单不存在」。
- **可运维**：MES 监控指标（生产完成率/领料准确率/设备稼动率）；操作日志留存≥1 年（MES_OPERATION_LOG_RETENTION_DAYS，默认 365）。

### 1.3 通用约束

- 细胞独立部署，仅通过 PaaS 与 ERP/MES/WMS 交互；接口支持 JSON（可选扩展 XML）。
- 操作日志留存≥1 年（模拟配置），符合工业数据留存要求。
- 接口设计遵循《接口设计说明书》；错误体 code/message/details/requestId。

## 2. 部署与配置

### 2.1 Docker 部署

```bash
# 构建
cd cells/mes && docker build -t mes-cell:latest .

# 运行
docker run -d -p 8006:8006 -e PORT=8006 mes-cell:latest

# 健康检查
curl http://localhost:8006/health
# 返回 {"status":"up","cell":"mes"}
```

### 2.2 环境变量

| 环境变量 | 说明 | 默认 |
|----------|------|------|
| PORT | 服务端口 | 8006 |
| MES_OPERATION_LOG_RETENTION_DAYS | 操作日志保留天数 | 365 |
| CELL_VERIFY_SIGNATURE | 网关验签 | 0 |

## 3. 数据备份（工业数据留存）

- 生产数据备份需符合工业数据留存要求；持久化落地后由运维配置每日/定期备份脚本。
- 当前为内存存储，商用需切换持久化并配置备份策略。

## 4. 接口清单（主要）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /health | 健康检查 |
| GET/POST | /boms | BOM 列表/创建（body 含 lines 明细） |
| GET | /boms/<id> | BOM 详情（含 lines） |
| GET | /boms/<id>/lines | BOM 明细行 |
| GET | /production-orders/<id>/material-requirements | 物料需求计算 |
| PATCH | /production-orders/<id> | 更新状态/完成 |
| GET | /trace/serial/<sn> | 按序列号追溯 |
| GET | /audit-logs | 审计日志 |
| GET | /production-orders/export | 生产订单导出 CSV |

通用请求头：X-Tenant-Id、X-Workshop-Id（车间权限）、X-Request-ID（幂等）。错误体含 code、message、details、requestId。

## 5. 交付物清单

- 本手册（MES商用交付手册（工业版）.md）
- 《MES车间操作指南》
- 《MES与ERP对接手册》
- 工业级测试报告（功能/性能/追溯性）
- database_schema.sql、Dockerfile、api_contract.yaml
