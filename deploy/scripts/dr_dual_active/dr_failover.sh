#!/usr/bin/env sh
# 故障切换：主站不可用时在灾备站执行，切换流量至灾备站（需配合 DNS/SLB/Ingress 配置）
# 用法: 在灾备节点执行 DR_SITE_ID=dr ./dr_failover.sh
# 前置: 已从 S3 拉取最新备份并完成 restore_full.sh，网关/治理/细胞已启动
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
[ -f "${SCRIPT_DIR}/env.example" ] && . "${SCRIPT_DIR}/env.example" 2>/dev/null || true
DR_SITE_ID="${DR_SITE_ID:-dr}"

echo "[dr-failover] 灾备切换: DR_SITE_ID=$DR_SITE_ID"
echo "[dr-failover] 请确认: 1) 备份已恢复 2) 本节点服务已启动 3) 健康检查通过"
echo "[dr-failover] 切换方式: 将 DNS 或 SLB/Ingress 指向本节点网关地址，或更新 K8s Ingress 后端"
echo "[dr-failover] 示例: 修改 DNS 记录将 paas.example.com 解析至本节点 IP"
echo "[dr-failover] 完成切换后请记录切换时间并通知运维。"

# 可选：写入切换标记，供监控或自动化识别
MARKER_FILE="${SCRIPT_DIR}/../backup/.dr_failover_marker"
mkdir -p "$(dirname "$MARKER_FILE")"
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) DR_SITE_ID=$DR_SITE_ID failover" >> "$MARKER_FILE"
echo "[dr-failover] 已写入切换标记: $MARKER_FILE"
exit 0
