"""
网关路由配置单元测试：load_routes、文件解析、环境变量。
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from platform_core.core.gateway import config as gateway_config


def test_load_routes_from_env(monkeypatch):
    monkeypatch.setenv("CELL_CRM_URL", "http://crm:5001")
    monkeypatch.setenv("CELL_ERP_URL", "http://erp:5002")
    monkeypatch.setattr(gateway_config, "CONFIG_PATH", "")  # 避免文件覆盖
    routes = gateway_config.load_routes()
    assert "crm" in routes and routes["crm"] == "http://crm:5001"
    assert "erp" in routes and routes["erp"] == "http://erp:5002"


def test_cell_from_route_item():
    from platform_core.core.gateway.config import _cell_from_route_item
    assert _cell_from_route_item({"id": "cell-crm", "upstream": "http://crm:5001"}) == "crm"
    assert _cell_from_route_item({"path_prefix": "/api/cells/erp", "upstream": "http://erp:5002"}) == "erp"
    assert _cell_from_route_item({"id": "erp", "upstream": "http://erp:5002"}) == "erp"


def test_load_routes_from_json_file(monkeypatch):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"routes": {"crm": "http://crm:5001", "erp": "http://erp:5002"}}, f)
        path = f.name
    try:
        monkeypatch.setattr(gateway_config, "CONFIG_PATH", path)
        for k in list(os.environ.keys()):
            if k.startswith("CELL_") and k.endswith("_URL"):
                monkeypatch.delenv(k, raising=False)
        routes = gateway_config._load_routes_from_file(path)
        assert "crm" in routes and routes["crm"] == "http://crm:5001"
        assert "erp" in routes and routes["erp"] == "http://erp:5002"
    finally:
        os.unlink(path)


def test_load_routes_from_yaml_file():
    try:
        import yaml
    except ImportError:
        pytest.skip("PyYAML not installed")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        yaml.dump({
            "routes": [
                {"id": "cell-crm", "upstream": "http://crm:5001"},
                {"path_prefix": "/api/cells/erp", "upstream": "http://erp:5002"},
            ]
        }, f)
        path = f.name
    try:
        routes = gateway_config._load_routes_from_file(path)
        assert "crm" in routes
        assert "erp" in routes
    finally:
        os.unlink(path)
