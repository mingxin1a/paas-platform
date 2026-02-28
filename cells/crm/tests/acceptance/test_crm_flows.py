"""
CRM 验收测试：Salesforce 式端到端流程。
- 线索创建 -> 分配 -> 转化为客户+商机
- 客户 360° 视图
- 商机预测与赢率
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


def headers(tenant="acceptance-tenant", request_id=None):
    h = {"Content-Type": "application/json", "X-Tenant-Id": tenant}
    if request_id:
        h["X-Request-ID"] = request_id
    return h


def test_lead_to_opportunity_full_flow(client):
    """线索 -> 分配 -> 转化(account+opportunity) -> 客户详情 -> 商机列表"""
    r = client.post(
        "/leads",
        json={"name": "王五", "company": "验收公司", "email": "w@test.com"},
        headers=headers(request_id="acc-lead-1"),
    )
    assert r.status_code == 201
    lead_id = r.json["leadId"]
    assert r.json["status"] == "new"
    r2 = client.patch("/leads/" + lead_id, json={"assignedTo": "sales-1"}, headers=headers())
    assert r2.status_code == 200
    r3 = client.post(
        "/leads/" + lead_id + "/convert",
        json={"convertTo": "both", "createOpportunityTitle": "验收商机", "amountCents": 99900},
        headers=headers(request_id="acc-conv-1"),
    )
    assert r3.status_code == 200
    customer_id = r3.json["customerId"]
    opportunity_id = r3.json["opportunityId"]
    assert customer_id and opportunity_id
    r4 = client.get("/customers/" + customer_id, headers=headers())
    assert r4.status_code == 200
    assert r4.json["name"] == "验收公司"
    r5 = client.get("/opportunities?customerId=" + customer_id, headers=headers())
    assert r5.status_code == 200
    assert r5.json["total"] >= 1
    assert any(o["opportunityId"] == opportunity_id for o in r5.json["data"])


def test_customer_360_and_relationships(client):
    """创建客户 -> 添加联系人 -> 添加商机 -> 360 视图包含全部"""
    r = client.post("/customers", json={"name": "360验收客户"}, headers=headers(request_id="acc-c-1"))
    assert r.status_code == 201
    cid = r.json["customerId"]
    client.post(
        "/contacts",
        json={"customerId": cid, "name": "主联系人", "isPrimary": True},
        headers=headers(request_id="acc-ct-1"),
    )
    client.post(
        "/opportunities",
        json={"customerId": cid, "title": "360商机", "amountCents": 50000},
        headers=headers(request_id="acc-opp-1"),
    )
    r360 = client.get("/customers/" + cid + "/360", headers=headers())
    assert r360.status_code == 200
    assert r360.json["customer"]["name"] == "360验收客户"
    assert len(r360.json["contacts"]) >= 1
    assert len(r360.json["opportunities"]) >= 1


def test_forecast_and_win_rate_contract(client):
    """预测与赢率接口返回契约约定字段"""
    r = client.get("/opportunities/forecast", headers=headers())
    assert r.status_code == 200
    assert "byStage" in r.json and "totalWeightedCents" in r.json
    r2 = client.get("/opportunities/win-rate?periodDays=30", headers=headers())
    assert r2.status_code == 200
    assert r2.json["periodDays"] == 30
    assert "wonCount" in r2.json and "lostCount" in r2.json and "winRatePct" in r2.json


def test_activities_create_list_complete(client):
    """活动：创建 -> 列表 -> 完成 -> 待办列表"""
    r = client.post(
        "/activities",
        json={"subject": "跟进客户A", "activityType": "call", "relatedCustomerId": "c1", "dueAt": "2025-12-31T12:00:00Z"},
        headers=headers(request_id="acc-act-1"),
    )
    assert r.status_code == 201
    aid = r.json["activityId"]
    r2 = client.get("/activities?customerId=c1", headers=headers())
    assert r2.status_code == 200
    assert r2.json["total"] >= 1
    r3 = client.post("/activities/" + aid + "/complete", headers=headers())
    assert r3.status_code == 200
    assert r3.json["status"] == 2
    r4 = client.get("/activities/todo", headers=headers())
    assert r4.status_code == 200
    assert "data" in r4.json


def test_products_and_opportunity_lines(client):
    """产品 -> 商机行项目 -> 商机金额汇总"""
    r = client.post("/customers", json={"name": "行项目客户"}, headers=headers(request_id="acc-pl-c1"))
    cid = r.json["customerId"]
    r = client.post("/opportunities", json={"customerId": cid, "title": "行项目商机"}, headers=headers(request_id="acc-pl-o1"))
    oid = r.json["opportunityId"]
    r = client.post("/products", json={"productCode": "P001", "name": "产品A", "standardPriceCents": 10000}, headers=headers(request_id="acc-pl-p1"))
    pid = r.json["productId"]
    r = client.post(
        "/opportunities/" + oid + "/lines",
        json={"productId": pid, "quantity": 2, "unitPriceCents": 8000},
        headers=headers(request_id="acc-pl-l1"),
    )
    assert r.status_code == 201
    assert r.json["totalCents"] == 16000
    r2 = client.get("/opportunities/" + oid + "/lines", headers=headers())
    assert r2.status_code == 200
    assert len(r2.json["data"]) == 1


def test_pipeline_and_funnel(client):
    """管道汇总与漏斗数据"""
    r = client.get("/pipeline/summary", headers=headers())
    assert r.status_code == 200
    assert "byStage" in r.json and "totalWeightedCents" in r.json
    r2 = client.get("/pipeline/funnel", headers=headers())
    assert r2.status_code == 200
    assert "stages" in r2.json and "totalCount" in r2.json
    r3 = client.get("/reports/activity-stats", headers=headers())
    assert r3.status_code == 200
    assert "data" in r3.json


def test_approval_flow(client):
    """审批：提交 -> 待审批列表 -> 通过/拒绝"""
    r = client.post("/customers", json={"name": "审批客户"}, headers=headers(request_id="acc-ap-c1"))
    cid = r.json["customerId"]
    r = client.post("/opportunities", json={"customerId": cid, "title": "大单"}, headers=headers(request_id="acc-ap-o1"))
    oid = r.json["opportunityId"]
    r = client.post(
        "/approvals",
        json={"opportunityId": oid, "requestType": "large_deal", "requestedBy": "sales-1", "requestedValueCents": 1000000},
        headers=headers(request_id="acc-ap-r1"),
    )
    assert r.status_code == 201
    req_id = r.json["requestId"]
    r2 = client.get("/approvals?status=pending", headers=headers())
    assert r2.status_code == 200
    assert any(x["requestId"] == req_id for x in r2.json["data"])
    r3 = client.post("/approvals/" + req_id + "/process", json={"approved": True, "processedBy": "manager-1"}, headers=headers())
    assert r3.status_code == 200
    assert r3.json["status"] == "approved"


def test_template_merge(client):
    """模板合并：{{key}} 替换"""
    r = client.post(
        "/templates/merge",
        json={"template": "尊敬的 {{name}}，您的商机 {{title}} 已进入下一阶段。", "context": {"name": "张三", "title": "项目A"}},
        headers=headers(),
    )
    assert r.status_code == 200
    assert "merged" in r.json
    assert "张三" in r.json["merged"] and "项目A" in r.json["merged"]
