"""
压力/并发场景占位测试：可扩展为多线程请求或 locust/jmeter 驱动。
CI 中默认仅运行轻量级用例；完整压测见 deploy 脚本或独立压测任务。
"""
from __future__ import annotations

import pytest


def test_stress_placeholder_sequential_orders():
    """顺序创建多笔订单不报错（轻量压力）。"""
    import os
    import sys
    ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    from tests.test_all_cells_health import load_cell_app
    app = load_cell_app("erp")
    if app is None:
        pytest.skip("ERP 无法加载")
    app.config["TESTING"] = True
    with app.test_client() as c:
        for i in range(10):
            r = c.post(
                "/orders",
                json={"customerId": f"c{i}", "totalAmountCents": 100 * (i + 1)},
                headers={"Content-Type": "application/json", "X-Tenant-Id": "t1", "X-Request-ID": f"stress-{i}"},
            )
            assert r.status_code == 201, f"iteration {i} got {r.status_code}"
