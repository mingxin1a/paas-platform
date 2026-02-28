"""
CRM FastAPI 细胞单元测试：《接口设计说明书》统一格式、错误码、鉴权与 CRUD。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

# 测试使用同一进程内可共享的 SQLite 文件，避免 :memory: per-connection 导致请求间数据隔离
import tempfile
_test_db = Path(tempfile.gettempdir()) / f"crm_test_{os.getpid()}.db"
os.environ["CRM_DATABASE_URL"] = f"sqlite:///{_test_db.as_posix()}"

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    return TestClient(app)


def _headers(tenant: str = "tenant-001", request_id: str | None = None):
    h = {"Content-Type": "application/json", "Authorization": "Bearer test-token", "X-Tenant-Id": tenant}
    if request_id:
        h["X-Request-ID"] = request_id
    return h


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "up"
    assert r.json()["cell"] == "crm"
    assert "X-Response-Time" in r.headers


def test_unauthorized_without_auth(client):
    r = client.get("/customers", headers={"X-Tenant-Id": "t1"})
    assert r.status_code == 401
    body = r.json()
    assert body.get("code") == "UNAUTHORIZED"


def test_customers_crud(client):
    # List
    r = client.get("/customers", headers=_headers())
    assert r.status_code == 200
    assert "data" in r.json() and "total" in r.json()
    assert r.json()["total"] == 0
    # Create (幂等)
    r2 = client.post("/customers", json={"name": "测试客户", "contactPhone": "13800138000"}, headers=_headers(request_id="req-c1"))
    assert r2.status_code == 201
    data = r2.json()
    assert data["name"] == "测试客户"
    assert "customerId" in data
    cid = data["customerId"]
    # 幂等冲突
    r3 = client.post("/customers", json={"name": "其他"}, headers=_headers(request_id="req-c1"))
    assert r3.status_code == 409
    # Get
    r4 = client.get(f"/customers/{cid}", headers=_headers())
    assert r4.status_code == 200
    assert r4.json()["name"] == "测试客户"
    # Update
    r5 = client.patch(f"/customers/{cid}", json={"contactEmail": "a@b.com"}, headers=_headers(request_id="req-c1-patch"))
    assert r5.status_code == 200
    assert r5.json()["contactEmail"] == "a@b.com"
    # Delete
    r6 = client.delete(f"/customers/{cid}", headers=_headers())
    assert r6.status_code == 204
    r7 = client.get(f"/customers/{cid}", headers=_headers())
    assert r7.status_code == 404


def test_contacts_crud(client):
    # 先建客户
    rc = client.post("/customers", json={"name": "客户A"}, headers=_headers(request_id="req-cc"))
    assert rc.status_code == 201
    customer_id = rc.json()["customerId"]
    # 创建联系人
    r = client.post("/contacts", json={"customerId": customer_id, "name": "张三", "phone": "13900139000", "isPrimary": True}, headers=_headers(request_id="req-ct1"))
    assert r.status_code == 201
    assert r.json()["name"] == "张三"
    contact_id = r.json()["contactId"]
    # List by customer
    r2 = client.get("/contacts", params={"customerId": customer_id}, headers=_headers())
    assert r2.status_code == 200
    assert r2.json()["total"] >= 1
    # Get
    r3 = client.get(f"/contacts/{contact_id}", headers=_headers())
    assert r3.status_code == 200
    # Delete
    r4 = client.delete(f"/contacts/{contact_id}", headers=_headers())
    assert r4.status_code == 204


def test_opportunities_crud(client):
    rc = client.post("/customers", json={"name": "客户B"}, headers=_headers(request_id="req-co"))
    assert rc.status_code == 201
    customer_id = rc.json()["customerId"]
    r = client.post("/opportunities", json={"customerId": customer_id, "title": "商机1", "amountCents": 10000, "currency": "CNY"}, headers=_headers(request_id="req-op1"))
    assert r.status_code == 201
    assert r.json()["title"] == "商机1"
    oid = r.json()["opportunityId"]
    r2 = client.get(f"/opportunities/{oid}", headers=_headers())
    assert r2.status_code == 200
    r3 = client.get("/opportunities", params={"customerId": customer_id}, headers=_headers())
    assert r3.status_code == 200
    assert r3.json()["total"] >= 1


def test_follow_ups_crud(client):
    r = client.post("/follow-ups", json={"content": "电话跟进，客户有意向", "followUpType": "call"}, headers=_headers(request_id="req-fu1"))
    assert r.status_code == 201
    assert r.json()["content"] == "电话跟进，客户有意向"
    fid = r.json()["followUpId"]
    r2 = client.get(f"/follow-ups/{fid}", headers=_headers())
    assert r2.status_code == 200
    r3 = client.get("/follow-ups", headers=_headers())
    assert r3.status_code == 200
    assert r3.json()["total"] >= 1
    r4 = client.patch(f"/follow-ups/{fid}", json={"content": "已更新内容"}, headers=_headers(request_id="req-fu1-p"))
    assert r4.status_code == 200
    assert r4.json()["content"] == "已更新内容"
    r5 = client.delete(f"/follow-ups/{fid}", headers=_headers())
    assert r5.status_code == 204


def test_post_requires_x_request_id(client):
    r = client.post("/customers", json={"name": "x"}, headers=_headers())  # 无 X-Request-ID
    assert r.status_code == 400
    assert r.json().get("code") == "BAD_REQUEST"


def test_audit_logs(client):
    r = client.get("/audit-logs", headers=_headers())
    assert r.status_code == 200
    j = r.json()
    assert "data" in j and "total" in j
    r2 = client.get("/audit-logs", params={"resourceType": "customer"}, headers=_headers())
    assert r2.status_code == 200


def test_opportunities_import_export(client):
    rc = client.post("/customers", json={"name": "客户E"}, headers=_headers(request_id="req-imp"))
    assert rc.status_code == 201
    cid = rc.json()["customerId"]
    r = client.post("/opportunities/import", json={"items": [{"customerId": cid, "title": "批量商机1", "amountCents": 5000}]}, headers=_headers())
    assert r.status_code == 202
    j = r.json()
    assert j.get("accepted") is True and j.get("created") == 1
    r2 = client.get("/opportunities/export", params={"format": "csv"}, headers=_headers())
    assert r2.status_code == 200
    assert "text/csv" in r2.headers.get("content-type", "")
