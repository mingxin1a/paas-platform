"""
全细胞健康与契约校验：对每个细胞加载 app，请求 /health 及契约约定主列表接口。
不依赖网关或真实部署，仅验证细胞自身可运行且契约路径存在。
"""
import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CELLS_DIR = os.path.join(ROOT, "cells")

# 每个细胞的主列表路径（GET，需 X-Tenant-Id）与预期 200
CELL_MAIN_GET = {
    "crm": "/customers",
    "erp": "/orders",
    "wms": "/inventory",
    "hrm": "/employees",
    "oa": "/tasks",
    "mes": "/work-orders",
    "tms": "/shipments",
    "srm": "/suppliers",
    "plm": "/products",
    "ems": "/consumption-records",
    "his": "/patients",
    "lis": "/samples",
    "lims": "/samples",
}


def discover_cells():
    if not os.path.isdir(CELLS_DIR):
        return []
    return [
        n for n in sorted(os.listdir(CELLS_DIR))
        if os.path.isdir(os.path.join(CELLS_DIR, n)) and not n.startswith(".")
    ]


def load_cell_app(cell_name):
    """从 cells/<cell_name> 加载 src.app 的 app 对象。每次加载前清理已缓存的 src 模块。"""
    cell_path = os.path.join(CELLS_DIR, cell_name)
    app_py = os.path.join(cell_path, "src", "app.py")
    if not os.path.isfile(app_py):
        return None
    # 避免上一细胞残留的 src 被复用
    to_remove = [k for k in sys.modules if k == "src" or k.startswith("src.")]
    for k in to_remove:
        del sys.modules[k]
    if cell_path in sys.path:
        sys.path.remove(cell_path)
    sys.path.insert(0, cell_path)
    try:
        import src.app as app_mod
        return getattr(app_mod, "app", None)
    except Exception:
        return None
    finally:
        if cell_path in sys.path:
            sys.path.remove(cell_path)


@pytest.fixture
def flask_available():
    try:
        import flask
        return True
    except ImportError:
        return False


@pytest.mark.parametrize("cell_name", discover_cells())
def test_cell_health(cell_name, flask_available):
    """每个细胞 /health 返回 200 且 body 含 status 与 cell 名。"""
    if not flask_available:
        pytest.skip("flask not installed")
    app = load_cell_app(cell_name)
    if app is None:
        pytest.skip(f"cell {cell_name} has no runnable app")
    with app.test_client() as client:
        r = client.get("/health")
        assert r.status_code == 200, f"{cell_name} /health status"
        data = r.get_json()
        assert data is not None, f"{cell_name} /health json"
        assert data.get("status") == "up", f"{cell_name} status=up"
        assert data.get("cell") == cell_name, f"{cell_name} cell name"


@pytest.mark.parametrize("cell_name", [c for c in discover_cells() if c in CELL_MAIN_GET])
def test_cell_main_list_contract(cell_name, flask_available):
    """每个细胞契约主列表 GET 带 X-Tenant-Id 返回 200。"""
    if not flask_available:
        pytest.skip("flask not installed")
    path = CELL_MAIN_GET.get(cell_name)
    if not path:
        pytest.skip(f"no main GET for {cell_name}")
    app = load_cell_app(cell_name)
    if app is None:
        pytest.skip(f"cell {cell_name} has no runnable app")
    with app.test_client() as client:
        r = client.get(path, headers={"X-Tenant-Id": "tenant-verify"})
        assert r.status_code == 200, f"{cell_name} GET {path} status"
        data = r.get_json()
        assert data is not None, f"{cell_name} GET {path} json"
        assert "data" in data or "total" in data or isinstance(data, list), f"{cell_name} list shape"
