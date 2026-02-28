"""WMS Store 单元测试：入库/出库、库存、批次、幂等。"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import pytest
from src.store import WMSStore


@pytest.fixture
def store():
    return WMSStore()


def test_inbound_create_with_source_and_erp_order_id(store):
    o = store.inbound_create("t1", "WH01", "production", source_order_id="mes-1", erp_order_id="erp-1")
    assert o["orderId"] and o["typeCode"] == "production"
    assert o.get("sourceOrderId") == "mes-1" and o.get("erpOrderId") == "erp-1"


def test_inbound_add_line_and_get(store):
    o = store.inbound_create("t1", "WH01", "purchase")
    line = store.inbound_add_line("t1", o["orderId"], "SKU1", 10)
    assert line is not None and line["skuId"] == "SKU1" and line["quantity"] == 10
    ib = store.inbound_get("t1", o["orderId"])
    assert ib is not None and len(ib.get("lines", [])) >= 1


def test_outbound_create_and_update_status(store):
    o = store.outbound_create("t1", "WH01", "sales", source_order_id="so-1", erp_order_id="erp-1")
    assert o["orderId"] and o.get("erpOrderId") == "erp-1"
    updated = store.outbound_update_status("t1", o["orderId"], 3)
    assert updated is not None and updated["status"] == 3


def test_inventory_add_and_get(store):
    store.inventory_add("t1", "WH01", "SKU1", 100)
    store.inventory_add("t1", "WH01", "SKU1", 50)
    inv = store.inventory_get("t1", "WH01", "SKU1")
    assert isinstance(inv, list) and len(inv) >= 1 and inv[0].get("quantity") == 150


def test_idem(store):
    store.idem_set("req-1", "ob-1")
    assert store.idem_get("req-1") == "ob-1"


def test_inbound_list_filter_by_warehouse_and_status(store):
    store.inbound_create("t1", "WH01", "purchase")
    store.inbound_create("t1", "WH02", "purchase")
    lst = store.inbound_list("t1", warehouse_id="WH01")
    assert all(o["warehouseId"] == "WH01" for o in lst)
