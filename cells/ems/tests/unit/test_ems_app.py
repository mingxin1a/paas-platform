"""EMS 细胞基础接口测试：健康、配置、能耗记录。"""
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
    assert r.json.get("cell") == "ems"

def test_config_retention(client):
    r = client.get("/config/retention", headers=h())
    assert r.status_code == 200
    assert "energyDataRetentionDays" in r.json

def test_consumption_list_and_create(client):
    r = client.get("/consumption-records", headers=h())
    assert r.status_code == 200
    assert "data" in r.json and "total" in r.json
    r2 = client.post("/consumption-records", json={"meterId": "M1", "value": 100.5, "unit": "kWh"}, headers=h(req_id="ems-c1"))
    assert r2.status_code in (200, 201)
    assert r2.json.get("meterId") == "M1" or "recordId" in r2.json

def test_stats_and_analysis(client):
    client.post("/consumption-records", json={"meterId": "M1", "value": 100, "unit": "kWh"}, headers=h(req_id="ems-s1"))
    r = client.get("/stats?period=day", headers=h())
    assert r.status_code == 200
    assert "data" in r.json
    r2 = client.get("/analysis?period=month", headers=h())
    assert r2.status_code == 200
    assert "totalConsumption" in r2.json or "period" in r2.json

def test_alerts_and_suggestions(client):
    client.post("/alerts", json={"meterId": "M1", "alertType": "anomaly", "actualValue": 999}, headers=h())
    r = client.get("/alerts", headers=h())
    assert r.status_code == 200
    assert "data" in r.json
    r2 = client.get("/suggestions", headers=h())
    assert r2.status_code == 200
    assert "data" in r2.json

def test_reports_and_export(client):
    r = client.get("/reports?period=month", headers=h())
    assert r.status_code == 200
    r2 = client.get("/export", headers=h())
    assert r2.status_code == 200
    assert "retentionDays" in r2.json

def test_audit_logs(client):
    client.post("/consumption-records", json={"meterId": "M2", "value": 50, "unit": "kWh"}, headers=h(req_id="ems-a1"))
    r = client.get("/audit-logs", headers=h())
    assert r.status_code == 200
    assert "data" in r.json and "total" in r.json
