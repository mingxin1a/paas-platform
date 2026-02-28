import os
import pytest


@pytest.fixture(scope="session")
def gateway_url():
    """E2E 测试使用的网关地址，默认本仓库网关端口 8000。"""
    return os.environ.get("GATEWAY_URL", "http://localhost:8000").rstrip("/")
