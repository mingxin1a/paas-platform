#!/usr/bin/env sh
# SuperPaaS 统一入口：自检 / 全量验证 / 单细胞交付校验 / 进化周期
# 用法:
#   ./run.sh self_check          — 自检（等同 ./self_check.sh）
#   ./run.sh verify <CELL_NAME>  — 单细胞交付校验
#   ./run.sh evolution            — 执行一次进化周期
#   ./run.sh full_verify          — 全量验证（scripts/run_full_verification.py）
#   ./run.sh commercial_accept   — 商用验收一键全量校验（自检+批次1细胞交付）
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
CMD="${1:-self_check}"
case "$CMD" in
  self_check)
    exec "${ROOT}/scripts/self_check.sh" "${@:2}"
    ;;
  verify)
    exec "${ROOT}/scripts/verify_delivery.sh" "$2"
    ;;
  evolution)
    exec "${ROOT}/scripts/run_evolution_cycle.sh"
    ;;
  full_verify)
    exec python "${ROOT}/scripts/run_full_verification.py" "${@:2}"
    ;;
  commercial_accept)
    exec "${ROOT}/scripts/commercial_acceptance_verify.sh" "${@:2}"
    ;;
  *)
    echo "用法: $0 {self_check|verify <CELL>|evolution|full_verify|commercial_accept} [args...]"
    exit 1
    ;;
esac
