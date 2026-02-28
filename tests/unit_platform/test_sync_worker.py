"""
Sync Worker 单元测试：dispatch 分发、各 handler 逻辑（通过 mock _req 不发起真实 HTTP）。
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


@pytest.fixture(autouse=True)
def mock_link_env(monkeypatch):
    """默认开启联动，便于测试 handler 被调用。"""
    monkeypatch.setenv("LINK_CRM_TO_ERP", "1")
    monkeypatch.setenv("LINK_ERP_TO_MES", "1")
    monkeypatch.setenv("LINK_MES_TO_WMS", "1")
    monkeypatch.setenv("LINK_WMS_TO_TMS", "1")
    monkeypatch.setenv("LINK_ALL_TO_OA", "1")
    monkeypatch.setenv("LINK_ALL_TO_DATALAKE", "0")  # 测试中不请求数据湖
    monkeypatch.setenv("GATEWAY_URL", "http://localhost:8000")


def test_dispatch_unknown_event_type():
    """未知事件类型不抛错，且 LINK_ALL_TO_DATALAKE=0 时不请求。"""
    import platform_core.sync_worker.worker as w
    w.dispatch("unknown.event.type", {"tenantId": "t1"})


def test_dispatch_crm_contract_signed(monkeypatch):
    """crm.contract.signed 触发 ERP 下单与 OA 审批（mock _req）。"""
    import platform_core.sync_worker.worker as w
    calls = []
    def fake_req(method, url, body=None, tenant_id="default"):
        calls.append((method, url, body))
        if "erp/orders" in url:
            return 201, {"orderId": "ord-1"}
        if "oa/approvals" in url:
            return 201, {}
        return 200, {}
    monkeypatch.setattr(w, "_req", fake_req)
    w.dispatch("crm.contract.signed", {
        "tenantId": "t1", "customerId": "c1", "contractId": "con-1",
        "amountCents": 10000, "currency": "CNY",
    })
    assert any("erp/orders" in u for _, u, _ in calls)
    assert any("oa/approvals" in u for _, u, _ in calls)


def test_dispatch_erp_order_created(monkeypatch):
    """erp.order.created 触发 OA 与 MES 计划/生产订单（mock _req）。"""
    import platform_core.sync_worker.worker as w
    calls = []
    def fake_req(method, url, body=None, tenant_id="default"):
        calls.append((method, url, body))
        if "production-plans" in url:
            return 201, {"planId": "plan-1"}
        if "production-orders" in url:
            return 201, {"orderId": "po-1"}
        if "oa/approvals" in url:
            return 201, {}
        return 200, {}
    monkeypatch.setattr(w, "_req", fake_req)
    w.dispatch("erp.order.created", {
        "tenantId": "t1", "orderId": "erp-ord-1", "customerId": "c1",
        "orderLines": [{"productSku": "SKU1", "quantity": 2}],
    })
    assert any("production-plans" in u for _, u, _ in calls)
    assert any("production-orders" in u for _, u, _ in calls)


def test_dispatch_wms_inbound_completed_production(monkeypatch):
    """wms.inbound.completed typeCode=production 回写 ERP 订单状态。"""
    import platform_core.sync_worker.worker as w
    calls = []
    def fake_req(method, url, body=None, tenant_id="default"):
        calls.append((method, url, body))
        return 200, {}
    monkeypatch.setattr(w, "_req", fake_req)
    w.dispatch("wms.inbound.completed", {
        "tenantId": "t1", "orderId": "wms-ib-1", "typeCode": "production", "erpOrderId": "erp-1",
    })
    assert any("erp/orders" in u and "erp-1" in u for _, u, _ in calls)
    assert any(b and b.get("orderStatus") == 3 for _, _, b in calls if b)


def test_dispatch_wms_inbound_completed_non_production(monkeypatch):
    """wms.inbound.completed typeCode=purchase 不回写 ERP。"""
    import platform_core.sync_worker.worker as w
    calls = []
    def fake_req(method, url, body=None, tenant_id="default"):
        calls.append(url)
        return 200, {}
    monkeypatch.setattr(w, "_req", fake_req)
    w.dispatch("wms.inbound.completed", {
        "tenantId": "t1", "orderId": "wms-ib-1", "typeCode": "purchase", "erpOrderId": "erp-1",
    })
    assert not any("erp/orders" in u for u in calls)


def test_dispatch_tms_shipment_delivered(monkeypatch):
    """tms.shipment.delivered 回写 WMS 出库与 ERP 订单状态。"""
    import platform_core.sync_worker.worker as w
    calls = []
    def fake_req(method, url, body=None, tenant_id="default"):
        calls.append((method, url, body))
        return 200, {}
    monkeypatch.setattr(w, "_req", fake_req)
    w.dispatch("tms.shipment.delivered", {
        "tenantId": "t1", "wmsOutboundOrderId": "wms-ob-1", "erpOrderId": "erp-1",
    })
    assert any("wms/outbound-orders" in u and "wms-ob-1" in u for _, u, _ in calls)
    assert any("erp/orders" in u and "erp-1" in u for _, u, _ in calls)


def test_run_once_returns_since_when_non_200(monkeypatch):
    """run_once 在 GET /api/events 非 200 时返回原 since。"""
    import platform_core.sync_worker.worker as w
    monkeypatch.setattr(w, "_req", lambda method, url, body=None, tenant_id="default": (500, {}))
    out = w.run_once(0.0)
    assert out == 0.0
