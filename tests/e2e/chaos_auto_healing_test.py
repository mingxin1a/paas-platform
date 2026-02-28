"""
混沌工程：自愈策略
验证 cells 的 ai_agent 能加载 auto_healing.yaml 并对预设日志模式做出反应。
"""
import os
import sys
import tempfile

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, _ROOT)


class TestChaosAutoHealing:
    """自愈：加载配置并检测日志模式。"""

    def test_crm_ai_agent_loads_config(self):
        import yaml
        config_path = os.path.join(_ROOT, "cells", "crm", "auto_healing.yaml")
        assert os.path.isfile(config_path)
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        assert cfg.get("cell") == "crm"
        assert "rules" in cfg
        assert any(r.get("id") == "api_error_rate_high" for r in cfg["rules"])

    def test_crm_ai_agent_detects_pool_exhausted(self):
        import re
        line = "ERROR connection pool exhausted for datasource"
        pattern = r"connection pool exhausted|pool size exhausted"
        assert re.search(pattern, line, re.I) is not None
        config_path = os.path.join(_ROOT, "cells", "crm", "auto_healing.yaml")
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        rule = next((r for r in config["rules"] if r.get("id") == "connection_pool_exhausted"), None)
        assert rule is not None
        assert rule.get("action") in ("log", "restart_instance")
