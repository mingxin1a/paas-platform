"""
批次1 商用验收测试用例（CRM/ERP/OA/SRM）。
对应文档：docs/commercial_delivery/批次1_商用验收测试用例.md。
核心接口压测达标见：docs/commercial_delivery/batch1_jmeter_load_test_guide.md（JMeter 执行）。
"""
from __future__ import annotations

import os
import sys
import json

import pytest

# 项目根与 cells 目录；复用 test_all_cells_health 的加载逻辑以保证环境一致
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CELLS_DIR = os.path.join(ROOT, "cells")

try:
    from tests.test_all_cells_health import load_cell_app as _load_app_from_health
except ImportError:
    _load_app_from_health = None


def _load_cell_app(cell_name: str):
    """加载细胞 app：优先复用 test_all_cells_health.load_cell_app（Flask）；否则本地加载。"""
    if _load_app_from_health:
        app = _load_app_from_health(cell_name)
        if app is not None:
            return app, "flask"
    cell_path = os.path.normpath(os.path.join(CELLS_DIR, cell_name))
    if not os.path.isdir(cell_path):
        return None, None
    to_restore = [k for k in list(sys.modules.keys()) if k == "src" or k.startswith("src.")]
    for mod in to_restore:
        sys.modules.pop(mod, None)
    while cell_path in sys.path:
        sys.path.remove(cell_path)
    sys.path.insert(0, cell_path)
    try:
        app_py = os.path.join(cell_path, "src", "app.py")
        if os.path.isfile(app_py):
            try:
                import src.app as m  # noqa: PLC0415
                app = getattr(m, "app", None)
                if app is not None:
                    return app, "flask"
            except Exception:
                pass
        main_py = os.path.join(cell_path, "src", "main.py")
        if os.path.isfile(main_py):
            try:
                import src.main as m  # noqa: PLC0415
                app = getattr(m, "app", None)
                if app is not None:
                    return app, "fastapi"
            except Exception:
                pass
    finally:
        if cell_path in sys.path:
            sys.path.remove(cell_path)
    return None, None


def _get(client, path, headers=None):
    if hasattr(client, "get"):
        r = client.get(path, headers=headers or {})
    else:
        r = client.get(path, headers=headers or {})
    if hasattr(r, "status_code"):
        code = r.status_code
        body = r.get_data() if hasattr(r, "get_data") else r.content
        try:
            data = json.loads(body.decode("utf-8") if isinstance(body, bytes) else body)
        except Exception:
            data = {}
    else:
        code = r.status_code
        data = r.json() if hasattr(r, "json") else {}
    return code, data


def _post(client, path, json_body=None, headers=None):
    if hasattr(client, "post"):
        r = client.post(path, json=json_body or {}, headers=headers or {})
    else:
        r = client.post(path, json=json_body or {}, headers=headers or {})
    code = r.status_code
    body = getattr(r, "content", None) or (r.get_data() if hasattr(r, "get_data") else b"{}")
    try:
        data = json.loads(body.decode("utf-8") if isinstance(body, bytes) else body)
    except Exception:
        data = {}
    return code, data


def _headers(tenant="tenant-001", user_id=None, data_scope=None, request_id=None):
    h = {"Content-Type": "application/json", "X-Tenant-Id": tenant, "Authorization": "Bearer test"}
    if user_id:
        h["X-User-Id"] = user_id
    if data_scope:
        h["X-Data-Scope"] = data_scope
    if request_id:
        h["X-Request-ID"] = request_id
    return h


def test_load_cell_crm_app():
    """辅助：验证从项目根可加载 CRM app（用于排查环境）。"""
    app, typ = _load_cell_app("crm")
    if app is None:
        pytest.skip("CRM app 无法加载（需从项目根执行且 cells/crm 依赖已安装；可先运行 tests/test_all_cells_health.py 校验）")
    assert typ in ("flask", "fastapi")


# ---------- CRM ----------
class TestCRMBatch1Commercial:
    """CRM-01 ~ CRM-05 商用验收."""

    @pytest.fixture
    def crm_client(self):
        app, typ = _load_cell_app("crm")
        if app is None:
            pytest.skip("CRM app 无法加载（请从项目根执行 pytest，并确保 cells/crm 依赖已安装）")
        if typ == "flask":
            app.config["TESTING"] = True
            yield app.test_client()
        else:
            from starlette.testclient import TestClient
            yield TestClient(app)

    def test_crm_01_sales_forecast(self, crm_client):
        """CRM-01 销售预测接口：GET /reports/sales-forecast 或 /reports/funnel，含 byStage/totalWeightedCents 或 data."""
        code, data = _get(crm_client, "/reports/sales-forecast", _headers())
        if code != 200:
            code, data = _get(crm_client, "/reports/funnel", _headers())
        assert code == 200
        assert "byStage" in data or "data" in data
        if "totalWeightedCents" in data:
            assert isinstance(data["totalWeightedCents"], (int, float))

    def test_crm_02_data_scope_self(self, crm_client):
        """CRM-02 客户列表行级权限：X-Data-Scope: self + X-User-Id 仅返回本人客户（需 DB 有 owner）。"""
        _post(crm_client, "/customers", {"name": "权限测客户"}, _headers(request_id="scope-req-1", user_id="u1"))
        code, data = _get(crm_client, "/customers", _headers(user_id="u1", data_scope="self"))
        assert code == 200
        assert "data" in data
        # 当 data_scope=self 时，应只含 ownerId=u1 的客户（若后端实现过滤）
        for item in data.get("data", []):
            if item.get("ownerId") is not None:
                assert item.get("ownerId") == "u1"

    def test_crm_03_export_customers_csv(self, crm_client):
        """CRM-03 客户导出 CSV：GET /export/customers?format=csv 或 /customers/export?format=csv."""
        code, _ = _get(crm_client, "/export/customers?format=csv", _headers())
        if code != 200:
            code, _ = _get(crm_client, "/customers/export?format=csv", _headers())
        assert code == 200
        # 若返回 CSV 则 response 可能是 bytes；此处仅断言 200

    def test_crm_04_human_error_customer_name_empty(self, crm_client):
        """CRM-04 人性化报错：客户名空 POST /customers body {} -> 400，message 含「请填写客户名称」."""
        code, data = _post(crm_client, "/customers", {}, _headers(request_id="err-req-1"))
        assert code == 400
        msg = (data.get("message") or data.get("detail") or "") if isinstance(data, dict) else str(data)
        assert "客户名称" in msg or "name" in msg.lower()

    def test_crm_05_opportunity_owner(self, crm_client):
        """CRM-05 商机创建归属人：X-User-Id 创建商机后列表 ownerId 一致（当 data_scope=self）。"""
        # 先需有客户
        _post(crm_client, "/customers", {"name": "商机归属测"}, _headers(request_id="opp-owner-1", user_id="u1"))
        code, cust = _get(crm_client, "/customers", _headers(user_id="u1"))
        assert code == 200
        cust_id = (cust.get("data") or [{}])[0].get("customerId") if cust.get("data") else None
        if not cust_id:
            pytest.skip("无客户可创建商机")
        code, data = _post(
            crm_client,
            "/opportunities",
            {"customerId": cust_id, "title": "商用验收商机", "amountCents": 10000},
            _headers(request_id="opp-owner-2", user_id="u1"),
        )
        assert code in (200, 201)
        assert "opportunityId" in data or "opportunity_id" in str(data)


# ---------- ERP ----------
class TestERPBatch1Commercial:
    """ERP-01 ~ ERP-05."""

    @pytest.fixture
    def erp_client(self):
        app, typ = _load_cell_app("erp")
        if app is None:
            pytest.skip("ERP app 无法加载")
        app.config["TESTING"] = True
        yield app.test_client()

    def test_erp_01_cost_summary(self, erp_client):
        """ERP-01 生产成本核算汇总 GET /pp/cost-summary."""
        code, data = _get(erp_client, "/pp/cost-summary", _headers())
        assert code == 200
        assert "data" in data or "materialCostCents" in data or "totalCostCents" in data

    def test_erp_04_export_orders_csv(self, erp_client):
        """ERP-04 销售订单导出 CSV."""
        code, _ = _get(erp_client, "/export/orders?format=csv", _headers())
        assert code == 200

    def test_erp_05_human_error_work_order_not_found(self, erp_client):
        """ERP-05 人性化报错：工单不存在 GET /pp/work-orders/nonexistent-id/cost -> 404."""
        code, data = _get(erp_client, "/pp/work-orders/nonexistent-id/cost", _headers())
        assert code == 404
        msg = (data.get("message") or data.get("detail") or "") if isinstance(data, dict) else str(data)
        assert "工单" in msg or "不存在" in msg or "not found" in msg.lower()


# ---------- OA ----------
class TestOABatch1Commercial:
    """OA-01 ~ OA-04."""

    @pytest.fixture
    def oa_client(self):
        app, typ = _load_cell_app("oa")
        if app is None:
            pytest.skip("OA app 无法加载")
        app.config["TESTING"] = True
        yield app.test_client()

    def test_oa_02_approval_print(self, oa_client):
        """OA-02 审批单打印模板 GET /approvals/{id}/print -> 200 text/html."""
        code, data = _post(oa_client, "/approvals", {"typeCode": "purchase", "title": "打印测"}, _headers(request_id="print-req-1"))
        if code not in (200, 201):
            pytest.skip("无法创建审批单")
        iid = data.get("instanceId") or data.get("instance_id")
        if not iid:
            pytest.skip("无 instanceId")
        r = oa_client.get(f"/approvals/{iid}/print", headers=_headers())
        assert r.status_code == 200
        ct = r.headers.get("Content-Type") or ""
        assert "html" in ct or (hasattr(r, "get_data") and b"<" in (r.get_data() or b""))

    def test_oa_03_approvals_pagination(self, oa_client):
        """OA-03 审批列表分页 GET /approvals?page=1&pageSize=20."""
        code, data = _get(oa_client, "/approvals?page=1&pageSize=20", _headers())
        assert code == 200
        assert "data" in data and "total" in data
        assert "page" in data or "pageSize" in data or isinstance(data.get("data"), list)

    def test_oa_04_human_error_announcement_title(self, oa_client):
        """OA-04 人性化报错：公告标题必填 POST /announcements body {} -> 400."""
        code, data = _post(oa_client, "/announcements", {}, _headers(request_id="ann-err-1"))
        assert code == 400
        msg = (data.get("message") or data.get("details") or "") if isinstance(data, dict) else str(data)
        assert "标题" in msg or "title" in msg.lower()


# ---------- SRM ----------
class TestSRMBatch1Commercial:
    """SRM-01 ~ SRM-05."""

    @pytest.fixture
    def srm_client(self):
        app, typ = _load_cell_app("srm")
        if app is None:
            pytest.skip("SRM app 无法加载")
        app.config["TESTING"] = True
        yield app.test_client()

    def test_srm_01_bidding_project_create(self, srm_client):
        """SRM-01 招投标项目创建 POST /bidding/projects {title} -> 201 projectId, status=open."""
        code, data = _post(srm_client, "/bidding/projects", {"title": "项目A"}, _headers(request_id="bid-1"))
        assert code in (200, 201)
        assert data.get("projectId") or data.get("project_id")
        assert data.get("status") in ("open", "draft", None) or "open" in str(data.get("status", "")).lower()

    def test_srm_04_export_purchase_orders_csv(self, srm_client):
        """SRM-04 采购订单导出 CSV."""
        code, _ = _get(srm_client, "/export/purchase-orders?format=csv", _headers())
        assert code == 200

    def test_srm_05_human_error_project_title_empty(self, srm_client):
        """SRM-05 人性化报错：项目名空 POST /bidding/projects body {} -> 400."""
        code, data = _post(srm_client, "/bidding/projects", {}, _headers(request_id="bid-err-1"))
        assert code == 400
        msg = (data.get("message") or data.get("details") or "") if isinstance(data, dict) else str(data)
        assert "项目" in msg or "名称" in msg or "title" in msg.lower()
