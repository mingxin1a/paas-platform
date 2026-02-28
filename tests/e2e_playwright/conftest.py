"""
Playwright E2E 公共配置：base_url 从 GATEWAY_URL 读取，未设置时跳过 E2E 或使用默认。
"""
import os
import pytest


def pytest_addoption(parser):
    parser.addoption("--e2e-base-url", default=os.environ.get("GATEWAY_URL", "http://localhost:8000"), help="E2E 网关/base URL")


@pytest.fixture(scope="session")
def base_url(request):
    return request.config.getoption("--e2e-base-url", default="http://localhost:8000").rstrip("/")


@pytest.fixture(scope="session")
def e2e_skip_if_no_host(request):
    """若 GATEWAY_URL 未设置或为占位，可标记跳过 E2E（CI 中可选运行）。"""
    url = os.environ.get("GATEWAY_URL", "").strip()
    if not url or url == "http://localhost:8000":
        # 仍运行，但测试内可检查连通性后 skip
        pass
    return url or "http://localhost:8000"
