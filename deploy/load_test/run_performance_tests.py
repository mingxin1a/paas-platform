#!/usr/bin/env python3
"""
性能测试执行入口：基准 / 负载 / 压力 / 稳定性。
依赖：pip install locust
用法:
  python run_performance_tests.py baseline   # 基准 10 用户 5 分钟
  python run_performance_tests.py load       # 负载 100->300->500 阶梯
  python run_performance_tests.py stress      # 压力 500->1000 找拐点
  python run_performance_tests.py stability  # 稳定性 200 用户 72 小时
  GATEWAY_URL=http://your-gateway:8000 python run_performance_tests.py baseline
"""
from __future__ import annotations

import os
import subprocess
import sys

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8000")
LOCUST_FILE = os.path.join(os.path.dirname(__file__), "locustfile.py")


def run_locust(users: int, spawn_rate: int, duration: str, headless: bool = True, extra: list | None = None):
    cmd = [
        sys.executable, "-m", "locust",
        "-f", LOCUST_FILE,
        "--host", GATEWAY_URL.rstrip("/"),
        "-u", str(users),
        "-r", str(spawn_rate),
        "-t", duration,
    ]
    if headless:
        cmd.append("--headless")
    if extra:
        cmd.extend(extra)
    env = os.environ.copy()
    env["GATEWAY_URL"] = GATEWAY_URL
    return subprocess.run(cmd, env=env)


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_performance_tests.py <baseline|load|stress|stability>")
        sys.exit(1)
    mode = sys.argv[1].lower()

    if mode == "baseline":
        # 基准：10 用户，5 分钟
        sys.exit(run_locust(10, 5, "5m").returncode)
    if mode == "load":
        # 负载：100 用户，10 分钟（可手动分多轮 100->300->500）
        sys.exit(run_locust(100, 10, "10m").returncode)
    if mode == "stress":
        # 压力：500 用户，15 分钟
        sys.exit(run_locust(500, 25, "15m").returncode)
    if mode == "stability":
        # 稳定性：200 用户，72 小时
        sys.exit(run_locust(200, 5, "72h").returncode)
    print("Unknown mode. Use: baseline | load | stress | stability")
    sys.exit(1)


if __name__ == "__main__":
    main()
