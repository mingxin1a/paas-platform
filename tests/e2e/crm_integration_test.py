"""
CRM 模块端到端集成测试
验证 CRM 通过 PaaS 网关的完整调用链。
遵循《接口设计说明书_V2.0》《03_超级_PaaS_平台逻辑全景图》
00 第三审判合规：静态导入 platform_core，禁止反射/动态加载。
"""
import os
import sys

import pytest

# 项目根目录，保证 platform_core 可被导入（包名避免与 stdlib platform 冲突）
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, _ROOT)

try:
    from flask import Flask
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False

# 静态导入平台核心（单一实现，与 deploy 一致）
from platform_core.core.registry.client import RegistryClient
from platform_core.core.gateway.app import create_app


@pytest.fixture(scope="module")
def registry():
    r = RegistryClient()
    r.register("crm", "http://crm-cell:8001")
    return r


@pytest.fixture(scope="module")
def monitor_emit():
    def emit(trace_id, cell, path, status, duration_ms):
        pass
    return emit


@pytest.fixture(scope="module")
def gateway_app(registry, monitor_emit):
    if not HAS_FLASK:
        pytest.skip("flask not installed")
    return create_app(registry_resolver=registry.resolve, monitor_emit=monitor_emit, circuit_breakers=None)


@pytest.fixture(scope="module")
def client(gateway_app):
    if not HAS_FLASK:
        pytest.skip("flask not installed")
    return gateway_app.test_client()


class TestCrmViaGateway:
    """通过 PaaS 网关访问 CRM 的完整调用链验证。"""

    def test_gateway_health(self, client):
        """网关健康检查。"""
        if not HAS_FLASK:
            pytest.skip("flask not installed")
        r = client.get("/health")
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("status") == "up"

    def test_crm_get_customers_requires_auth(self, client):
        """GET /api/v1/crm/customers 缺少 Authorization 返回 400。"""
        if not HAS_FLASK:
            pytest.skip("flask not installed")
        r = client.get(
            "/api/v1/crm/customers",
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 400
        body = r.get_json()
        assert body.get("code") == "MISSING_HEADER"
        assert "Authorization" in body.get("message", "")

    def test_crm_get_customers_full_headers(self, client):
        """GET /api/v1/crm/customers 带齐必须头，返回 200 与 X-Response-Time。未转发时返回列表形 { data, total }。"""
        if not HAS_FLASK:
            pytest.skip("flask not installed")
        r = client.get(
            "/api/v1/crm/customers",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer test-token",
                "X-Tenant-Id": "tenant-001",
            },
        )
        assert r.status_code == 200
        assert "X-Response-Time" in r.headers
        data = r.get_json()
        # 未开启 USE_REAL_FORWARD 时网关返回前端期望的列表形
        assert "data" in data
        assert isinstance(data["data"], list)
        assert "total" in data
        assert data["total"] >= 0

    def test_crm_post_customer_requires_request_id(self, client):
        """POST /api/v1/crm/customers 缺少 X-Request-ID 返回 400（幂等要求）。"""
        if not HAS_FLASK:
            pytest.skip("flask not installed")
        r = client.post(
            "/api/v1/crm/customers",
            headers={"Content-Type": "application/json", "Authorization": "Bearer test"},
            json={"name": "Test Customer"},
        )
        assert r.status_code == 400
        body = r.get_json()
        assert "X-Request-ID" in body.get("message", "")

    def test_crm_post_customer_full_headers(self, client):
        """POST /api/v1/crm/customers 带 X-Request-ID，返回 200。未转发时返回 gateway 占位。"""
        if not HAS_FLASK:
            pytest.skip("flask not installed")
        r = client.post(
            "/api/v1/crm/customers",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer test-token",
                "X-Request-ID": "req-e2e-001",
                "X-Tenant-Id": "tenant-001",
            },
            json={"name": "E2E Customer", "contactEmail": "e2e@example.com"},
        )
        assert r.status_code == 200
        assert "X-Response-Time" in r.headers
        data = r.get_json()
        assert data.get("cell") == "crm"
        assert data.get("traceId") is not None
        # 未转发时为 gateway 占位，含 forwardTo 或 gateway
        assert "forwardTo" in data or data.get("gateway") == "ok"
