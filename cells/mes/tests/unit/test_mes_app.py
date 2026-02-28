"""MES 单元测试：工单、生产订单、报工、生产入库、质检、看板、设备遥测。"""
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
    assert r.json["cell"] == "mes"

def test_work_order_and_production_order(client):
    r = client.post("/work-orders", json={"orderNo": "WO001", "productCode": "P1", "qty": 10}, headers=h(req_id="wo-1"))
    assert r.status_code == 201
    wo_id = r.json["workOrderId"]
    r2 = client.post("/production-orders", json={"workshopId": "WS1", "orderNo": "PO001", "productSku": "P1", "quantity": 10}, headers=h(req_id="po-1"))
    assert r2.status_code == 201
    order_id = r2.json["orderId"]
    r3 = client.patch(f"/work-orders/{wo_id}", json={"status": 2}, headers=h())
    assert r3.status_code == 200

def test_quality_inspections(client):
    r = client.post("/production-orders", json={"workshopId": "WS1", "orderNo": "QP001", "productSku": "P1", "quantity": 5}, headers=h(req_id="qp-po-1"))
    assert r.status_code == 201
    order_id = r.json["orderId"]
    r2 = client.get("/quality-inspections", headers=h())
    assert r2.status_code == 200
    assert "data" in r2.json and "total" in r2.json
    r3 = client.post("/quality-inspections", json={"orderId": order_id, "lotNumber": "LOT-Q1", "result": "PASS", "defectCode": ""}, headers=h(req_id="qi-1"))
    assert r3.status_code == 201
    assert r3.json.get("inspectionId") and r3.json.get("orderId") == order_id
    r4 = client.get("/quality-inspections", headers=h())
    assert r4.status_code == 200
    assert r4.json["total"] >= 1

def test_board(client):
    r = client.get("/board", headers=h())
    assert r.status_code == 200
    data = r.json
    assert "workOrdersByStatus" in data or "productionOrdersByStatus" in data or "capacityStats" in data or "orderProgress" in data

def test_device_telemetry(client):
    r = client.post("/devices/telemetry", json={"deviceId": "D1", "metric": "temperature", "value": 36.5}, headers=h())
    assert r.status_code == 202
    r2 = client.get("/devices/telemetry", headers=h())
    assert r2.status_code == 200
    assert "data" in r2.json
    r3 = client.get("/devices/telemetry?deviceId=D1&limit=10", headers=h())
    assert r3.status_code == 200

def test_production_inbound(client):
    r = client.post("/production-orders", json={"workshopId": "WS1", "orderNo": "IB-PO1", "productSku": "P1", "quantity": 20}, headers=h(req_id="ib-po-1"))
    assert r.status_code == 201
    order_id = r.json["orderId"]
    r2 = client.post("/production-inbounds", json={"orderId": order_id, "warehouseId": "WH1", "quantity": 20, "lotNumber": "LOT-IN"}, headers=h(req_id="pin-1"))
    assert r2.status_code == 201
    assert r2.json.get("inboundId") and r2.json.get("orderId") == order_id

def test_production_orders_list_and_material_issue(client):
    r = client.post("/production-orders", json={"workshopId": "WS1", "orderNo": "PO-L1", "productSku": "P1", "quantity": 10}, headers=h(req_id="po-l1"))
    assert r.status_code == 201
    order_id = r.json["orderId"]
    r2 = client.get("/production-orders", headers=h())
    assert r2.status_code == 200
    assert r2.json.get("total", 0) >= 1
    r3 = client.post("/material-issues", json={"orderId": order_id, "materialSku": "M1", "requiredQty": 5}, headers=h())
    assert r3.status_code == 201
    assert r3.json.get("issueId")

def test_work_report_batch(client):
    r = client.post("/production-orders", json={"workshopId": "WS1", "orderNo": "PO-WR", "productSku": "P1", "quantity": 5}, headers=h(req_id="po-wr"))
    assert r.status_code == 201
    order_id = r.json["orderId"]
    r2 = client.post("/work-reports/batch", json={"orderId": order_id, "items": [{"operationCode": "OP1", "completedQty": 5}]}, headers=h(req_id="wr-batch"))
    assert r2.status_code == 201
    assert r2.json.get("count", 0) >= 1

def test_quality_inspection_list_filter(client):
    r = client.get("/quality-inspections?orderId=non-existent", headers=h())
    assert r.status_code == 200
    assert r.json.get("total", 0) >= 0

def test_config_retention_and_metrics(client):
    r = client.get("/config/retention", headers=h())
    assert r.status_code == 200
    assert "operationLogRetentionDays" in r.json
    r2 = client.get("/metrics", headers=h())
    assert r2.status_code == 200
    assert r2.json.get("cell") == "mes"

def test_trace_by_lot_and_order(client):
    r = client.get("/trace/lot/LOT-X", headers=h())
    assert r.status_code == 200
    r2 = client.get("/trace/order/ord-none", headers=h())
    assert r2.status_code == 200

def test_event_publish_production_inbound(client):
    """跨细胞协作：生产入库完成后应发布 mes.production_inbound.completed 事件（通过 mock 断言 payload）。"""
    try:
        from unittest.mock import patch
    except ImportError:
        import sys
        if sys.version_info[0] >= 3:
            from unittest.mock import patch
        else:
            return
    with patch("src.app._events.publish") as mock_publish:
        mock_publish.return_value = True
        r = client.post("/production-orders", json={"workshopId": "WS1", "orderNo": "EV-PO1", "productSku": "P1", "quantity": 5}, headers=h(req_id="ev-po-1"))
        assert r.status_code == 201
        order_id = r.json["orderId"]
        r2 = client.post("/production-inbounds", json={"orderId": order_id, "warehouseId": "WH1", "quantity": 5, "lotNumber": "LOT-EV"}, headers=h(req_id="ev-pin-1"))
        assert r2.status_code == 201
        mock_publish.assert_called()
        call_args = mock_publish.call_args
        assert call_args[0][0] == "mes.production_inbound.completed"
        data = call_args[0][1]
        assert data.get("orderId") == order_id and data.get("warehouseId") == "WH1" and data.get("quantity") == 5
