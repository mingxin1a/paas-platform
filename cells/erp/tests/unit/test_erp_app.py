"""ERP 单元测试：GL、AR、AP、MM、PP 接口契约与幂等。"""
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
    assert r.json["cell"] == "erp"

def test_gl_accounts_and_journal(client):
    r = client.get("/gl/accounts", headers=h())
    assert r.status_code == 200
    r2 = client.post("/gl/accounts", json={"accountCode": "1001", "name": "现金", "accountType": 1}, headers=h(req_id="gl-acc-1"))
    assert r2.status_code == 201
    r3 = client.post("/gl/journal-entries", json={"documentNo": "J001", "postingDate": "2025-01-01", "lines": [{"accountCode": "1001", "debitCents": 10000, "creditCents": 0}, {"accountCode": "4001", "debitCents": 0, "creditCents": 10000}]}, headers=h(req_id="gl-ent-1"))
    assert r3.status_code == 201

def test_ar_ap(client):
    r = client.post("/ar/invoices", json={"customerId": "c1", "documentNo": "AR001", "amountCents": 50000}, headers=h(req_id="ar-1"))
    assert r.status_code == 201
    r2 = client.post("/ap/invoices", json={"supplierId": "s1", "documentNo": "AP001", "amountCents": 30000}, headers=h(req_id="ap-1"))
    assert r2.status_code == 201

def test_mm_pp(client):
    r = client.post("/mm/materials", json={"materialCode": "M001", "name": "原料A"}, headers=h(req_id="mm-1"))
    assert r.status_code == 201
    mid = r.json["materialId"]
    r2 = client.post("/mm/purchase-orders", json={"supplierId": "s1", "documentNo": "PO001"}, headers=h(req_id="po-1"))
    assert r2.status_code == 201
    r3 = client.post("/pp/boms", json={"productMaterialId": mid}, headers=h(req_id="bom-1"))
    assert r3.status_code == 201
    r4 = client.post("/pp/work-orders", json={"bomId": r3.json["bomId"], "productMaterialId": mid, "plannedQuantity": 10}, headers=h(req_id="wo-1"))
    assert r4.status_code == 201


def test_validation_error_unbalanced_gl(client):
    client.post("/gl/accounts", json={"accountCode": "1001", "name": "现金", "accountType": 1}, headers=h(req_id="v-gl-1"))
    r = client.post("/gl/journal-entries", json={"documentNo": "J2", "postingDate": "2025-01-01", "lines": [{"accountCode": "1001", "debitCents": 1000, "creditCents": 0}]}, headers=h(req_id="v-gl-2"))
    assert r.status_code == 400
    assert r.json.get("code") == "BUSINESS_RULE_VIOLATION"


def test_list_pagination(client):
    r = client.get("/orders?page=1&pageSize=2", headers=h())
    assert r.status_code == 200
    assert "data" in r.json and "total" in r.json and r.json.get("page") == 1 and r.json.get("pageSize") == 2


def test_soft_delete_order(client):
    r = client.post("/orders", json={"customerId": "c2", "totalAmountCents": 100}, headers=h(req_id="del-ord-1"))
    assert r.status_code == 201
    oid = r.json["orderId"]
    r2 = client.delete(f"/orders/{oid}", headers=h())
    assert r2.status_code == 200
    assert r2.json.get("deleted") is True
    r3 = client.get(f"/orders/{oid}", headers=h())
    assert r3.status_code == 404


def test_pp_cost_summary_and_work_order_cost(client):
    r = client.post("/mm/materials", json={"materialCode": "M2", "name": "原料B"}, headers=h(req_id="cost-mm"))
    assert r.status_code == 201
    mid = r.json["materialId"]
    r2 = client.post("/pp/boms", json={"productMaterialId": mid}, headers=h(req_id="cost-bom"))
    assert r2.status_code == 201
    bid = r2.json["bomId"]
    r3 = client.post("/pp/work-orders", json={"bomId": bid, "productMaterialId": mid, "plannedQuantity": 5}, headers=h(req_id="cost-wo"))
    assert r3.status_code == 201
    wid = r3.json["workOrderId"]
    r4 = client.post(f"/pp/work-orders/{wid}/report", json={"completedQuantity": 5, "unitMaterialCostCents": 100, "unitLaborCostCents": 50}, headers=h())
    assert r4.status_code == 200
    r5 = client.get("/pp/cost-summary", headers=h())
    assert r5.status_code == 200
    assert "data" in r5.json and "total" in r5.json
    r6 = client.get(f"/pp/work-orders/{wid}/cost", headers=h())
    assert r6.status_code == 200
    c = r6.json
    assert c.get("materialCostCents") == 500 and c.get("laborCostCents") == 250 and c.get("totalCostCents") == 750


def test_export_orders_csv(client):
    r = client.get("/export/orders?format=csv", headers=h())
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("Content-Type", "")


def test_audit_logs(client):
    r = client.get("/audit-logs", headers=h())
    assert r.status_code == 200
    assert "data" in r.get_json() and "total" in r.get_json()


def test_orders_import(client):
    r = client.post("/orders/import", json={"items": [{"customerId": "c-imp", "totalAmountCents": 99900, "currency": "CNY"}]}, headers=h())
    assert r.status_code == 202
    j = r.get_json()
    assert j.get("accepted") is True and j.get("created") == 1
