"""
集成测试：WMS→TMS 业务流程（出库单同步运输、签收回写）。
不启动网关，直接调用 WMS / TMS Cell app。
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tests.test_all_cells_health import load_cell_app


def _headers(tenant="t1", request_id=None):
    h = {"Content-Type": "application/json", "X-Tenant-Id": tenant}
    if request_id:
        h["X-Request-ID"] = request_id
    return h


@pytest.fixture
def wms_client():
    app = load_cell_app("wms")
    if app is None:
        pytest.skip("WMS cell 无法加载")
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def tms_client():
    app = load_cell_app("tms")
    if app is None:
        pytest.skip("TMS cell 无法加载")
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_tms_shipment_create_with_wms_and_erp_ids(tms_client):
    """TMS 运单创建支持 wmsOutboundOrderId、erpOrderId 用于签收回写。"""
    r = tms_client.post(
        "/shipments",
        json={
            "trackingNo": "TN-001",
            "origin": "WH01",
            "destination": "客户A",
            "wmsOutboundOrderId": "wms-ob-1",
            "erpOrderId": "erp-1",
        },
        headers=_headers(request_id="int-tms-1"),
    )
    assert r.status_code == 201
    s = r.get_json()
    assert s.get("shipmentId") and s.get("wmsOutboundOrderId") == "wms-ob-1" and s.get("erpOrderId") == "erp-1"


def test_tms_delivery_confirm(tms_client):
    """TMS 签收确认接口存在且返回 201。"""
    r = tms_client.post(
        "/shipments",
        json={"origin": "A", "destination": "B"},
        headers=_headers(request_id="int-tms-ship-1"),
    )
    assert r.status_code == 201
    sid = r.get_json()["shipmentId"]
    r2 = tms_client.post(
        "/delivery-confirm",
        json={"shipmentId": sid, "confirmId": "cf-1", "status": "confirmed"},
        headers=_headers(request_id="int-tms-cf-1"),
    )
    assert r2.status_code in (200, 201)
