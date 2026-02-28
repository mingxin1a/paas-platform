"""
全平台压力测试脚本（Locust）
覆盖：网关健康、登录、核心细胞接口、管理端接口、核心业务流程。
用法:
  locust -f locustfile.py --host=http://localhost:8000
  指定用户数/时长: locust -f locustfile.py --host=http://localhost:8000 -u 100 -r 10 -t 5m --headless
  72h 稳定性: -u 200 -r 5 -t 72h --headless
"""
import json
import os
import time
import uuid
from locust import HttpUser, task, between, events

# 从环境变量读取，默认 localhost:8000
HOST = os.environ.get("GATEWAY_URL", "http://localhost:8000").rstrip("/")

# 核心细胞及路径（与 smoke_test / 网关路由一致）
CELL_GET_PATHS = [
    ("crm", "customers"),
    ("erp", "orders"),
    ("wms", "inbound-orders"),
    ("mes", "work-orders"),
    ("tms", "shipments"),
    ("oa", "tasks"),
    ("his", "patients"),
    ("lis", "samples"),
]


def _headers(user) -> dict:
    """统一请求头：Authorization、X-Tenant-Id、X-Request-ID。"""
    h = {
        "Content-Type": "application/json",
        "X-Tenant-Id": "tenant-perf-" + str(hash(user) % 100),
        "X-Request-ID": str(uuid.uuid4()),
    }
    if getattr(user, "token", None):
        h["Authorization"] = "Bearer " + user.token
    else:
        h["Authorization"] = "Bearer perf-test-token"
    return h


class PlatformUser(HttpUser):
    """模拟平台用户：登录后访问多细胞接口与管理端。"""
    host = HOST
    wait_time = between(0.5, 1.5)

    def on_start(self):
        """每个虚拟用户启动时登录一次，获取 token。"""
        try:
            r = self.client.post(
                "/api/auth/login",
                json={"username": "client", "password": "123"},
                headers={"Content-Type": "application/json", "X-Request-ID": str(uuid.uuid4())},
                timeout=10,
                name="/api/auth/login",
            )
            if r.status_code == 200:
                data = r.json()
                self.token = (data.get("token") or "").strip()
                if self.token:
                    return
        except Exception:
            pass
        self.token = None  # 无 token 时仍用默认 Bearer，网关可能放行测试 token

    @task(3)
    def health(self):
        """网关健康检查。"""
        self.client.get("/health", name="/health")

    @task(2)
    def auth_me(self):
        """当前用户信息。"""
        self.client.get("/api/auth/me", headers=_headers(self), name="/api/auth/me")

    @task(5)
    def cell_list(self):
        """各细胞主列表 GET：轮询不同 cell。"""
        idx = int(time.time() * 10) % len(CELL_GET_PATHS)
        cell, path = CELL_GET_PATHS[idx]
        url = f"/api/v1/{cell}/{path}?page=1&pageSize=20"
        self.client.get(url, headers=_headers(self), name=f"/api/v1/[cell]/{path}")

    @task(1)
    def cell_health(self):
        """细胞健康探测。"""
        idx = int(time.time() * 10) % len(CELL_GET_PATHS)
        cell, _ = CELL_GET_PATHS[idx]
        self.client.get(f"/api/v1/{cell}/health", headers=_headers(self), name="/api/v1/[cell]/health")

    @task(2)
    def admin_cells(self):
        """管理端：细胞列表。"""
        self.client.get("/api/admin/cells", headers=_headers(self), name="/api/admin/cells")

    @task(1)
    def admin_health_summary(self):
        """管理端：健康汇总。"""
        self.client.get("/api/admin/health-summary", headers=_headers(self), name="/api/admin/health-summary")

    @task(1)
    def crm_create_customer(self):
        """CRM 业务流程：创建客户。"""
        name = "perf-" + str(uuid.uuid4())[:8]
        self.client.post(
            "/api/v1/crm/customers",
            json={"name": name, "contactPhone": "13800138000"},
            headers=_headers(self),
            name="/api/v1/crm/customers POST",
        )

    @task(1)
    def erp_create_order(self):
        """ERP 业务流程：创建订单。"""
        self.client.post(
            "/api/v1/erp/orders",
            json={"customerId": "c1", "totalAmountCents": 10000, "currency": "CNY"},
            headers=_headers(self),
            name="/api/v1/erp/orders POST",
        )


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """测试开始时的环境检查。"""
    import logging
    logging.info("Performance test started. Host=%s", HOST)
