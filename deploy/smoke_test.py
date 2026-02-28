#!/usr/bin/env python3
"""冒烟测试：对已部署的网关执行健康检查与细胞接口检查。支持单细胞(默认 CRM)或全部细胞。"""
import os
import sys
import time
import urllib.request
import urllib.error

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8000")
MAX_WAIT = 60

# 每个细胞经网关的主列表路径（GET），用于冒烟
CELL_PATHS = {
    "crm": "/api/v1/crm/customers",
    "erp": "/api/v1/erp/orders",
    "wms": "/api/v1/wms/inventory",
    "hrm": "/api/v1/hrm/employees",
    "oa": "/api/v1/oa/tasks",
    "mes": "/api/v1/mes/work-orders",
    "tms": "/api/v1/tms/shipments",
    "srm": "/api/v1/srm/suppliers",
    "plm": "/api/v1/plm/products",
    "ems": "/api/v1/ems/consumption-records",
    "his": "/api/v1/his/patients",
    "lis": "/api/v1/lis/samples",
    "lims": "/api/v1/lims/samples",
}

SMOKE_HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Bearer smoke-test",
    "X-Tenant-Id": "tenant-001",
}


def get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.getcode(), r.headers, r.read().decode()


def main():
    use_all = os.environ.get("USE_ALL_CELLS", "").strip().lower() in ("1", "true", "yes") or "--all" in sys.argv
    print("[smoke] Gateway URL:", GATEWAY_URL)
    print("[smoke] mode:", "all cells" if use_all else "gateway + CRM")

    start = time.time()
    while time.time() - start < MAX_WAIT:
        try:
            code, _, _ = get(f"{GATEWAY_URL}/health")
            if code == 200:
                break
        except Exception as e:
            print("[smoke] waiting for gateway...", e)
            time.sleep(2)
    else:
        print("[smoke] gateway not ready in time")
        sys.exit(1)
    print("[smoke] gateway /health OK")

    if use_all:
        failed = []
        for cell, path in CELL_PATHS.items():
            try:
                code, _, body = get(f"{GATEWAY_URL}{path}", headers=SMOKE_HEADERS)
                if code == 200:
                    print(f"[smoke] OK: {cell} {path}")
                else:
                    print(f"[smoke] FAIL: {cell} {path} -> {code} {body[:80]}")
                    failed.append(cell)
            except Exception as e:
                print(f"[smoke] FAIL: {cell} {path} -> {e}")
                failed.append(cell)
        if failed:
            print(f"[smoke] {len(failed)} cell(s) failed: {', '.join(failed)}")
            sys.exit(1)
        print(f"[smoke] all {len(CELL_PATHS)} cells passed")
        return 0

    # 默认：仅 CRM
    code, hdrs, body = get(f"{GATEWAY_URL}/api/v1/crm/customers", headers=SMOKE_HEADERS)
    if code != 200:
        print("[smoke] GET /api/v1/crm/customers failed:", code, body[:200])
        sys.exit(1)
    print("[smoke] GET /api/v1/crm/customers OK (code=200)")
    print("[smoke] all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
