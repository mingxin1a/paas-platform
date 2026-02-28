# scripts/ — 脚本与校验入口

本目录集中存放**运行、自检、交付校验**等脚本，根目录保留兼容入口（转发到本目录）。

| 脚本 | 用途 |
|------|------|
| **self_check.sh** / **self_check.py** | 一键自检：PaaS 健康、网关路由、双端前端、细胞合规、文档一致性、全细胞交付校验、pytest |
| **verify_delivery.sh** | 单细胞交付校验，用法：`./scripts/verify_delivery.sh <CELL_NAME>` |
| **run_evolution_cycle.sh** | 执行一次自主进化周期（可被 cron 调用） |
| **run_full_verification.py** | 全量验证：环境、PaaS 合规、细胞接入、接口规范、冒烟测试 |
| **weekly_benchmark_scan.sh** | 周基准扫描 |

**从项目根执行**：使用统一入口 `./run.sh self_check`、`./run.sh verify crm`、`./run.sh evolution`，或直接执行本目录下对应脚本。
