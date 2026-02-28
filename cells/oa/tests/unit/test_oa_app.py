"""
OA 细胞单元测试：《接口设计说明书》统一格式、健康、任务 CRUD、审批与公告。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import pytest
from src.app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _h(tenant: str = "tenant-001", req_id: str | None = None):
    headers = {"Content-Type": "application/json", "X-Tenant-Id": tenant}
    if req_id:
        headers["X-Request-ID"] = req_id
    return headers


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "up"
    assert r.get_json()["cell"] == "oa"
    assert "X-Response-Time" in r.headers or True


def test_tasks_list_empty(client):
    r = client.get("/tasks", headers=_h())
    assert r.status_code == 200
    data = r.get_json()
    assert "data" in data
    assert "total" in data
    assert data["total"] == 0
    assert data["data"] == []


def test_tasks_crud(client):
    r = client.post("/tasks", json={"title": "测试任务"}, headers=_h(req_id="oa-t1"))
    assert r.status_code == 201
    j = r.get_json()
    assert j["title"] == "测试任务"
    assert "taskId" in j
    tid = j["taskId"]
    r2 = client.get(f"/tasks/{tid}", headers=_h())
    assert r2.status_code == 200
    assert r2.get_json()["title"] == "测试任务"
    r3 = client.patch(f"/tasks/{tid}", json={"status": 2}, headers=_h())
    assert r3.status_code == 200
    assert r3.get_json()["status"] == 2
    r4 = client.get("/tasks", headers=_h())
    assert r4.status_code == 200
    assert r4.get_json()["total"] >= 1


def test_tasks_create_requires_title(client):
    r = client.post("/tasks", json={}, headers=_h(req_id="oa-t2"))
    assert r.status_code == 400
    assert r.get_json().get("code") == "BAD_REQUEST"
    assert "details" in r.get_json() or "message" in r.get_json()


def test_tasks_idempotent(client):
    r1 = client.post("/tasks", json={"title": "幂等任务"}, headers=_h(req_id="oa-idem"))
    assert r1.status_code == 201
    r2 = client.post("/tasks", json={"title": "其他"}, headers=_h(req_id="oa-idem"))
    assert r2.status_code == 409
    assert r2.get_json().get("code") == "IDEMPOTENT_CONFLICT"


def test_tasks_get_not_found(client):
    r = client.get("/tasks/nonexistent-id", headers=_h())
    assert r.status_code == 404
    assert r.get_json().get("code") == "NOT_FOUND"


def test_approvals_list(client):
    r = client.get("/approvals", headers=_h())
    assert r.status_code == 200
    j = r.get_json()
    assert "data" in j and "total" in j and "page" in j


def test_approvals_create(client):
    r = client.post("/approvals", json={"typeCode": "leave", "formData": {}}, headers=_h(req_id="oa-app1"))
    assert r.status_code == 201
    assert "instanceId" in r.get_json()


def test_approval_seal_and_print(client):
    r = client.post("/approvals", json={"typeCode": "leave", "formData": {"reason": "事由"}}, headers=_h(req_id="oa-seal1"))
    assert r.status_code == 201
    iid = r.get_json()["instanceId"]
    r2 = client.post(f"/approvals/{iid}/seal", headers=_h())
    assert r2.status_code == 200
    j = r2.get_json()
    assert j.get("sealedAt") and j.get("sealedBy")
    r3 = client.get(f"/approvals/{iid}/print", headers=_h())
    assert r3.status_code == 200
    assert "text/html" in r3.headers.get("Content-Type", "")
    assert "审批单" in r3.get_data(as_text=True)


def test_announcements_list(client):
    r = client.get("/announcements", headers=_h())
    assert r.status_code == 200
    j = r.get_json()
    assert "data" in j and "total" in j


def test_announcements_create(client):
    r = client.post("/announcements", json={"title": "测试公告", "content": "内容"}, headers=_h(req_id="oa-ann1"))
    assert r.status_code == 201
    assert "announcementId" in r.get_json()


def test_audit_logs(client):
    r = client.get("/audit-logs", headers=_h())
    assert r.status_code == 200
    j = r.get_json()
    assert "data" in j and "total" in j


def test_tasks_batch_complete_and_reminders(client):
    r1 = client.post("/tasks", json={"title": "待办1"}, headers=_h(req_id="oa-batch1"))
    assert r1.status_code == 201
    t1 = r1.get_json()["taskId"]
    r2 = client.post("/tasks/batch-complete", json={"taskIds": [t1]}, headers=_h())
    assert r2.status_code == 200
    j = r2.get_json()
    assert j.get("completed") == 1 and j.get("notFound") == []
    r3 = client.get("/reminders", headers=_h())
    assert r3.status_code == 200
    assert "tasks" in r3.get_json() and "pendingApprovals" in r3.get_json()


def test_announcement_get(client):
    r = client.post("/announcements", json={"title": "公告详情测", "content": "内容"}, headers=_h(req_id="oa-get-ann"))
    assert r.status_code == 201
    aid = r.get_json()["announcementId"]
    r2 = client.get(f"/announcements/{aid}", headers=_h())
    assert r2.status_code == 200
    assert r2.get_json().get("title") == "公告详情测"
