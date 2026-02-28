"""WMS 单元测试：库存、入库、出库、库位、批次 API。"""
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
    assert r.json["cell"] == "wms"

def test_inbound_outbound_flow(client):
    r = client.post("/inbound-orders", json={"warehouseId": "WH01"}, headers=h(req_id="ib-1"))
    assert r.status_code == 201
    ib_id = r.json["orderId"]
    r2 = client.post("/inbound-orders/" + ib_id + "/lines", json={"skuId": "SKU01", "quantity": 100, "lotNumber": "L001"}, headers=h(req_id="ib-l1"))
    assert r2.status_code == 201
    r3 = client.post("/inbound-orders/" + ib_id + "/receive", json={"lineId": r2.json["lineId"], "receivedQuantity": 50, "warehouseId": "WH01"}, headers=h())
    assert r3.status_code == 200
    r4 = client.get("/inventory?warehouseId=WH01", headers=h())
    assert r4.status_code == 200
    assert any(x["skuId"] == "SKU01" and x["quantity"] == 50 for x in r4.json["data"])

def test_locations_and_lots(client):
    r = client.post("/locations", json={"locationId": "A-01-01", "warehouseId": "WH01"}, headers=h(req_id="loc-1"))
    assert r.status_code == 201
    r2 = client.get("/lots?skuId=SKU01", headers=h())
    assert r2.status_code == 200
    r3 = client.get("/lots/fifo?warehouseId=WH01&skuId=SKU01&quantity=10", headers=h())
    assert r3.status_code == 200

def test_waves_and_board(client):
    r = client.post("/outbound-orders", json={"warehouseId": "WH01"}, headers=h(req_id="ob-wave-1"))
    assert r.status_code == 201
    ob_id = r.json["orderId"]
    client.post("/outbound-orders/" + ob_id + "/lines", json={"skuId": "SKU01", "quantity": 5}, headers=h(req_id="ob-l-wave-1"))
    r2 = client.post("/waves", json={"warehouseId": "WH01", "outboundOrderIds": [ob_id]}, headers=h(req_id="wave-1"))
    assert r2.status_code == 201
    wave_id = r2.json["waveId"]
    r3 = client.get("/waves/" + wave_id + "/picks", headers=h())
    assert r3.status_code == 200
    assert "data" in r3.json
    r4 = client.get("/board", headers=h())
    assert r4.status_code == 200
    assert "inboundPending" in r4.json or "outboundPending" in r4.json or "inventoryTotalQuantity" in r4.json

def test_scan_inbound_outbound(client):
    r = client.post("/inbound-orders", json={"warehouseId": "WH01"}, headers=h(req_id="scan-ib-1"))
    assert r.status_code == 201
    ib_id = r.json["orderId"]
    client.post("/inbound-orders/" + ib_id + "/lines", json={"skuId": "BARCODE-X", "quantity": 10}, headers=h(req_id="scan-ib-l1"))
    r2 = client.post("/scan/inbound", json={"orderId": ib_id, "barcode": "BARCODE-X", "quantity": 10}, headers=h())
    assert r2.status_code == 200
    assert r2.json.get("accepted") is True

def test_wave_confirm_pick(client):
    r = client.post("/outbound-orders", json={"warehouseId": "WH01"}, headers=h(req_id="ob-cp-1"))
    assert r.status_code == 201
    ob_id = r.json["orderId"]
    client.post("/outbound-orders/" + ob_id + "/lines", json={"skuId": "SKU01", "quantity": 3}, headers=h(req_id="ob-cp-l1"))
    r2 = client.post("/waves", json={"warehouseId": "WH01", "outboundOrderIds": [ob_id]}, headers=h(req_id="wave-cp-1"))
    assert r2.status_code == 201
    wave_id = r2.json["waveId"]
    r3 = client.get("/waves/" + wave_id + "/picks", headers=h())
    assert r3.status_code == 200
    picks = r3.json.get("data") or []
    if picks:
        pick_line_id = picks[0].get("pickLineId")
        client.post("/waves/" + wave_id + "/confirm-pick", json={"pickLineId": pick_line_id, "pickedQuantity": 1}, headers=h(req_id="cp-1"))
    r4 = client.get("/waves", headers=h())
    assert r4.status_code == 200

def test_config_retention_and_metrics(client):
    r = client.get("/config/retention", headers=h())
    assert r.status_code == 200
    r2 = client.get("/metrics", headers=h())
    assert r2.status_code == 200
    assert r2.json.get("cell") == "wms"

def test_transfers_and_alerts(client):
    r = client.get("/transfers", headers=h())
    assert r.status_code == 200
    r2 = client.get("/alerts/expiry", headers=h())
    assert r2.status_code == 200

def test_cycle_count_and_inbound_outbound_get(client):
    r = client.get("/cycle-counts", headers=h())
    assert r.status_code == 200
    r2 = client.post("/inbound-orders", json={"warehouseId": "WH01"}, headers=h(req_id="get-ib-1"))
    assert r2.status_code == 201
    ib_id = r2.json["orderId"]
    r3 = client.get("/inbound-orders/" + ib_id, headers=h())
    assert r3.status_code == 200
    r4 = client.post("/outbound-orders", json={"warehouseId": "WH01"}, headers=h(req_id="get-ob-1"))
    assert r4.status_code == 201
    r5 = client.get("/outbound-orders/" + r4.json["orderId"], headers=h())
    assert r5.status_code == 200

def test_locations_get_and_inventory(client):
    r = client.get("/locations?warehouseId=WH01", headers=h())
    assert r.status_code == 200
    client.post("/locations", json={"locationId": "B-02-01", "warehouseId": "WH01"}, headers=h(req_id="loc-g1"))
    r2 = client.get("/inventory", headers=h())
    assert r2.status_code == 200

def test_event_publish_inbound_outbound(client):
    """跨细胞协作：入库收货/出库发货后应发布 wms.inbound.completed / wms.outbound.completed。"""
    from unittest.mock import patch
    with patch("src.app._events.publish") as mock_publish:
        mock_publish.return_value = True
        r = client.post("/inbound-orders", json={"warehouseId": "WH01"}, headers=h(req_id="ev-ib-1"))
        assert r.status_code == 201
        ib_id = r.json["orderId"]
        rl = client.post("/inbound-orders/" + ib_id + "/lines", json={"skuId": "S1", "quantity": 10}, headers=h(req_id="ev-ib-l1"))
        line_id = rl.json["lineId"]
        client.post("/inbound-orders/" + ib_id + "/receive", json={"lineId": line_id, "receivedQuantity": 10, "warehouseId": "WH01"}, headers=h())
        calls = [c[0][0] for c in mock_publish.call_args_list]
        assert "wms.inbound.completed" in calls
        mock_publish.reset_mock()
        r2 = client.post("/outbound-orders", json={"warehouseId": "WH01"}, headers=h(req_id="ev-ob-1"))
        ob_id = r2.json["orderId"]
        rl2 = client.post("/outbound-orders/" + ob_id + "/lines", json={"skuId": "S1", "quantity": 5}, headers=h(req_id="ev-ob-l1"))
        client.post("/outbound-orders/" + ob_id + "/ship", json={"lineId": rl2.json["lineId"], "pickedQuantity": 5, "warehouseId": "WH01"}, headers=h())
        calls2 = [c[0][0] for c in mock_publish.call_args_list]
        assert "wms.outbound.completed" in calls2
