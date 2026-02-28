#!/usr/bin/env bash
# 安全扫描门禁：Bandit（Python SAST）+ Safety（依赖漏洞）
# 高危/严重漏洞时返回非零，供 CI 或本地门禁阻断。
# 用法：./scripts/security_scan.sh [项目根目录，默认 .]
set -e
ROOT="${1:-.}"
cd "$ROOT"
echo "[security] Bandit (Python SAST, severity >= HIGH)..."
pip install -q bandit
bandit -r platform_core cells -s HIGH -x '*/tests/*','*/venv/*','*/.venv/*' -q
echo "[security] Safety (dependency vulnerabilities)..."
pip install -q safety
safety check
echo "[security] All checks passed."
