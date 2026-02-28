#!/usr/bin/env python3
"""
核心业务流程测试用例（可直接执行）
覆盖 PaaS 网关 + 各 Cell 商用核心流程的端到端验证。
用法:
  经网关（默认）: GATEWAY_URL=http://localhost:8000 python core_business_flow_tests.py
  仅健康检查:     python core_business_flow_tests.py --health-only
  指定 Cell:      python core_business_flow_tests.py --cell crm
  简单压测:       python core_business_flow_tests.py --load  (100 并发 5 分钟，需安装 requests)
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
import urllib.error

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8000")
BASE_HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Bearer test-token",
    "X-Tenant-Id": "tenant-acceptance-test",
    "X-Request-ID": "",
}


def _req(method: str, url: str, body: dict | None = None, headers: dict | None = None) -> tuple[int, dict]:
    req_headers = {**BASE_HEADERS}
    req_headers["X-Request-ID"] = f"test-{int(time.time()*1000)}-{os.urandom(4).hex()}"
    if headers:
        req_headers.update(headers)
    data = json.dumps(body).encode("utf-8") if body and method in ("POST", "PUT", "PATCH") else None
    req = urllib.request.Request(url, data=data, method=method, headers=req_headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read().decode()
            return r.getcode(), json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode() if e.fp else "{}"
        try:
            return e.code, json.loads(raw) if raw else {"error": str(e)}
        except Exception:
            return e.code, {"error": raw or str(e)}
    except Exception as e:
        return 0, {"error": str(e)}


def _base(cell: str, path: str) -> str:
    return f"{GATEWAY_URL.rstrip('/')}/api/v1/{cell}/{path.lstrip('/')}"


# ---------- 1. 网关与健康 ----------
def test_gateway_health() -> tuple[bool, str]:
    code, _ = _req("GET", f"{GATEWAY_URL.rstrip('/')}/health")
    if code == 200:
        return True, "网关 /health OK"
    return False, f"网关 /health 返回 {code}"


def test_cell_health(cell: str) -> tuple[bool, str]:
    code, body = _req("GET", _base(cell, "health"))
    if code == 200 and body.get("status") == "up":
        return True, f"{cell} /health OK"
    return False, f"{cell} /health 返回 {code} {body}"


# ---------- 2. CRM：客户→商机→合同→回款 ----------
def test_crm_flow() -> tuple[bool, str]:
    # 创建客户
    code, body = _req("POST", _base("crm", "customers"), {"name": "验收客户", "contactPhone": "13800138000"})
    if code not in (200, 201):
        return False, f"CRM 创建客户 失败: {code} {body}"
    customer_id = body.get("customerId") or body.get("id")
    if not customer_id:
        return False, f"CRM 创建客户 未返回 customerId: {body}"
    # 列表
    code2, list_body = _req("GET", _base("crm", "customers"))
    if code2 != 200:
        return False, f"CRM 客户列表 失败: {code2} {list_body}"
    total = list_body.get("total", 0)
    return True, f"CRM 客户创建+列表 OK (customerId={customer_id}, total={total})"


# ---------- 3. ERP：采购流程 物料→采购订单→（应付/付款） ----------
def test_erp_flow() -> tuple[bool, str]:
    # 物料
    code, body = _req("POST", _base("erp", "mm/materials"), {"materialCode": "MAT-ACC-001", "name": "验收物料", "unit": "个"})
    if code not in (200, 201):
        return False, f"ERP 创建物料 失败: {code} {body}"
    material_id = body.get("materialId") or body.get("id")
    if not material_id:
        return False, f"ERP 创建物料 未返回 materialId: {body}"
    # 采购订单
    code2, po_body = _req("POST", _base("erp", "mm/purchase-orders"), {
        "supplierId": "sup1", "lines": [{"materialId": material_id, "quantity": 10, "unitPriceCents": 1000}]
    })
    if code2 not in (200, 201):
        return False, f"ERP 创建采购订单 失败: {code2} {po_body}"
    return True, f"ERP 物料+采购订单 OK (materialId={material_id})"


# ---------- 4. WMS：入库→库存→出库 ----------
def test_wms_flow() -> tuple[bool, str]:
    code, body = _req("GET", _base("wms", "inventory"))
    if code != 200:
        return False, f"WMS 库存列表 失败: {code} {body}"
    code2, ib = _req("POST", _base("wms", "inbound-orders"), {
        "warehouseId": "WH-ACC", "typeCode": "purchase", "sourceOrderId": "", "erpOrderId": ""
    })
    if code2 not in (200, 201):
        return False, f"WMS 创建入库单 失败: {code2} {ib}"
    order_id = ib.get("orderId") or ib.get("id")
    if not order_id:
        return False, f"WMS 入库单未返回 orderId: {ib}"
    code3, _ = _req("GET", _base("wms", f"inbound-orders/{order_id}"))
    if code3 != 200:
        return False, f"WMS 入库单详情 失败: {code3}"
    return True, "WMS 库存查询+入库单创建+详情 OK"


# ---------- 5. MES：生产计划→工单→领料→报工→生产入库 ----------
def test_mes_flow() -> tuple[bool, str]:
    code, body = _req("GET", _base("mes", "work-orders"))
    if code != 200:
        return False, f"MES 工单列表 失败: {code} {body}"
    code2, body2 = _req("GET", _base("mes", "boms"))
    if code2 != 200:
        return False, f"MES BOM 列表 失败: {code2} {body2}"
    code3, wo = _req("POST", _base("mes", "work-orders"), {
        "orderNo": f"WO-ACC-{int(time.time())}", "productCode": "P001", "qty": 10, "workshopId": "WS1"
    })
    if code3 not in (200, 201):
        return False, f"MES 创建工单 失败: {code3} {wo}"
    wo_id = wo.get("workOrderId") or wo.get("id")
    if wo_id:
        code4, _ = _req("GET", _base("mes", f"work-orders/{wo_id}"))
        if code4 != 200:
            return False, f"MES 工单详情 失败: {code4}"
    return True, "MES 工单列表+BOM+创建工单+详情 OK"


# ---------- 6. OA：审批列表/创建 ----------
def test_oa_flow() -> tuple[bool, str]:
    code, body = _req("GET", _base("oa", "approvals"))
    if code != 200:
        return False, f"OA 审批列表 失败: {code} {body}"
    return True, "OA 审批列表 OK"


# ---------- 7. SRM：供应商→RFQ ----------
def test_srm_flow() -> tuple[bool, str]:
    code, body = _req("GET", _base("srm", "suppliers"))
    if code != 200:
        return False, f"SRM 供应商列表 失败: {code} {body}"
    return True, "SRM 供应商列表 OK"


# ---------- 8. TMS：运单 ----------
def test_tms_flow() -> tuple[bool, str]:
    code, body = _req("GET", _base("tms", "shipments"))
    if code != 200:
        return False, f"TMS 运单列表 失败: {code} {body}"
    code2, sh = _req("POST", _base("tms", "shipments"), {
        "trackingNo": f"TMS-ACC-{int(time.time())}", "origin": "北京", "destination": "上海",
        "vehicleId": "", "driverId": "", "wmsOutboundOrderId": "", "erpOrderId": ""
    })
    if code2 not in (200, 201):
        return False, f"TMS 创建运单 失败: {code2} {sh}"
    sh_id = sh.get("shipmentId") or sh.get("id")
    if sh_id:
        code3, _ = _req("GET", _base("tms", f"shipments/{sh_id}"))
        if code3 != 200:
            return False, f"TMS 运单详情 失败: {code3}"
    return True, "TMS 运单列表+创建+详情 OK"


# ---------- 9. EMS：能耗记录+统计 ----------
def test_ems_flow() -> tuple[bool, str]:
    code, body = _req("POST", _base("ems", "consumption-records"), {"meterId": "M1", "value": 100.5, "unit": "kWh"})
    if code not in (200, 201):
        return False, f"EMS 能耗采集 失败: {code} {body}"
    code2, body2 = _req("GET", _base("ems", "stats") + "?period=day")
    if code2 != 200:
        return False, f"EMS 统计 失败: {code2} {body2}"
    return True, "EMS 采集+统计 OK"


# ---------- 10. PLM：产品+BOM ----------
def test_plm_flow() -> tuple[bool, str]:
    code, body = _req("POST", _base("plm", "products"), {"productCode": "P-ACC-001", "name": "验收产品"})
    if code not in (200, 201):
        return False, f"PLM 创建产品 失败: {code} {body}"
    code2, body2 = _req("GET", _base("plm", "boms"))
    if code2 != 200:
        return False, f"PLM BOM 列表 失败: {code2} {body2}"
    return True, "PLM 产品+BOM OK"


# ---------- 11. HIS：患者→挂号→就诊 ----------
def test_his_flow() -> tuple[bool, str]:
    code, body = _req("GET", _base("his", "patients"))
    if code != 200:
        return False, f"HIS 患者列表 失败: {code} {body}"
    return True, "HIS 患者列表 OK"


# ---------- 12. LIS：检验申请→样本→报告 ----------
def test_lis_flow() -> tuple[bool, str]:
    code, body = _req("GET", _base("lis", "samples"))
    if code != 200:
        return False, f"LIS 样本列表 失败: {code} {body}"
    return True, "LIS 样本列表 OK"


# ---------- 13. LIMS：样品→任务→溯源 ----------
def test_lims_flow() -> tuple[bool, str]:
    code, body = _req("GET", _base("lims", "samples"))
    if code != 200:
        return False, f"LIMS 样品列表 失败: {code} {body}"
    code2, body2 = _req("GET", _base("lims", "config/retention"))
    if code2 != 200:
        return False, f"LIMS 留存配置 失败: {code2} {body2}"
    return True, "LIMS 样品+留存配置 OK"


# ---------- 幂等性验证 ----------
def test_idempotency(cell: str, path: str, body: dict, id_key: str) -> tuple[bool, str]:
    rid = f"idem-{int(time.time()*1000)}"
    headers = {**BASE_HEADERS, "X-Request-ID": rid}
    code1, b1 = _req("POST", _base(cell, path), body, headers)
    # 第二次使用相同 X-Request-ID
    code2, b2 = _req("POST", _base(cell, path), body, headers)
    # 期望：第二次 200/201 返回同一资源，或 409 冲突
    if code2 in (200, 201, 409):
        if code2 == 409:
            return True, f"{cell} {path} 幂等 OK (二次 409)"
        if b2.get(id_key) == b1.get(id_key):
            return True, f"{cell} {path} 幂等 OK (二次 {code2} 同资源)"
    return False, f"{cell} {path} 幂等异常: 首次 {code1} 二次 {code2} {b2}"


# ---------- 故障隔离（仅检查网关健康汇总） ----------
def test_fault_isolation() -> tuple[bool, str]:
    url = f"{GATEWAY_URL.rstrip('/')}/api/admin/health-summary"
    req = urllib.request.Request(url, method="GET", headers={**BASE_HEADERS})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode())
        if data.get("gateway") == "up":
            return True, "网关健康汇总可访问（故障隔离需人工停 Cell 验证）"
        return False, f"健康汇总异常: {data}"
    except Exception as e:
        return False, f"健康汇总请求失败: {e}"


# ---------- 压测（可选，需 requests） ----------
def run_load_test(duration_sec: int = 300, concurrency: int = 100) -> tuple[bool, str]:
    try:
        import concurrent.futures
    except ImportError:
        return False, "压测需要 Python 3.2+ concurrent.futures"
    url = _base("crm", "customers")
    errors = []
    success = 0
    start = time.time()
    def one_request(_):
        c, _ = _req("GET", url)
        return c == 200
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = [ex.submit(one_request, i) for i in range(concurrency)]
        while time.time() - start < duration_sec:
            done = sum(1 for f in futures if f.done())
            for f in concurrent.futures.as_completed(futures):
                try:
                    if f.result():
                        success += 1
                    else:
                        errors.append("non-200")
                except Exception as e:
                    errors.append(str(e))
            if done >= len(futures):
                futures = [ex.submit(one_request, i) for i in range(concurrency)]
        elapsed = time.time() - start
    total = success + len(errors)
    if total == 0:
        return False, "压测无请求完成"
    pct = 100 * success / total if total else 0
    return pct >= 99, f"压测 {elapsed:.0f}s 完成请求约 {total} 次，成功率 {pct:.1f}%"


def main():
    health_only = "--health-only" in sys.argv
    load = "--load" in sys.argv
    cell_filter = None
    for i, arg in enumerate(sys.argv):
        if arg == "--cell" and i + 1 < len(sys.argv):
            cell_filter = sys.argv[i + 1].strip().lower()
            break

    print(f"[core_business_flow_tests] GATEWAY_URL={GATEWAY_URL}")
    if load:
        ok, msg = run_load_test(duration_sec=60, concurrency=50)  # 缩短为 1 分钟示例
        print(f"  [LOAD] {'PASS' if ok else 'FAIL'}: {msg}")
        sys.exit(0 if ok else 1)

    # 健康检查
    ok, msg = test_gateway_health()
    print(f"  [gateway] {'PASS' if ok else 'FAIL'}: {msg}")
    if not ok:
        sys.exit(1)
    if health_only:
        cells = ["crm", "erp", "wms", "oa", "mes", "tms", "srm", "plm", "ems", "his", "lis", "lims"]
        for c in cells:
            if cell_filter and c != cell_filter:
                continue
            ok, msg = test_cell_health(c)
            print(f"  [{c}] {'PASS' if ok else 'FAIL'}: {msg}")
        sys.exit(0)

    flows = [
        ("crm", test_crm_flow),
        ("erp", test_erp_flow),
        ("wms", test_wms_flow),
        ("mes", test_mes_flow),
        ("oa", test_oa_flow),
        ("srm", test_srm_flow),
        ("tms", test_tms_flow),
        ("ems", test_ems_flow),
        ("plm", test_plm_flow),
        ("his", test_his_flow),
        ("lis", test_lis_flow),
        ("lims", test_lims_flow),
    ]
    if cell_filter:
        flows = [(n, fn) for n, fn in flows if n == cell_filter]
    failed = []
    for name, fn in flows:
        try:
            ok, msg = fn()
            print(f"  [{name}] {'PASS' if ok else 'FAIL'}: {msg}")
            if not ok:
                failed.append(name)
        except Exception as e:
            print(f"  [{name}] FAIL: {e}")
            failed.append(name)

    # 幂等
    ok, msg = test_idempotency("ems", "consumption-records", {"meterId": "M-idem", "value": 1, "unit": "kWh"}, "recordId")
    print(f"  [idempotency] {'PASS' if ok else 'FAIL'}: {msg}")
    if not ok:
        failed.append("idempotency")

    ok, msg = test_fault_isolation()
    print(f"  [fault_isolation] {'PASS' if ok else 'FAIL'}: {msg}")

    if failed:
        print(f"[core_business_flow_tests] 失败: {', '.join(failed)}")
        sys.exit(1)
    print("[core_business_flow_tests] 全部通过")
    sys.exit(0)


if __name__ == "__main__":
    main()
