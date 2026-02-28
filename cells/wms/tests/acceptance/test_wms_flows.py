"""WMS 验收测试：入库 -> 库存 -> 出库 -> 批次 FIFO。"""
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

def h(tenant="acceptance-wms", req_id=None):
    headers = {"Content-Type": "application/json", "X-Tenant-Id": tenant}
    if req_id:
        headers["X-Request-ID"] = req_id
    return headers

def test_full_inbound_inventory_outbound(client):
    r = client.post("/inbound-orders", json={"warehouseId": "WH-ACC"}, headers=h(req_id="acc-ib-1"))
    assert r.status_code == 201
    ib_id = r.json["orderId"]
    r2 = client.post("/inbound-orders/" + ib_id + "/lines", json={"skuId": "S1", "quantity": 200}, headers=h(req_id="acc-ib-l1"))
    assert r2.status_code == 201
    line_id = r2.json["lineId"]
    r3 = client.post("/inbound-orders/" + ib_id + "/receive", json={"lineId": line_id, "receivedQuantity": 200, "warehouseId": "WH-ACC"}, headers=h())
    assert r3.status_code == 200
    r4 = client.get("/inventory?warehouseId=WH-ACC", headers=h())
    assert r4.status_code == 200
    assert any(x["skuId"] == "S1" and x["quantity"] == 200 for x in r4.json["data"])
    r5 = client.post("/outbound-orders", json={"warehouseId": "WH-ACC"}, headers=h(req_id="acc-ob-1"))
    assert r5.status_code == 201
    ob_id = r5.json["orderId"]
    r6 = client.post("/outbound-orders/" + ob_id + "/lines", json={"skuId": "S1", "quantity": 80}, headers=h(req_id="acc-ob-l1"))
    assert r6.status_code == 201
    client.post("/outbound-orders/" + ob_id + "/ship", json={"lineId": r6.json["lineId"], "pickedQuantity": 80, "warehouseId": "WH-ACC"}, headers=h())
    r7 = client.get("/inventory?warehouseId=WH-ACC&skuId=S1", headers=h())
    assert r7.status_code == 200
    assert any(x["quantity"] == 120 for x in r7.json["data"])
