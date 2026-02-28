#!/usr/bin/env python3
"""
CRM 细胞管家式 AI
监控本细胞日志，自动处理预设异常（如数据库连接池耗尽）。
启动后连接 PaaS 监控中心，注册并轮询指令，按 auto_healing.yaml 执行自愈。
《01_核心法律》3.1 管家式 AI；零心智负担：开箱即用。
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

CELL_NAME = "crm"
CONFIG_PATH = Path(__file__).parent / "auto_healing.yaml"
LOG_PATTERNS = [
    (r"connection pool exhausted|pool size exhausted", "connection_pool_exhausted"),
    (r"timeout|timed out", "timeout"),
    (r"OutOfMemoryError|MemoryError", "oom"),
    (r"too many connections", "too_many_connections"),
]

# 监控中心 URL（部署时由 env 注入，如 http://monitor:9000 或 http://localhost:9000）
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
    """根据规则执行动作：log / alert / restart。"""
    rules = config.get("rules", [])
    for r in rules:
        if r.get("id") != rule_id:
            continue
        action = r.get("action", "log")
        logger.warning("rule=%s action=%s cell=%s snippet=%s", rule_id, action, CELL_NAME, line[:200])
        if action == "restart_instance" and os.environ.get("SUPPAAS_AUTO_HEAL_RESTART") == "1":
            cmd = r.get("restart_command", "echo 'restart placeholder'")
            subprocess.run(cmd, shell=True, timeout=30)
        break


def execute_instruction(inst: dict, config: dict) -> None:
    """执行来自监控中心的指令，按 auto_healing.yaml 规则执行（如 restart_instance）。"""
    rule_id = inst.get("id", "")
    action = inst.get("action", "log")
    params = inst.get("params", {})
    logger.info("executing instruction id=%s action=%s params=%s", rule_id, action, params)
    rules = config.get("rules", [])
    for r in rules:
        if r.get("id") != rule_id:
            continue
        if action == "restart_instance":
            if os.environ.get("SUPPAAS_AUTO_HEAL_RESTART") == "1":
                cmd = r.get("restart_command", "echo 'restart crm-cell'")
                subprocess.run(cmd, shell=True, timeout=30)
            else:
                logger.warning("restart_instance skipped (SUPPAAS_AUTO_HEAL_RESTART != 1)")
        break
    else:
        if action == "restart_instance":
            subprocess.run("echo 'restart crm-cell'", shell=True, timeout=10)


def _monitor_loop(agent_id: str) -> None:
    """后台线程：向监控中心注册，周期性拉取指令并执行、可选心跳。"""
    if not MONITOR_CENTER_URL:
        logger.info("MONITOR_CENTER_URL not set, skip monitor loop")
        return
    base = MONITOR_CENTER_URL.rstrip("/")
    # 注册
    try:
        req = urllib.request.Request(
            f"{base}/register",
            data=json.dumps({"cell": CELL_NAME, "agent_id": agent_id}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            logger.info("registered with monitor: %s", r.read().decode()[:200])
    except Exception as e:
        logger.warning("register failed: %s", e)
        return
    config = load_healing_config()
    last_heartbeat = 0
    while True:
        time.sleep(POLL_INTERVAL)
        try:
            # 拉取指令
            req = urllib.request.Request(f"{base}/instructions?cell={CELL_NAME}&agent_id={agent_id}")
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode())
            for inst in data.get("instructions", []):
                execute_instruction(inst, config)
            # 可选心跳
            if time.time() - last_heartbeat >= HEARTBEAT_INTERVAL:
                last_heartbeat = time.time()
                req = urllib.request.Request(
                    f"{base}/heartbeat",
                    data=json.dumps({"cell": CELL_NAME, "agent_id": agent_id}).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                urllib.request.urlopen(req, timeout=5)
        except urllib.error.HTTPError as e:
            logger.debug("instructions/heartbeat error: %s", e)
        except Exception as e:
            logger.debug("monitor poll: %s", e)


def tail_and_scan(log_path: str = None) -> None:
    config = load_healing_config()
    if log_path and os.path.isfile(log_path):
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            f.seek(0, 2)
            while True:
                line = f.readline()
                if not line:
                    import time
                    time.sleep(1)
                    continue
                for pattern, rule_id in LOG_PATTERNS:
                    if re.search(pattern, line, re.I):
                        handle_detected(rule_id, line, config)
                        break
    else:
        for line in sys.stdin:
            for pattern, rule_id in LOG_PATTERNS:
                if re.search(pattern, line, re.I):
                    handle_detected(rule_id, line, config)
                    break


if __name__ == "__main__":
    agent_id = os.environ.get("HOSTNAME", "crm-agent-local")
    if MONITOR_CENTER_URL:
        t = threading.Thread(target=_monitor_loop, args=(agent_id,), daemon=True)
        t.start()
    tail_and_scan(os.environ.get("CELL_LOG_PATH"))
