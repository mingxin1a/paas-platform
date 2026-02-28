#!/usr/bin/env python3
"""启动治理中心服务：注册发现、健康巡检、链路与 RED 指标 API。"""
import os
import sys
import logging

sys.path.insert(0, os.environ.get("APP_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
logging.basicConfig(level=logging.INFO)

from platform_core.core.governance.app import app, _seed_from_env, _start_health_loop

_seed_from_env()
_start_health_loop()
port = int(os.environ.get("GOVERNANCE_PORT", "8005"))
app.run(host="0.0.0.0", port=port)
