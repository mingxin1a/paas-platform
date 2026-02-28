"""LIMS 细胞基础接口测试：健康、样品列表。"""
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
    assert r.json.get("cell") == "lims"

def test_samples_list(client):
    r = client.get("/samples", headers=h())
    assert r.status_code == 200
    assert "data" in r.json or isinstance(r.json.get("data"), list)

def test_sample_receive_and_report_review_archive(client):
    r = client.post("/samples", json={"sampleNo": "L001", "batchId": "B1", "testType": "QC"}, headers=h(req_id="lims-s1"))
    assert r.status_code == 201
    sid = r.json.get("sampleId")
    if sid:
        r2 = client.post(f"/samples/{sid}/receive", headers=h())
        assert r2.status_code == 200
    r3 = client.post("/reports", json={"sampleId": sid or "x", "content": "报告"}, headers=h(req_id="lims-r1"))
    assert r3.status_code == 201
    rid = r3.json.get("reportId")
    if rid:
        client.post(f"/reports/{rid}/review", headers=h())
        r4 = client.post(f"/reports/{rid}/archive", headers=h())
        assert r4.status_code in (200, 404)

def test_trace(client):
    r = client.get("/trace", headers=h())
    assert r.status_code == 200
    assert "data" in r.json
