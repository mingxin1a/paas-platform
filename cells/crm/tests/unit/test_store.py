"""
CRM store 单元测试：线索创建/分配/转化、商机、客户、联系人、预测与赢率。
"""
from __future__ import annotations

import pytest
import sys
from pathlib import Path

# 细胞根目录加入 path
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.store import InMemoryStore, STAGE_CONFIG


@pytest.fixture
def store():
    return InMemoryStore()


@pytest.fixture
def tenant():
    return "tenant-001"


def test_customer_create_and_list(store, tenant):
    c = store.customer_create(tenant, "公司A", "138****", "a@b.com")
    assert c["customerId"]
    assert c["name"] == "公司A"
    assert c["tenantId"] == tenant
    data, total = store.customer_list(tenant)
    assert total == 1
    assert data[0]["name"] == "公司A"


def test_lead_create_assign_convert(store, tenant):
    lead = store.lead_create(tenant, "张三", "阿里", "13900001111", "z@a.com", "web")
    assert lead["status"] == "new"
    store.lead_assign(tenant, lead["leadId"], "user-1")
    lead2 = store.lead_get(tenant, lead["leadId"])
    assert lead2["assignedTo"] == "user-1"
    lead3, cid, oid = store.lead_convert(tenant, lead["leadId"], "both", "商机标题", 10000)
    assert lead3["status"] == "converted"
    assert cid
    assert oid
    assert lead3["convertedCustomerId"] == cid
    assert lead3["convertedOpportunityId"] == oid


def test_opportunity_forecast(store, tenant):
    c = store.customer_create(tenant, "客户1")
    store.opportunity_create(tenant, c["customerId"], "商机1", 100000, "CNY", 1)
    store.opportunity_create(tenant, c["customerId"], "商机2", 200000, "CNY", 3)
    summary = store.forecast_summary(tenant)
    assert "byStage" in summary
    assert summary["totalWeightedCents"] >= 0


def test_win_rate_analysis(store, tenant):
    c = store.customer_create(tenant, "客户1")
    o1 = store.opportunity_create(tenant, c["customerId"], "O1", 1000, "CNY", 1)
    store.opportunity_update_stage(tenant, o1["opportunityId"], 5, 2)
    o2 = store.opportunity_create(tenant, c["customerId"], "O2", 2000, "CNY", 1)
    store.opportunity_update_stage(tenant, o2["opportunityId"], 6, 3)
    analysis = store.win_rate_analysis(tenant, 90)
    assert analysis["wonCount"] == 1
    assert analysis["lostCount"] == 1
    assert analysis["winRatePct"] == 50.0


def test_customer_360(store, tenant):
    c = store.customer_create(tenant, "公司B")
    store.contact_create(tenant, c["customerId"], "李四", "13900002222", "l@b.com", True)
    store.opportunity_create(tenant, c["customerId"], "商机B", 50000, "CNY", 2)
    cust = store.customer_get(tenant, c["customerId"])
    contacts, _ = store.contact_list(tenant, customer_id=c["customerId"])
    opps, _ = store.opportunity_list(tenant, customer_id=c["customerId"])
    assert cust["name"] == "公司B"
    assert len(contacts) == 1
    assert len(opps) == 1
