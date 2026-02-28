#!/usr/bin/env bash
# 主备切换示例脚本（仅供预案参考，实际 VIP/DNS 由 Keepalived 或云厂商 SLB 负责）
# 用途：文档化切换步骤；生产需按实际环境修改并纳入变更流程

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "[failover] Example failover script - customize for your env"

# 示例：若使用 Keepalived，备机提升为主通常由 Keepalived 自动完成（主机 /health 失败后 VIP 漂移）
# 示例：若使用 K8s，多副本 + Service 已实现无单点，无需本脚本
# 示例：若使用云 SLB，将后端从主机组切换到备机组需在控制台或 API 完成

echo "[failover] 1. 确认当前网关健康：curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/health"
echo "[failover] 2. 若主站点不可用，在容灾站点执行：启动网关与治理中心，并切换 DNS 或 SLB 指向容灾站点"
echo "[failover] 3. 数据双活：会话存储使用 Redis 主从/集群后，多活网关共享同一 Redis，无需本脚本做会话迁移"
exit 0
