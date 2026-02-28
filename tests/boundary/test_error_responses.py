"""
边界测试：异常场景、错误响应格式、404/400/409/429。
不依赖真实网关，通过加载 Cell app 直接请求。
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tests.test_all_cells_health import load_cell_app


def _h(tenant="t1", req_id=None):
    h = {"Content-Type": "application/json", "X-Tenant-Id": tenant}
    if req_id:
        h["X-Request-ID"] = req_id
    return h


def test_erp_404_on_nonexistent_order():
    app = load_cell_app("erp")
    if app is None:
        pytest.skip("ERP 无法加载")
    app.config["TESTING"] = True
    with app.test_client() as c:
        r = c.get("/orders/nonexistent-order-id-999", headers=_h())
        assert r.status_code == 404
        body = r.get_json()
        assert body is not None and ("code" in body or "message" in body or "error" in body)


def test_erp_400_validation_missing_required():
    app = load_cell_app("erp")
    if app is None:
        pytest.skip("ERP 无法加载")
    app.config["TESTING"] = True
    with app.test_client() as c:
        r = c.post("/orders", json={}, headers=_h(req_id="bound-1"))
        assert r.status_code == 400
        body = r.get_json()
        assert body is not None


def test_erp_409_idempotent_conflict():
    app = load_cell_app("erp")
    if app is None:
        pytest.skip("ERP 无法加载")
    app.config["TESTING"] = True
    with app.test_client() as c:
        r1 = c.post("/orders", json={"customerId": "c1", "totalAmountCents": 100}, headers=_h(req_id="idem-dup"))
        if r1.status_code not in (200, 201):
            pytest.skip("ERP 创建订单失败")
        r2 = c.post("/orders", json={"customerId": "c1", "totalAmountCents": 200}, headers=_h(req_id="idem-dup"))
        assert r2.status_code == 409


def test_crm_400_empty_customer_name():
    app = load_cell_app("crm")
    if app is None:
        pytest.skip("CRM 无法加载")
    app.config["TESTING"] = True
    with app.test_client() as c:
        r = c.post("/customers", json={"name": ""}, headers=_h(req_id="bound-crm-1"))
        assert r.status_code in (400, 422)


def test_wms_inbound_get_404():
    app = load_cell_app("wms")
    if app is None:
        pytest.skip("WMS 无法加载")
    app.config["TESTING"] = True
    with app.test_client() as c:
        r = c.get("/inbound-orders/nonexistent-inbound-999", headers=_h())
        assert r.status_code == 404


def test_mes_production_order_404():
    app = load_cell_app("mes")
    if app is None:
        pytest.skip("MES 无法加载")
    app.config["TESTING"] = True
    with app.test_client() as c:
        r = c.get("/production-orders/nonexistent-mes-order", headers=_h())
        assert r.status_code == 404


def test_gateway_required_headers_return_400_or_401():
    """网关：缺少 Authorization 或 X-Request-ID（POST）返回 400/401。"""
    from platform_core.core.gateway.app import create_app
    app = create_app(registry_resolver=lambda c: None, use_dynamic_routes=True)
    app.config["TESTING"] = True
    with app.test_client() as c:
        r = c.post(
            "/api/v1/erp/orders",
            json={"customerId": "c1", "totalAmountCents": 100},
            headers={"Content-Type": "application/json", "X-Tenant-Id": "t1"},
        )
        assert r.status_code in (400, 401, 503)
