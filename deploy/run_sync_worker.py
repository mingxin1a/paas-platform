#!/usr/bin/env python3
"""
启动模块间业务联动 Worker。依赖：网关已启动（GATEWAY_URL）、事件总线可用（GET/POST /api/events）。
可选：DATALAKE_URL 用于同步至数据湖。联动开关见环境变量 LINK_*。
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from platform_core.sync_worker.worker import run_loop

if __name__ == "__main__":
    run_loop()
