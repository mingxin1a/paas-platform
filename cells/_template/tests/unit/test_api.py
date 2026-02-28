# 标准化接口与错误码测试（《接口设计说明书》）
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    return TestClient(app)


def _headers(tenant: str = "tenant-001", request_id: str | None = None):
    h = {"Content-Type": "application/json", "Authorization": "Bearer test", "X-Tenant-Id": tenant}
    if request_id:
        h["X-Request-ID"] = request_id
    return h


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "up"
    assert "X-Response-Time" in r.headers


def test_unauthorized(client):
    r = client.get("/items", headers={"X-Tenant-Id": "t1"})
    assert r.status_code == 401
    assert r.json().get("code") == "UNAUTHORIZED"


def test_items_crud(client):
    r = client.get("/items", headers=_headers())
    assert r.status_code == 200
    assert "data" in r.json() and "total" in r.json()
    r2 = client.post("/items", json={"name": "示例"}, headers=_headers(request_id="req-1"))
    assert r2.status_code == 201
    assert r2.json()["name"] == "示例"
    assert "itemId" in r2.json()
    r3 = client.post("/items", json={"name": "重复"}, headers=_headers(request_id="req-1"))
    assert r3.status_code == 409
    item_id = r2.json()["itemId"]
    r4 = client.get(f"/items/{item_id}", headers=_headers())
    assert r4.status_code == 200
    r5 = client.delete(f"/items/{item_id}", headers=_headers())
    assert r5.status_code == 204


def test_post_requires_x_request_id(client):
    r = client.post("/items", json={"name": "x"}, headers=_headers())
    assert r.status_code == 400
    assert "X-Request-ID" in (r.json().get("message") or "")
