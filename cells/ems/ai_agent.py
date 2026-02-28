#!/usr/bin/env python3
"""EMS 细胞管家式 AI。"""
import os, re, sys, logging, subprocess
from pathlib import Path
CELL_NAME, CONFIG_PATH = "ems", Path(__file__).parent / "auto_healing.yaml"
LOG_PATTERNS = [(r"connection pool exhausted", "connection_pool_exhausted"), (r"timeout|timed out", "timeout"), (r"OutOfMemoryError", "oom")]
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(f"{CELL_NAME}.ai_agent")
def load_healing_config():
    try:
        import yaml
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r", encoding="utf-8") as f: return yaml.safe_load(f) or {}
    except Exception: pass
    return {}
def handle_detected(rule_id, line, config):
    for r in config.get("rules", []):
        if r.get("id") != rule_id: continue
        if r.get("action") == "restart_instance" and os.environ.get("SUPPAAS_AUTO_HEAL_RESTART") == "1":
            subprocess.run(r.get("restart_command", "echo restart"), shell=True, timeout=30)
        logger.warning("rule=%s cell=%s", rule_id, CELL_NAME); break
def tail_and_scan(log_path=None):
    c = load_healing_config()
    src = open(log_path, "r", encoding="utf-8", errors="ignore") if log_path and os.path.isfile(log_path) else sys.stdin
    if hasattr(src, "seek"): src.seek(0, 2)
    while True:
        line = src.readline() if hasattr(src, "readline") else (src.read() or "")
        if not line: import time; time.sleep(1); continue
        for pat, rid in LOG_PATTERNS:
            if re.search(pat, line, re.I): handle_detected(rid, line, c); break
        if src is sys.stdin: break
if __name__ == "__main__": tail_and_scan(os.environ.get("CELL_LOG_PATH"))
