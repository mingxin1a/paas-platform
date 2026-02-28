#!/usr/bin/env python3
"""ERP 细胞管家式 AI：监控日志，自动处理预设异常。"""
import os, re, sys, logging, subprocess
from pathlib import Path
CELL_NAME = "erp"
CONFIG_PATH = Path(__file__).parent / "auto_healing.yaml"
LOG_PATTERNS = [(r"connection pool exhausted|pool size exhausted", "connection_pool_exhausted"), (r"timeout|timed out", "timeout"), (r"OutOfMemoryError|MemoryError", "oom"), (r"too many connections", "too_many_connections")]
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(f"{CELL_NAME}.ai_agent")

def load_healing_config():
    try:
        import yaml
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    except Exception: pass
    return {}

def handle_detected(rule_id, line, config):
    for r in config.get("rules", []):
        if r.get("id") != rule_id: continue
        action = r.get("action", "log")
        logger.warning("rule=%s action=%s cell=%s", rule_id, action, CELL_NAME)
        if action == "restart_instance" and os.environ.get("SUPPAAS_AUTO_HEAL_RESTART") == "1":
            subprocess.run(r.get("restart_command", "echo restart"), shell=True, timeout=30)
        break

def tail_and_scan(log_path=None):
    config = load_healing_config()
    if log_path and os.path.isfile(log_path):
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            f.seek(0, 2)
            while True:
                line = f.readline()
                if not line: import time; time.sleep(1); continue
                for pattern, rule_id in LOG_PATTERNS:
                    if re.search(pattern, line, re.I): handle_detected(rule_id, line, config); break
    else:
        for line in sys.stdin:
            for pattern, rule_id in LOG_PATTERNS:
                if re.search(pattern, line, re.I): handle_detected(rule_id, line, config); break

if __name__ == "__main__":
    tail_and_scan(os.environ.get("CELL_LOG_PATH"))
