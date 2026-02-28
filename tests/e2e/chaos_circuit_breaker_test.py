"""
混沌工程：熔断器
《接口设计说明书》3.3.1：10 秒内异常率 ≥ 50% 时断路器开启，请求返回 503。
"""
import os
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, _ROOT)

from platform_core.core.registry.client import RegistryClient
from platform_core.core.gateway.app import create_app
from platform_core.core.gateway.circuit_breaker import CircuitBreakerRegistry

try:
    from flask import Flask
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False


@pytest.fixture(scope="module")
def registry():
    r = RegistryClient()
    r.register("chaos_cell", "http://chaos-cell:9999")
    return r


@pytest.fixture(scope="module")
def breakers():
    return CircuitBreakerRegistry()


@pytest.fixture(scope="module")
def gateway_app(registry, breakers):
    if not HAS_FLASK:
        pytest.skip("flask not installed")
    return create_app(registry_resolver=registry.resolve, monitor_emit=None, circuit_breakers=breakers)


@pytest.fixture(scope="module")
def client(gateway_app):
    return gateway_app.test_client()


class TestChaosCircuitBreaker:
    """混沌：模拟细胞连续失败，验证熔断器开启后拒绝请求。"""

    def test_breaker_opens_after_50_percent_failures(self, breakers):
        cell = "chaos_cell"
        cb = breakers.get(cell)
        for _ in range(3):
            cb.record(False)
        for _ in range(2):
            cb.record(True)
        assert cb.allow_request() is False

    def test_gateway_returns_503_when_circuit_open(self, client, breakers):
        if not HAS_FLASK:
            pytest.skip("flask not installed")
        cell = "chaos_cell"
        cb = breakers.get(cell)
        for _ in range(4):
            cb.record(False)
        assert cb.allow_request() is False
        headers = {"Content-Type": "application/json", "Authorization": "Bearer x", "X-Tenant-Id": "t1"}
        r = client.get(f"/api/v1/{cell}/any", headers=headers)
        assert r.status_code == 503
        assert r.get_json().get("code") == "CIRCUIT_OPEN"
