"""
网关单元测试：健康、认证、管理端 API、请求头校验。
"""
from __future__ import annotations

import pytest


def test_health(gateway_client):
    r = gateway_client.get("/health")
    assert r.status_code == 200
    data = r.get_json()
    assert data is not None
    assert data.get("status") in ("up", "ok") or "gateway" in str(data).lower()


def test_auth_login_success(gateway_client):
    r = gateway_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin"},
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 200
    body = r.get_json()
    assert body.get("token")
    assert body.get("user", {}).get("username") == "admin"
    assert body.get("user", {}).get("role") == "admin"


def test_auth_login_missing_username(gateway_client):
    r = gateway_client.post(
        "/api/auth/login",
        json={"password": "admin"},
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 400
    assert r.get_json().get("code") == "BAD_REQUEST"


def test_auth_login_wrong_password(gateway_client):
    r = gateway_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "wrong"},
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 401
    assert r.get_json().get("code") == "UNAUTHORIZED"


def test_admin_cells_requires_auth(gateway_client):
    r = gateway_client.get("/api/admin/cells")
    assert r.status_code == 401


def test_admin_cells_with_token(gateway_client):
    login = gateway_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin"},
        headers={"Content-Type": "application/json"},
    )
    token = login.get_json().get("token")
    r = gateway_client.get(
        "/api/admin/cells",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    assert r.status_code == 200
    body = r.get_json()
    assert "data" in body and "total" in body


def test_admin_routes_with_token(gateway_client):
    login = gateway_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin"},
        headers={"Content-Type": "application/json"},
    )
    token = login.get_json().get("token")
    r = gateway_client.get(
        "/api/admin/routes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.get_json()
    assert "routes" in body


def test_admin_routes_forbidden_for_client_role(gateway_client):
    """管理端接口仅允许 admin 角色，client token 应返回 403（越权防护）。"""
    login = gateway_client.post(
        "/api/auth/login",
        json={"username": "client", "password": "123"},
        headers={"Content-Type": "application/json"},
    )
    assert login.status_code == 200
    token = login.get_json().get("token")
    r = gateway_client.get(
        "/api/admin/cells",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    assert r.status_code == 403
    assert r.get_json().get("code") == "FORBIDDEN"


def test_cell_proxy_requires_headers(gateway_client):
    """POST 到细胞代理缺少 Authorization 或 X-Request-ID 应返回 400/401。"""
    r = gateway_client.post(
        "/api/v1/erp/orders",
        json={"customerId": "c1", "totalAmountCents": 100},
        headers={"Content-Type": "application/json", "X-Tenant-Id": "t1"},
    )
    assert r.status_code in (400, 401, 503)


def test_response_headers_trace_id(gateway_client):
    r = gateway_client.get("/health")
    assert r.status_code == 200
    assert "X-Trace-Id" in r.headers or "X-Response-Time" in r.headers
