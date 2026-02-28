"""ERP 验收测试：GL 过账、AR/AP、MM 采购、PP 工单 端到端。"""
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

def h(tenant="acceptance-erp", req_id=None):
    headers = {"Content-Type": "application/json", "X-Tenant-Id": tenant}
    if req_id:
        headers["X-Request-ID"] = req_id
    return headers

def test_gl_flow(client):
    client.post("/gl/accounts", json={"accountCode": "1001", "name": "现金", "accountType": 1}, headers=h(req_id="acc-gl-1"))
    client.post("/gl/accounts", json={"accountCode": "4001", "name": "收入", "accountType": 4}, headers=h(req_id="acc-gl-2"))
    r = client.post("/gl/journal-entries", json={"documentNo": "J-ACC", "postingDate": "2025-02-01", "lines": [{"accountCode": "1001", "debitCents": 100000, "creditCents": 0}, {"accountCode": "4001", "debitCents": 0, "creditCents": 100000}]}, headers=h(req_id="acc-gl-ent-1"))
    assert r.status_code == 201
    assert r.json["totalDebitCents"] == 100000
    assert r.json["totalCreditCents"] == 100000

def test_mm_pp_flow(client):
    r1 = client.post("/mm/materials", json={"materialCode": "P001", "name": "成品1"}, headers=h(req_id="acc-mm-1"))
    assert r1.status_code == 201
    r2 = client.post("/pp/boms", json={"productMaterialId": r1.json["materialId"]}, headers=h(req_id="acc-bom-1"))
    assert r2.status_code == 201
    r3 = client.post("/pp/work-orders", json={"bomId": r2.json["bomId"], "productMaterialId": r1.json["materialId"], "plannedQuantity": 100}, headers=h(req_id="acc-wo-1"))
    assert r3.status_code == 201
    assert r3.json["plannedQuantity"] == 100


def test_gl_trial_balance_and_entries(client):
    """GL 试算表 + 按期间筛选凭证"""
    client.post("/gl/accounts", json={"accountCode": "2001", "name": "银行", "accountType": 1}, headers=h(req_id="acc-tb-a1"))
    client.post("/gl/accounts", json={"accountCode": "4001", "name": "收入", "accountType": 4}, headers=h(req_id="acc-tb-a2"))
    client.post("/gl/journal-entries", json={"documentNo": "J-TB", "postingDate": "2025-01-15", "lines": [{"accountCode": "2001", "debitCents": 50000, "creditCents": 0}, {"accountCode": "4001", "debitCents": 0, "creditCents": 50000}]}, headers=h(req_id="acc-tb-e1"))
    r = client.get("/gl/trial-balance", headers=h())
    assert r.status_code == 200
    assert "data" in r.json
    r2 = client.get("/gl/journal-entries?dateFrom=2025-01-01&dateTo=2025-01-31", headers=h())
    assert r2.status_code == 200
    assert r2.json["total"] >= 1


def test_ar_receipt_and_ageing(client):
    """应收：开票 -> 收款 -> 账龄"""
    r = client.post("/ar/invoices", json={"customerId": "c1", "documentNo": "AR-A1", "amountCents": 100000, "dueDate": "2025-01-10"}, headers=h(req_id="acc-ar-1"))
    assert r.status_code == 201
    iid = r.json["invoiceId"]
    r2 = client.post("/ar/invoices/" + iid + "/receipts", json={"amountCents": 40000}, headers=h())
    assert r2.status_code == 200
    assert r2.json.get("paidAmountCents") == 40000
    r3 = client.get("/ar/ageing", headers=h())
    assert r3.status_code == 200
    assert "data" in r3.json


def test_ap_payment_and_ageing(client):
    """应付：开票 -> 付款 -> 账龄"""
    r = client.post("/ap/invoices", json={"supplierId": "s1", "documentNo": "AP-A1", "amountCents": 50000}, headers=h(req_id="acc-ap-1"))
    assert r.status_code == 201
    iid = r.json["invoiceId"]
    client.post("/ap/invoices/" + iid + "/payments", json={"amountCents": 50000}, headers=h())
    r2 = client.get("/ap/ageing", headers=h())
    assert r2.status_code == 200


def test_pp_work_order_report(client):
    """工单报工"""
    r = client.post("/mm/materials", json={"materialCode": "W01", "name": "工件"}, headers=h(req_id="acc-wo-m1"))
    mid = r.json["materialId"]
    r = client.post("/pp/boms", json={"productMaterialId": mid}, headers=h(req_id="acc-wo-b1"))
    bid = r.json["bomId"]
    r = client.post("/pp/work-orders", json={"bomId": bid, "productMaterialId": mid, "plannedQuantity": 50}, headers=h(req_id="acc-wo-w1"))
    wid = r.json["workOrderId"]
    r2 = client.post("/pp/work-orders/" + wid + "/report", json={"completedQuantity": 50}, headers=h())
    assert r2.status_code == 200
    assert r2.json["status"] == 4
    assert r2.json["completedQuantity"] == 50


def test_ar_receipt_over_amount_rejected(client):
    """收款超过待收金额应返回 400"""
    r = client.post("/ar/invoices", json={"customerId": "c2", "documentNo": "AR-O", "amountCents": 10000}, headers=h(req_id="acc-ar-o1"))
    assert r.status_code == 201
    iid = r.json["invoiceId"]
    r2 = client.post("/ar/invoices/" + iid + "/receipts", json={"amountCents": 20000}, headers=h())
    assert r2.status_code == 400
    assert r2.json.get("code") == "BUSINESS_RULE_VIOLATION"


def test_ar_receipt_idempotency(client):
    """同一 X-Request-ID 重复收款返回同一结果"""
    r = client.post("/ar/invoices", json={"customerId": "c3", "documentNo": "AR-ID", "amountCents": 50000}, headers=h(req_id="acc-ar-id1"))
    assert r.status_code == 201
    iid = r.json["invoiceId"]
    rid = "idem-receipt-1"
    r1 = client.post("/ar/invoices/" + iid + "/receipts", json={"amountCents": 20000}, headers=h(req_id=rid))
    r2 = client.post("/ar/invoices/" + iid + "/receipts", json={"amountCents": 20000}, headers=h(req_id=rid))
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json.get("paidAmountCents") == r2.json.get("paidAmountCents") == 20000
