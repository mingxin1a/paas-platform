#!/usr/bin/env python3
"""
HRM 细胞管家式 AI - 监控日志、连接监控中心、按 auto_healing.yaml 自愈。
《01_核心法律》3.1 管家式 AI。对标 OrangeHRM 能力，架构遵循 SuperPaaS。
"""
import os
import re
import sys
import json
import time
import logging
import subprocess
import threading
import urllib.request
import urllib.error
from pathlib import Path

CELL_NAME = "hrm"
CONFIG_PATH = Path(__file__).parent / "auto_healing.yaml"
LOG_PATTERNS = [
    (r"connection pool exhausted|pool size exhausted", "connection_pool_exhausted"),
    (r"timeout|timed out", "timeout"),
    (r"OutOfMemoryError|MemoryError", "oom"),
]
MONITOR_CENTER_URL = os.environ.get("MONITOR_CENTER_URL") or os.environ.get("MONITOR_URL", "")
POLL_INTERVAL = int(os.environ.get("SUPPAAS_INSTRUCTION_POLL_SEC", "15"))
HEARTBEAT_INTERVAL = int(os.environ.get("SUPPAAS_HEARTBEAT_SEC", "30"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(f"{CELL_NAME}.ai_agent")


def load_healing_config():
    try:
        import yaml
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    except Exception:
        pass
    return {}


def handle_detected(rule_id: str, line: str, config: dict) -> None:
    rules = config.get("rules", [])
    for r in rules:
        if r.get("id") != rule_id:
            continue
        action = r.get("action", "log")
        logger.warning("rule=%s action=%s cell=%s", rule_id, action, CELL_NAME)
        if action == "restart_instance" and os.environ.get("SUPPAAS_AUTO_HEAL_RESTART") == "1":
            cmd = r.get("restart_command", "echo 'restart hrm-cell'")
            subprocess.run(cmd, shell=True, timeout=30)
        break


def _monitor_loop(agent_id: str) -> None:
    if not MONITOR_CENTER_URL:
        return
    base = MONITOR_CENTER_URL.rstrip("/")
    try:
        req = urllib.request.Request(
            f"{base}/register",
            data=json.dumps({"cell": CELL_NAME, "agent_id": agent_id}).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        logger.warning("register failed: %s", e)
        return
    while True:
        time.sleep(POLL_INTERVAL)
        try:
            urllib.request.urlopen(f"{base}/instructions?cell={CELL_NAME}&agent_id={agent_id}", timeout=10)
        except Exception:
            pass


if __name__ == "__main__":
    agent_id = os.environ.get("HOSTNAME", "hrm-agent-local")
    if MONITOR_CENTER_URL:
        t = threading.Thread(target=_monitor_loop, args=(agent_id,), daemon=True)
        t.start()
    if os.environ.get("CELL_LOG_PATH") and os.path.isfile(os.environ["CELL_LOG_PATH"]):
        with open(os.environ["CELL_LOG_PATH"], "r", encoding="utf-8", errors="ignore") as f:
            f.seek(0, 2)
            while True:
                line = f.readline()
                if not line:
                    time.sleep(1)
                    continue
                config = load_healing_config()
                for pattern, rule_id in LOG_PATTERNS:
                    if re.search(pattern, line, re.I):
                        handle_detected(rule_id, line, config)
                        break
    else:
        logger.info("HRM ai_agent running (no log file); monitor_loop active if MONITOR_CENTER_URL set")
