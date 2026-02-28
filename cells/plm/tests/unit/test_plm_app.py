"""PLM 细胞基础接口测试：健康、产品、BOM。"""
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
    assert r.json.get("cell") == "plm"

def test_products_list_and_create(client):
    r = client.get("/products", headers=h())
    assert r.status_code == 200
    assert "data" in r.json
    r2 = client.post("/products", json={"productCode": "P001", "name": "产品A"}, headers=h(req_id="plm-p1"))
    assert r2.status_code in (200, 201)
    assert "productId" in r2.json or "productCode" in r2.json

def test_boms_and_change_records(client):
    r = client.get("/boms", headers=h())
    assert r.status_code == 200
    r2 = client.post("/change-records", json={"entityType": "Product", "entityId": "e1", "description": "变更"}, headers=h())
    assert r2.status_code == 201
    assert "changeId" in r2.json

def test_process_routes_and_drawings(client):
    r = client.post("/products", json={"productCode": "P002", "name": "产品B"}, headers=h(req_id="plm-p2"))
    pid = r.json.get("productId", "")
    if pid:
        r2 = client.post("/process-routes", json={"productId": pid, "name": "工艺路线1"}, headers=h(req_id="plm-pr1"))
        assert r2.status_code == 201
        assert "processRouteId" in r2.json
        r3 = client.get("/drawings", headers=h())
        assert r3.status_code == 200
        r4 = client.post("/drawings", json={"productId": pid, "storagePath": "/path/to/dwg"}, headers=h(req_id="plm-d1"))
        assert r4.status_code == 201

def test_audit_logs(client):
    r = client.get("/audit-logs", headers=h())
    assert r.status_code == 200
    assert "data" in r.json and "total" in r.json
