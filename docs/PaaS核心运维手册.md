# PaaS 核心运维手册

## 1. 部署

- 网关默认端口 8000；USE_REAL_FORWARD=1 真实转发。
- 细胞通过 CELL_<NAME>_URL 或路由表注册。
- glass_house 需可写（审计、健康报告）。

## 2. 环境变量（网关）

- GATEWAY_PORT, GATEWAY_SIGNING_SECRET
- GATEWAY_RATE_LIMIT_ENABLED, GATEWAY_RATE_LIMIT_IP_PER_MIN
- GATEWAY_APP_KEYS 或 GATEWAY_APP_KEY（可选）
- SUPERPAAS_ROOT, GOVERNANCE_URL

## 3. 健康与自检

- GET /health；细胞 GET /api/v1/<cell>/health
- python scripts/self_check.py -> glass_house/health_report.json

## 4. 审计

- operation_audit.log 仅追加；GET /api/admin/audit-logs 检索，/api/admin/audit-logs/export 导出。

## 5. 事件总线

- POST /api/events 发布，GET /api/events 拉取。
