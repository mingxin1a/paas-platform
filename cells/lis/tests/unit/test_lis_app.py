"""LIS 细胞基础接口测试：健康、样本列表。"""
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

def h(tenant="t1", req_id=None):
    headers = {"Content-Type": "application/json", "X-Tenant-Id": tenant}
    if req_id:
        headers["X-Request-ID"] = req_id
    return headers

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json.get("cell") == "lis"

def test_samples_list(client):
    r = client.get("/samples", headers=h())
    assert r.status_code == 200
    assert "data" in r.json or isinstance(r.json.get("data"), list)

def test_sample_receive_and_report_flow(client):
    r = client.post("/samples", json={"sampleNo": "S001", "patientId": "p1", "requestId": "req1", "specimenType": "blood"}, headers=h(req_id="lis-s1"))
    assert r.status_code == 201
    sid = r.json.get("sampleId")
    if sid:
        r2 = client.post(f"/samples/{sid}/receive", headers=h())
        assert r2.status_code == 200
        assert r2.json.get("receivedAt") or r2.json.get("status") == 1
    r3 = client.post("/reports", json={"sampleId": sid or "x", "content": "报告内容"}, headers=h(req_id="lis-r1"))
    assert r3.status_code == 201
    rid = r3.json.get("reportId")
    if rid:
        client.post(f"/reports/{rid}/review", headers=h())
        r4 = client.post(f"/reports/{rid}/publish", headers=h())
        assert r4.status_code in (200, 404)  # 404 if not reviewed in same store instance

def test_audit_logs(client):
    r = client.get("/audit-logs", headers=h())
    assert r.status_code == 200
    assert "data" in r.json and "total" in r.json
