"""HIS 细胞基础接口测试：健康、患者列表。"""
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
    assert r.json.get("cell") == "his"

def test_patients_list(client):
    r = client.get("/patients", headers=h())
    assert r.status_code == 200
    assert "data" in r.json or isinstance(r.json.get("data"), list)

def test_patient_create(client):
    r = client.post("/patients", json={"patientNo": "P001", "name": "测试", "gender": "M"}, headers=h(req_id="his-p1"))
    assert r.status_code in (200, 201)
    assert "patientId" in r.json or "patientNo" in r.json

def test_registration_and_charges(client):
    r = client.get("/registration", headers=h())
    assert r.status_code == 200
    assert "data" in r.json
    r2 = client.get("/charges", headers=h())
    assert r2.status_code == 200
    assert "data" in r2.json

def test_inpatients_list(client):
    r = client.get("/inpatients", headers=h())
    assert r.status_code == 200
    assert "data" in r.json

def test_audit_logs(client):
    client.post("/patients", json={"name": "审计测试"}, headers=h(req_id="his-a1"))
    r = client.get("/audit-logs", headers=h())
    assert r.status_code == 200
    assert "data" in r.json and "total" in r.json
