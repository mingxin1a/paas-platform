"""
PaaS 核心层单元测试公共 fixture：路径与网关 app。
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


@pytest.fixture
def gateway_app():
    """创建网关 Flask 应用（使用内存 session、无真实细胞）。"""
    from platform_core.core.gateway.app import create_app
    # 无路由时 resolver 返回 None，代理会 503，仅测认证与静态
    app = create_app(registry_resolver=lambda c: None, use_dynamic_routes=True)
    app.config["TESTING"] = True
    return app


@pytest.fixture
def gateway_client(gateway_app):
    """网关测试客户端。"""
    with gateway_app.test_client() as c:
        yield c
