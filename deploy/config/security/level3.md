# 等保2.0三级适配基础配置

平台层中立治理，仅基础安全加固清单。身份鉴别：登录失败锁定、口令复杂度（AUTH_FAILURE_THRESHOLD、AUTH_PASSWORD_MIN_LENGTH）。访问控制：最小权限、GATEWAY_REQUIRE_TENANT_ID=1。安全审计：X-Trace-Id 透传、细胞人性化审计。入侵防范：CELL_VERIFY_SIGNATURE=1、参数校验。数据保密：HTTPS、敏感数据脱敏、备份见 backup_cells.sh。配置落位：环境变量与 K8s Secret，无业务逻辑。
