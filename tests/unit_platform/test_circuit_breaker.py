"""
熔断器单元测试：状态转换、半开探测、环境变量。
"""
from __future__ import annotations

import os
import time

import pytest

import sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from platform_core.core.gateway.circuit_breaker import CircuitBreaker, CircuitBreakerRegistry


def test_circuit_breaker_closed_state():
    cb = CircuitBreaker("test-cell", window_sec=10, failure_ratio=0.5, half_open_probes=3, probe_successes_to_close=2)
    assert cb.state() == "closed"
    assert cb.allow_request() is True


def test_circuit_breaker_opens_after_failures():
    cb = CircuitBreaker("test-cell", window_sec=10, failure_ratio=0.5, half_open_probes=2, probe_successes_to_close=2)
    cb.record(success=False)
    cb.record(success=False)
    assert cb.state() == "open"
    assert cb.allow_request() is False


def test_circuit_breaker_stays_closed_with_successes():
    cb = CircuitBreaker("test-cell", window_sec=10, failure_ratio=0.5)
    cb.record(success=True)
    cb.record(success=True)
    assert cb.state() == "closed"
    assert cb.allow_request() is True


def test_circuit_breaker_half_open_after_window():
    cb = CircuitBreaker("test-cell", window_sec=0.1, failure_ratio=0.5, half_open_probes=3, probe_successes_to_close=2)
    cb.record(success=False)
    cb.record(success=False)
    assert cb.state() == "open"
    time.sleep(0.2)
    assert cb.allow_request() is True
    assert cb.state() == "half_open"


def test_circuit_breaker_half_open_closes_after_probe_successes():
    cb = CircuitBreaker("test-cell", window_sec=0.1, failure_ratio=0.5, half_open_probes=3, probe_successes_to_close=2)
    cb.record(success=False)
    cb.record(success=False)
    time.sleep(0.2)
    cb.allow_request()
    cb.record(success=True)
    cb.record(success=True)
    assert cb.state() == "closed"


def test_circuit_breaker_registry_returns_same_instance():
    reg = CircuitBreakerRegistry()
    a = reg.get("crm")
    b = reg.get("crm")
    assert a is b
    assert reg.get("erp") is not a
