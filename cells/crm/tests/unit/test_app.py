"""
CRM Flask 应用单元测试：API 契约与响应格式。
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


def _headers(tenant="tenant-001", request_id=None):
    h = {"Content-Type": "application/json", "X-Tenant-Id": tenant}
    if request_id:
        h["X-Request-ID"] = request_id
    return h


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json["status"] == "up"
    assert "X-Response-Time" in r.headers


def test_customers_get_post(client):
    r = client.get("/customers", headers=_headers())
    assert r.status_code == 200
    assert "data" in r.json and "total" in r.json
    r2 = client.post("/customers", json={"name": "测试客户"}, headers=_headers(request_id="req-1"))
    assert r2.status_code == 201
    assert r2.json["name"] == "测试客户"
    assert "customerId" in r2.json
    r3 = client.post("/customers", json={"name": "重复"}, headers=_headers(request_id="req-1"))
    assert r3.status_code == 409


def test_leads_create_convert(client):
    r = client.post("/leads", json={"name": "线索1", "company": "公司X"}, headers=_headers(request_id="lead-req-1"))
    assert r.status_code == 201
    lead_id = r.json["leadId"]
    r2 = client.patch("/leads/" + lead_id, json={"assignedTo": "user-1"}, headers=_headers())
    assert r2.status_code == 200
    r3 = client.post(
        "/leads/" + lead_id + "/convert",
        json={"convertTo": "both", "createOpportunityTitle": "转化商机", "amountCents": 10000},
        headers=_headers(request_id="conv-1"),
    )
    assert r3.status_code == 200
    assert r3.json["customerId"]
    assert r3.json["opportunityId"]


def test_opportunities_forecast_win_rate(client):
    r = client.get("/opportunities/forecast", headers=_headers())
    assert r.status_code == 200
    assert "byStage" in r.json and "totalWeightedCents" in r.json
    r2 = client.get("/opportunities/win-rate", headers=_headers())
    assert r2.status_code == 200
    assert "periodDays" in r2.json and "winRatePct" in r2.json


def test_customer_360(client):
    r = client.post("/customers", json={"name": "360客户"}, headers=_headers(request_id="c360-1"))
    assert r.status_code == 201
    cid = r.json["customerId"]
    r2 = client.get("/customers/" + cid + "/360", headers=_headers())
    assert r2.status_code == 200
    assert r2.json["customer"]["name"] == "360客户"
    assert "contacts" in r2.json and "opportunities" in r2.json
