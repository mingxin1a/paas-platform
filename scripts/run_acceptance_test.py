#!/usr/bin/env python3
"""
全平台商用验收测试脚本（一键执行）。
自动执行：网关健康、登录、管理端越权、各细胞健康与核心流程；生成验收报告。
用法:
  全量验收:  python scripts/run_acceptance_test.py
  单模块:    python scripts/run_acceptance_test.py --module crm
  仅健康:    python scripts/run_acceptance_test.py --health-only
  GATEWAY_URL=http://host:8000 python scripts/run_acceptance_test.py
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
sys.path.insert(0, str(ROOT))

# 延迟导入，确保 ROOT 在 path 中
def _run():
    import json
    import urllib.request
    import urllib.error

    GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8000").rstrip("/")
    BASE_HEADERS = {
        "Content-Type": "application/json",
        "Authorization": "Bearer test-token",
        "X-Tenant-Id": "tenant-acceptance-test",
        "X-Request-ID": "",
    }

    results = []

    def req(method: str, url: str, body: dict | None = None, headers: dict | None = None) -> tuple[int, dict]:
        h = {**BASE_HEADERS, "X-Request-ID": f"acc-{datetime.now().strftime('%H%M%S')}"}
        if headers:
            h.update(headers)
        data = json.dumps(body).encode("utf-8") if body and method in ("POST", "PUT", "PATCH") else None
        r = urllib.request.Request(url, data=data, method=method, headers=h)
        try:
            with urllib.request.urlopen(r, timeout=15) as res:
                raw = res.read().decode()
                return res.getcode(), json.loads(raw) if raw.strip() else {}
        except urllib.error.HTTPError as e:
            raw = e.read().decode() if e.fp else "{}"
            try:
                return e.code, json.loads(raw) if raw else {}
            except Exception:
                return e.code, {}
        except Exception as e:
            return 0, {"error": str(e)}

    def base(cell: str, path: str) -> str:
        return f"{GATEWAY_URL}/api/v1/{cell}/{path.lstrip('/')}"

    def record(name: str, passed: bool, msg: str):
        results.append({"name": name, "passed": passed, "msg": msg})
        return passed

    # ----- PaaS 平台 -----
    code, _ = req("GET", f"{GATEWAY_URL}/health")
    record("P1-网关健康", code == 200, f"GET /health => {code}")

    code, body = req("POST", f"{GATEWAY_URL}/api/auth/login", {"username": "client", "password": "123"})
    token = (body.get("token") or "").strip() if body else ""
    record("P2-认证登录", code == 200 and bool(token), f"POST /api/auth/login => {code}")

    if token:
        code, _ = req("GET", f"{GATEWAY_URL}/api/admin/cells", headers={"Authorization": f"Bearer {token}"})
        record("P4-管理端越权防护(client应403)", code == 403, f"client 访问 /api/admin/cells => {code}")

    admin_code, admin_body = req("POST", f"{GATEWAY_URL}/api/auth/login", {"username": "admin", "password": "admin"})
    admin_token = (admin_body.get("token") or "").strip() if admin_body else ""
    if admin_token:
        code, _ = req("GET", f"{GATEWAY_URL}/api/admin/cells", headers={"Authorization": f"Bearer {admin_token}"})
        record("P5-admin访问管理端", code == 200, f"admin /api/admin/cells => {code}")

    # 安全响应头
    try:
        r = urllib.request.Request(f"{GATEWAY_URL}/health", method="GET")
        with urllib.request.urlopen(r, timeout=5) as res:
            has_x = "X-Content-Type-Options" in res.headers or "X-Frame-Options" in res.headers
        record("S2-安全响应头", has_x, "X-Content-Type-Options/X-Frame-Options" if has_x else "缺少安全头")
    except Exception as e:
        record("S2-安全响应头", False, str(e))

    # ----- 业务模块：健康 + 流程 -----
    from deploy.core_business_flow_tests import (
        test_gateway_health,
        test_cell_health,
        test_crm_flow,
        test_erp_flow,
        test_oa_flow,
        test_srm_flow,
        test_wms_flow,
        test_mes_flow,
        test_tms_flow,
        test_ems_flow,
        test_plm_flow,
        test_his_flow,
        test_lis_flow,
        test_lims_flow,
    )

    module_filter = None
    for i, a in enumerate(sys.argv):
        if a == "--module" and i + 1 < len(sys.argv):
            module_filter = sys.argv[i + 1].strip().lower()
            break
    health_only = "--health-only" in sys.argv

    cells_flows = [
        ("crm", test_crm_flow),
        ("erp", test_erp_flow),
        ("oa", test_oa_flow),
        ("srm", test_srm_flow),
        ("wms", test_wms_flow),
        ("mes", test_mes_flow),
        ("tms", test_tms_flow),
        ("ems", test_ems_flow),
        ("plm", test_plm_flow),
        ("his", test_his_flow),
        ("lis", test_lis_flow),
        ("lims", test_lims_flow),
    ]
    if module_filter:
        cells_flows = [(n, f) for n, f in cells_flows if n == module_filter]

    for cell_id, flow_fn in cells_flows:
        ok, msg = test_cell_health(cell_id)
        record(f"C1-{cell_id}-健康", ok, msg)
        if not health_only:
            try:
                ok, msg = flow_fn()
                record(f"C3-{cell_id}-核心流程", ok, msg)
            except Exception as e:
                record(f"C3-{cell_id}-核心流程", False, str(e))

    if not module_filter and not health_only:
        for cell_id, _ in cells_flows:
            pass  # 已在上面的 flows 里跑过
        # 幂等与故障隔离（可选）
        try:
            from deploy.core_business_flow_tests import test_idempotency, test_fault_isolation
            ok, msg = test_idempotency("ems", "consumption-records", {"meterId": "M-idem", "value": 1, "unit": "kWh"}, "recordId")
            record("幂等-EMS", ok, msg)
            ok, msg = test_fault_isolation()
            record("故障隔离-健康汇总", ok, msg)
        except Exception as e:
            record("故障隔离-健康汇总", False, str(e))

    return results


def main():
    DIST.mkdir(parents=True, exist_ok=True)
    print("[run_acceptance_test] 开始商用验收测试 ...")
    try:
        results = _run()
    except Exception as e:
        results = [{"name": "启动", "passed": False, "msg": str(e)}]
        print(f"[run_acceptance_test] 执行异常: {e}")
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    report_path = DIST / f"acceptance_report_{stamp}.md"
    lines = [
        "# 商用验收测试报告",
        "",
        f"**执行时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**结果**：{passed}/{total} 通过",
        "",
        "| 验收项 | 结果 | 说明 |",
        "|--------|------|------|",
    ]
    for r in results:
        status = "通过" if r["passed"] else "不通过"
        lines.append(f"| {r['name']} | {status} | {r['msg'][:80]} |")
    lines.extend(["", "---", "生成自 `scripts/run_acceptance_test.py`"])
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[run_acceptance_test] 报告已生成: {report_path}")
    for r in results:
        sym = "✓" if r["passed"] else "✗"
        print(f"  {sym} {r['name']}: {r['msg'][:60]}")
    print(f"[run_acceptance_test] {passed}/{total} 通过")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
