"""TMS 单元测试：运单、轨迹、路线规划、看板、对账。"""
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
    assert r.json["cell"] == "tms"

def test_shipment_and_tracks(client):
    r = client.post("/shipments", json={"trackingNo": "TN001", "origin": "A", "destination": "B"}, headers=h(req_id="sh-1"))
    assert r.status_code == 201
    sid = r.json["shipmentId"]
    r2 = client.post("/tracks", json={"shipmentId": sid, "lat": "31.2", "lng": "121.5", "nodeName": "上海"}, headers=h(req_id="tr-1"))
    assert r2.status_code == 201
    r3 = client.get("/tracks", headers=h())
    assert r3.status_code == 200
    assert any(t.get("shipmentId") == sid for t in r3.json.get("data", []))

def test_route_plan(client):
    r = client.post("/routes/plan", json={"fromAddress": "上海仓", "toAddress": "北京仓", "shipmentId": ""}, headers=h(req_id="rp-1"))
    assert r.status_code == 201
    assert r.json.get("routePlanId") and r.json.get("waypoints")
    r2 = client.get("/routes/plan", headers=h())
    assert r2.status_code == 200
    assert "data" in r2.json and r2.json["total"] >= 1

def test_board(client):
    r = client.get("/board", headers=h())
    assert r.status_code == 200
    data = r.json
    assert "shipmentsByStatus" in data or "totalShipments" in data or "transportCostTotalCents" in data

def test_shipment_status_update(client):
    r = client.post("/shipments", json={"trackingNo": "TN002", "origin": "X", "destination": "Y"}, headers=h(req_id="sh-2"))
    assert r.status_code == 201
    sid = r.json["shipmentId"]
    r2 = client.patch(f"/shipments/{sid}", json={"status": 2}, headers=h())
    assert r2.status_code == 200
    assert r2.json.get("status") == 2

def test_reconciliation(client):
    r = client.get("/reconciliations", headers=h())
    assert r.status_code == 200
    r2 = client.post("/reconciliations", json={"periodStart": "2025-01-01", "periodEnd": "2025-01-31", "totalAmountCents": 100000}, headers=h(req_id="rec-1"))
    assert r2.status_code == 201

def test_delivery_confirm_and_transport_cost(client):
    r = client.post("/shipments", json={"trackingNo": "TN-DC", "origin": "A", "destination": "B"}, headers=h(req_id="sh-dc"))
    assert r.status_code == 201
    sid = r.json["shipmentId"]
    r2 = client.post("/delivery-confirm", json={"shipmentId": sid, "status": "confirmed"}, headers=h(req_id="dc-1"))
    assert r2.status_code == 201
    r3 = client.post("/transport-costs", json={"shipmentId": sid, "amountCents": 5000, "costType": "freight"}, headers=h(req_id="tc-1"))
    assert r3.status_code == 201
    r4 = client.get("/transport-costs", headers=h())
    assert r4.status_code == 200

def test_config_retention_and_metrics(client):
    r = client.get("/config/retention", headers=h())
    assert r.status_code == 200
    r2 = client.get("/metrics", headers=h())
    assert r2.status_code == 200
    assert r2.json.get("cell") == "tms"

def test_vehicles_and_drivers(client):
    r = client.get("/vehicles", headers=h())
    assert r.status_code == 200
    r2 = client.get("/drivers", headers=h())
    assert r2.status_code == 200

def test_event_publish_shipment_dispatched_delivered(client):
    """跨细胞协作：运单状态改为 2 发布 dispatched；到货确认发布 delivered。"""
    from unittest.mock import patch
    with patch("src.app._events.publish") as mock_publish:
        mock_publish.return_value = True
        r = client.post("/shipments", json={"trackingNo": "EV-TN", "origin": "O", "destination": "D"}, headers=h(req_id="ev-sh-1"))
        assert r.status_code == 201
        sid = r.json["shipmentId"]
        client.patch(f"/shipments/{sid}", json={"status": 2}, headers=h())
        calls = [c[0][0] for c in mock_publish.call_args_list]
        assert "tms.shipment.dispatched" in calls
        mock_publish.reset_mock()
        client.post("/delivery-confirm", json={"shipmentId": sid, "status": "confirmed"}, headers=h(req_id="ev-dc-1"))
        calls2 = [c[0][0] for c in mock_publish.call_args_list]
        assert "tms.shipment.delivered" in calls2
