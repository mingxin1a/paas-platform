"""
租户与配额单元测试。
"""
from __future__ import annotations

import os
import sys
import time

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from platform_core.core.tenant.store import TenantStore, STATUS_ENABLED, STATUS_DISABLED, DEFAULT_TENANT_ID
from platform_core.core.tenant.quota import TenantQuota


def test_tenant_store_default_tenant():
    store = TenantStore()
    assert store.is_valid(DEFAULT_TENANT_ID) is True
    t = store.get(DEFAULT_TENANT_ID)
    assert t is not None
    assert t.get("status") == STATUS_ENABLED


def test_tenant_store_create_and_get():
    store = TenantStore()
    t = store.create("tenant-001", "测试租户")
    assert t["id"] == "tenant-001"
    assert t["name"] == "测试租户"
    assert t["status"] == STATUS_ENABLED
    assert store.get("tenant-001")["name"] == "测试租户"
    assert store.is_valid("tenant-001") is True


def test_tenant_store_create_duplicate_raises():
    store = TenantStore()
    store.create("t-dup", "重复")
    with pytest.raises(ValueError, match="已存在"):
        store.create("t-dup", "重复2")


def test_tenant_store_disable_and_enable():
    store = TenantStore()
    store.create("t-dis", "禁用测试")
    assert store.is_valid("t-dis") is True
    store.disable("t-dis")
    assert store.is_valid("t-dis") is False
    store.enable("t-dis")
    assert store.is_valid("t-dis") is True


def test_tenant_store_expire_at():
    store = TenantStore()
    store.create("t-exp", "过期测试", expire_at=time.time() - 1)
    assert store.is_valid("t-exp") is False
    store.set_expire_at("t-exp", time.time() + 3600)
    assert store.is_valid("t-exp") is True


def test_tenant_quota_allow_request_no_limit():
    quota = TenantQuota()
    ok, _ = quota.allow_request("default")
    assert ok is True


def test_tenant_quota_set_and_exceed():
    quota = TenantQuota()
    quota.set_quota("t1", requests_per_min=2)
    ok1, _ = quota.allow_request("t1")
    ok2, _ = quota.allow_request("t1")
    ok3, reason = quota.allow_request("t1")
    assert ok1 is True
    assert ok2 is True
    assert ok3 is False
    assert "QUOTA" in reason or "quota" in reason.lower()
