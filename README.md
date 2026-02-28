# SuperPaaS / paas-platform

多细胞 PaaS 平台：网关统一入口，业务以独立细胞（CRM、ERP、WMS、HRM、OA、MES、TMS、SRM、PLM、EMS、HIS、LIS、LIMS）形式接入，双端前端（客户端 + 管理端）经网关认证与路由访问细胞。

## 目录结构（简要）

| 目录 | 说明 |
|------|------|
| **cells/** | 业务细胞（每细胞独立 app、契约、交付包） |
| **platform_core/** | 平台核心：网关、熔断、注册/健康、监控、签名 |
| **frontend/** | 客户端前端（5173），按权限使用细胞 |
| **frontend-admin/** | 管理端前端（5174），细胞管理、用户/权限、审计 |
| **deploy/** | 网关启动、部署、监控、冒烟测试 |
| **evolution_engine/** | 自主进化与交付校验（verify_all_cells、单细胞 verify_delivery） |
| **glass_house/** | 透明化：ADR、演化日志、gap 分析、runbook |
| **docs/** | 设计说明书、宪法与合规、细胞档案 |
| **scripts/** | 自检、交付校验、进化周期、全量验证等脚本（主实现）；根目录保留兼容入口 |
| **tests/** | 平台级测试（健康、网关、E2E） |

完整目录树、请求流与入口说明见 **[docs/项目目录与架构说明.md](docs/项目目录与架构说明.md)**。

## 一键启动 / 快速上手

**环境**：Python 3.8+、Node 18+（前端）。

1. **启动网关**（端口 8000）：`python deploy/run_gateway.py`
2. **启动客户端**（5173）：`cd frontend && npm install && npm run dev`
3. **启动管理端**（5174）：`cd frontend-admin && npm install && npm run dev`
4. **登录**：Mock 用户 `admin/admin`、`client/123`、`operator/123`

**日常检查**：`./run.sh self_check` 或 `python scripts/self_check.py`（细胞合规性 + 平台健康度一键校验）。单细胞校验：`./run.sh verify crm`。批次1 商用验收：`python -m pytest tests/acceptance/test_batch1_commercial.py -v`。

文档导航：[docs/README.md](docs/README.md) · 逻辑全景图：[docs/超级PaaS平台逻辑全景图.md](docs/超级PaaS平台逻辑全景图.md) · 待补充项：[docs/待补充项清单.md](docs/待补充项清单.md)

**商用化**： [商用交付总手册](docs/commercial_delivery/超级PaaS平台商用交付总手册.md) | [商用验收清单](docs/commercial_delivery/通用/超级PaaS平台商用验收清单.md) | [批次1 商用验收测试用例](docs/commercial_delivery/批次1_商用验收测试用例.md) | [阶段1交付报告](docs/阶段1交付报告.md)  
**批次1 标准化交付包**：执行 `python scripts/build_batch1_delivery.py` 生成 `dist/batch1_commercial_*.zip`。
