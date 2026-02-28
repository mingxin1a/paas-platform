"""
网关 Session/Token 存储单元测试。
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from platform_core.core.gateway.session_store import MemoryTokenStore, create_token_store


def test_memory_token_store_get_set():
    store = MemoryTokenStore()
    assert store.get("nonexistent") is None
    store.set("tok1", {"username": "admin", "role": "admin"}, ttl_sec=3600)
    assert store.get("tok1") == {"username": "admin", "role": "admin"}
    store.delete("tok1")
    assert store.get("tok1") is None


def test_create_token_store_returns_memory_by_default():
    store = create_token_store()
    assert store is not None
    store.set("t1", {"user": "a"})
    assert store.get("t1") == {"user": "a"}
