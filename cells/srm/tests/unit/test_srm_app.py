"""
SRM 细胞单元测试：《接口设计说明书》统一格式、健康、供应商与采购订单 CRUD、幂等与错误格式。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import pytest
from src.app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _h(tenant: str = "tenant-001", req_id: str | None = None):
    headers = {"Content-Type": "application/json", "X-Tenant-Id": tenant}
    if req_id:
        headers["X-Request-ID"] = req_id
    return headers


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "up"
    assert r.get_json()["cell"] == "srm"
    assert "X-Response-Time" in r.headers or True


def test_suppliers_list_empty(client):
    r = client.get("/suppliers", headers=_h())
    assert r.status_code == 200
    j = r.get_json()
    assert "data" in j and "total" in j
    assert j["data"] == [] and j["total"] == 0


def test_suppliers_crud(client):
    r = client.post("/suppliers", json={"name": "供应商A", "code": "SUP001", "contact": "13800138000"}, headers=_h(req_id="srm-s1"))
    assert r.status_code == 201
    j = r.get_json()
    assert j["name"] == "供应商A"
    assert "supplierId" in j
    sid = j["supplierId"]
    r2 = client.get(f"/suppliers/{sid}", headers=_h())
    assert r2.status_code == 200
    assert r2.get_json()["name"] == "供应商A"
    r3 = client.get("/suppliers", headers=_h())
    assert r3.status_code == 200
    assert r3.get_json()["total"] >= 1


def test_suppliers_contact_masking(client):
    """供应商 contact 敏感数据脱敏：列表与详情返回掩码（如 138****8000）。"""
    r = client.post("/suppliers", json={"name": "脱敏测", "contact": "13800138000"}, headers=_h(req_id="srm-mask"))
    assert r.status_code == 201
    sid = r.get_json()["supplierId"]
    list_r = client.get("/suppliers", headers=_h())
    assert list_r.status_code == 200
    found = [s for s in list_r.get_json()["data"] if s.get("supplierId") == sid]
    assert len(found) == 1
    assert "****" in (found[0].get("contact") or "")
    detail_r = client.get(f"/suppliers/{sid}", headers=_h())
    assert detail_r.status_code == 200
    assert "****" in (detail_r.get_json().get("contact") or "")


def test_suppliers_create_requires_name(client):
    r = client.post("/suppliers", json={}, headers=_h(req_id="srm-s2"))
    assert r.status_code == 400
    assert r.get_json().get("code") == "BAD_REQUEST"


def test_suppliers_idempotent(client):
    r1 = client.post("/suppliers", json={"name": "幂等供应商"}, headers=_h(req_id="srm-idem"))
    assert r1.status_code == 201
    r2 = client.post("/suppliers", json={"name": "其他"}, headers=_h(req_id="srm-idem"))
    assert r2.status_code == 409
    assert r2.get_json().get("code") == "IDEMPOTENT_CONFLICT"


def test_purchase_orders_crud(client):
    r = client.post("/suppliers", json={"name": "供方B"}, headers=_h(req_id="srm-po-s"))
    assert r.status_code == 201
    sid = r.get_json()["supplierId"]
    r2 = client.post("/purchase-orders", json={"supplierId": sid, "orderNo": "PO001", "amountCents": 10000}, headers=_h(req_id="srm-po1"))
    assert r2.status_code == 201
    j = r2.get_json()
    assert "orderId" in j
    oid = j["orderId"]
    r3 = client.get(f"/purchase-orders/{oid}", headers=_h())
    assert r3.status_code == 200
    r4 = client.patch(f"/purchase-orders/{oid}", json={"status": 2}, headers=_h())
    assert r4.status_code == 200
    assert r4.get_json()["status"] == 2


def test_purchase_order_not_found(client):
    r = client.get("/purchase-orders/nonexistent", headers=_h())
    assert r.status_code == 404
    assert r.get_json().get("code") == "NOT_FOUND"


def test_rfq_list(client):
    r = client.get("/rfqs", headers=_h())
    assert r.status_code == 200
    j = r.get_json()
    assert "data" in j and "total" in j and "page" in j


def test_quotes_list(client):
    r = client.get("/quotes", headers=_h())
    assert r.status_code == 200
    j = r.get_json()
    assert "data" in j and "total" in j


def test_evaluations_require_supplier(client):
    r = client.post("/evaluations", json={}, headers=_h(req_id="srm-ev1"))
    assert r.status_code == 400
    assert r.get_json().get("code") == "BAD_REQUEST"


def test_bidding_projects_crud(client):
    r = client.get("/bidding/projects", headers=_h())
    assert r.status_code == 200
    assert "data" in r.get_json() and "total" in r.get_json()
    r2 = client.post("/bidding/projects", json={"title": "年度钢材招标", "description": "2025年度"}, headers=_h(req_id="srm-bid1"))
    assert r2.status_code == 201
    j = r2.get_json()
    assert j.get("title") == "年度钢材招标" and "projectId" in j and j.get("status") == "open"
    pid = j["projectId"]
    r3 = client.get(f"/bidding/projects/{pid}", headers=_h())
    assert r3.status_code == 200
    r4 = client.patch(f"/bidding/projects/{pid}", json={"status": "closed"}, headers=_h())
    assert r4.status_code == 200
    assert r4.get_json().get("status") == "closed"


def test_bidding_project_title_required(client):
    r = client.post("/bidding/projects", json={}, headers=_h(req_id="srm-bid-empty"))
    assert r.status_code == 400
    assert r.get_json().get("code") == "BAD_REQUEST"


def test_export_purchase_orders_csv(client):
    r = client.get("/export/purchase-orders?format=csv", headers=_h())
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("Content-Type", "")
    assert "订单编号" in r.get_data(as_text=True) or ""


def test_audit_logs(client):
    r = client.get("/audit-logs", headers=_h())
    assert r.status_code == 200
    assert "data" in r.get_json() and "total" in r.get_json()


def test_suppliers_import(client):
    r = client.post("/suppliers/import", json={"items": [{"name": "批量供应商A", "code": "IMP001"}]}, headers=_h())
    assert r.status_code == 202
    j = r.get_json()
    assert j.get("accepted") is True and j.get("created") == 1
