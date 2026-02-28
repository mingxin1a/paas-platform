"""
PaaS 核心层全量集成测试：网关健康、登录、审计、细胞代理（需网关与至少一个细胞运行，或 mock）。
默认不启动真实服务；设置 GATEWAY_URL 且 USE_REAL_GATEWAY=1 时请求真实网关。
"""
from __future__ import annotations

import os
import json
import urllib.request
import urllib.error

import pytest

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8000").rstrip("/")
USE_REAL = os.environ.get("USE_REAL_GATEWAY", "") == "1"


def _req(method: str, path: str, body: dict | None = None, headers: dict | None = None) -> tuple[int, dict]:
    url = f"{GATEWAY_URL}{path}"
    h = {"Content-Type": "application/json", "X-Tenant-Id": "integration-test"}
    if headers:
        h.update(headers)
    data = json.dumps(body).encode("utf-8") if body and method in ("POST", "PUT", "PATCH") else None
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read().decode()
            return r.getcode(), json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode() if e.fp else "{}"
        try:
            return e.code, json.loads(raw) if raw else {}
        except Exception:
            return e.code, {}
    except Exception:
        return 0, {}


@pytest.mark.skipif(not USE_REAL, reason="USE_REAL_GATEWAY=1 and gateway running required")
def test_gateway_health():
    code, _ = _req("GET", "/health")
    assert code == 200


@pytest.mark.skipif(not USE_REAL, reason="USE_REAL_GATEWAY=1 and gateway running required")
def test_gateway_login():
    code, body = _req("POST", "/api/auth/login", {"username": "admin", "password": "admin"})
    assert code == 200
    assert body.get("token") and body.get("user")


@pytest.mark.skipif(not USE_REAL, reason="USE_REAL_GATEWAY=1 and gateway running required")
def test_gateway_admin_cells_requires_auth():
    code, _ = _req("GET", "/api/admin/cells")
    assert code == 401


@pytest.mark.skipif(not USE_REAL, reason="USE_REAL_GATEWAY=1 and gateway running required")
def test_gateway_cell_proxy_health():
    code, body = _req(
        "GET", "/api/v1/crm/health",
        headers={"Authorization": "Bearer smoke-test", "X-Request-ID": "int-crm-health"}
    )
    assert code == 200
    assert body.get("status") == "up"
