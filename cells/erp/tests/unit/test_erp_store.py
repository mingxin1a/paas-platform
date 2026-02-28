"""ERP Store 单元测试：订单、GL、AR/AP、幂等、分页、审计。"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import pytest
from src.store import ERPStore


@pytest.fixture
def store():
    return ERPStore()


def test_order_create_and_list(store):
    o = store.order_create("t1", "c1", 10000, "CNY")
    assert o["orderId"] and o["tenantId"] == "t1" and o["customerId"] == "c1"
    assert o["totalAmountCents"] == 10000 and o["orderStatus"] == 1
    items, total = store.order_list("t1")
    assert total >= 1 and any(x["orderId"] == o["orderId"] for x in items)


def test_order_create_with_lines(store):
    o = store.order_create("t1", "c1", 20000, "CNY", order_lines=[{"productSku": "SKU1", "quantity": 2}, {"productSku": "SKU2", "quantity": 1}])
    assert "orderLines" in o and len(o["orderLines"]) == 2
    assert o["orderLines"][0]["productSku"] == "SKU1" and o["orderLines"][0]["quantity"] == 2


def test_order_get_soft_delete(store):
    o = store.order_create("t1", "c1", 100)
    oid = o["orderId"]
    assert store.order_get("t1", oid) is not None
    store.order_soft_delete("t1", oid)
    assert store.order_get("t1", oid) is None


def test_order_update_status(store):
    o = store.order_create("t1", "c1", 100)
    updated = store.order_update_status("t1", o["orderId"], 2)
    assert updated is not None and updated["orderStatus"] == 2


def test_idem_get_set(store):
    store.idem_set("req-1", "ord-1")
    assert store.idem_get("req-1") == "ord-1"
    assert store.idem_get("req-2") is None


def test_gl_account_and_journal(store):
    store.gl_account_create("t1", "1001", "现金", 1)
    items, _ = store.gl_account_list("t1")
    assert any(a["accountCode"] == "1001" for a in items)
    e = store.gl_entry_create("t1", "J001", "2025-01-01", [
        {"accountCode": "1001", "debitCents": 1000, "creditCents": 0},
        {"accountCode": "4001", "debitCents": 0, "creditCents": 1000},
    ])
    assert e["entryId"] and e["totalDebitCents"] == 1000 and e["totalCreditCents"] == 1000


def test_paginate(store):
    for i in range(5):
        store.order_create("t1", f"c{i}", 100 * i)
    page1, total = store.order_list("t1", page=1, page_size=2)
    assert len(page1) <= 2 and total >= 5
    page2, _ = store.order_list("t1", page=2, page_size=2)
    assert len(page2) <= 2


def test_audit_append_and_list(store):
    store.audit_append("t1", "u1", "order.create", 1, "trace-1", "order", "ord-1")
    out, total = store.audit_list("t1", page=1, page_size=10)
    assert total >= 1 and any(e.get("resourceType") == "order" for e in out)


def test_ar_ap_create(store):
    ar = store.ar_create("t1", "c1", "AR001", 50000)
    assert ar["invoiceId"] and ar["amountCents"] == 50000
    ap = store.ap_create("t1", "s1", "AP001", 30000)
    assert ap["invoiceId"] and ap["supplierId"] == "s1"


def test_order_get_wrong_tenant_returns_none(store):
    o = store.order_create("t1", "c1", 100)
    assert store.order_get("t2", o["orderId"]) is None
