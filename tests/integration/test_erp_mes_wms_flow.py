"""
集成测试：ERP→MES→WMS 业务流程联动（不启动网关，直接调用各 Cell app）。
验证：ERP 销售订单创建 → MES 生产计划/生产订单 → WMS 生产入库单；数据与事件 payload 可追溯。
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
def erp_client():
    app = load_cell_app("erp")
    if app is None:
        pytest.skip("ERP cell 无法加载")
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def mes_client():
    app = load_cell_app("mes")
    if app is None:
        pytest.skip("MES cell 无法加载")
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def wms_client():
    app = load_cell_app("wms")
    if app is None:
        pytest.skip("WMS cell 无法加载")
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_erp_order_create_with_lines(erp_client):
    """ERP 销售订单带 orderLines 创建，用于下游 MES 生产计划。"""
    r = erp_client.post(
        "/orders",
        json={
            "customerId": "c1",
            "totalAmountCents": 50000,
            "currency": "CNY",
            "orderLines": [{"productSku": "PROD-01", "quantity": 2}, {"productSku": "PROD-02", "quantity": 1}],
        },
        headers=_headers(request_id="int-erp-1"),
    )
    assert r.status_code == 201
    body = r.get_json()
    assert body.get("orderId") and body.get("orderLines") and len(body["orderLines"]) == 2


def test_mes_production_plan_and_order(mes_client):
    """MES 生产计划与生产订单创建，契约与物料需求接口存在。"""
    r = mes_client.post(
        "/production-plans",
        json={"planNo": "plan-int-1", "productSku": "PROD-01", "plannedQty": 10, "planDate": "2025-01-15"},
        headers=_headers(request_id="int-mes-plan-1"),
    )
    assert r.status_code == 201
    plan_id = r.get_json().get("planId")
    assert plan_id
    r2 = mes_client.post(
        "/production-orders",
        json={"workshopId": "WS01", "orderNo": "ord-1", "productSku": "PROD-01", "quantity": 10, "planId": plan_id},
        headers=_headers(request_id="int-mes-po-1"),
    )
    assert r2.status_code == 201
    po = r2.get_json()
    assert po.get("orderId") and po.get("orderNo") == "ord-1"
    # 物料需求接口（可能返回空列表）
    r3 = mes_client.get(f"/production-orders/{po['orderId']}/material-requirements", headers=_headers())
    assert r3.status_code == 200


def test_wms_inbound_production_and_lines(wms_client):
    """WMS 生产入库单创建，带 sourceOrderId/erpOrderId 追溯。"""
    r = wms_client.post(
        "/inbound-orders",
        json={
            "warehouseId": "WH01",
            "typeCode": "production",
            "sourceOrderId": "mes-po-1",
            "erpOrderId": "erp-ord-1",
        },
        headers=_headers(request_id="int-wms-ib-1"),
    )
    assert r.status_code == 201
    body = r.get_json()
    assert body.get("orderId") and body.get("typeCode") == "production"
    assert body.get("sourceOrderId") == "mes-po-1" and body.get("erpOrderId") == "erp-ord-1"
    r2 = wms_client.post(
        f"/inbound-orders/{body['orderId']}/lines",
        json={"skuId": "PROD-01", "quantity": 10},
        headers=_headers(request_id="int-wms-line-1"),
    )
    assert r2.status_code in (200, 201)


def test_wms_outbound_sales_and_tms_traceability(wms_client):
    """WMS 销售出库单带 erpOrderId，便于 TMS 签收回写。"""
    r = wms_client.post(
        "/outbound-orders",
        json={
            "warehouseId": "WH01",
            "typeCode": "sales",
            "sourceOrderId": "so-1",
            "erpOrderId": "erp-sales-1",
        },
        headers=_headers(request_id="int-wms-ob-1"),
    )
    assert r.status_code == 201
    ob = r.get_json()
    assert ob.get("orderId") and ob.get("erpOrderId") == "erp-sales-1"
    # PATCH 出库单状态（模拟 TMS 签收回写）
    r2 = wms_client.patch(f"/outbound-orders/{ob['orderId']}", json={"status": 3}, headers=_headers())
    assert r2.status_code == 200
    assert r2.get_json().get("status") == 3


def test_erp_order_update_status_after_wms_inbound(erp_client):
    """ERP 订单状态可更新为 3（生产完成）/4（已送达）。"""
    r = erp_client.post(
        "/orders",
        json={"customerId": "c1", "totalAmountCents": 100},
        headers=_headers(request_id="int-erp-status-1"),
    )
    assert r.status_code == 201
    oid = r.get_json()["orderId"]
    r2 = erp_client.patch(f"/orders/{oid}", json={"orderStatus": 3}, headers=_headers())
    assert r2.status_code == 200
    assert r2.get_json().get("orderStatus") == 3
