#!/usr/bin/env python3
"""在容器内启动网关，使用环境变量解析路由与熔断；可选接入治理中心（注册发现、链路与指标）。"""
import os
import sys
import logging

sys.path.insert(0, os.environ.get("APP_ROOT", "/app"))
logging.basicConfig(level=logging.INFO)

from platform_core.core.gateway.app import create_app
from platform_core.core.gateway.config import load_routes
from platform_core.core.gateway.circuit_breaker import CircuitBreakerRegistry

def _env_resolver(cell):
    routes = load_routes()
    return routes.get(cell) or os.environ.get(f"CELL_{cell.upper()}_URL")

def _log_emit(trace_id, cell, path, status, duration_ms):
    logging.info("request cell=%s path=%s status=%s duration_ms=%s trace_id=%s", cell, path, status, duration_ms, trace_id)

# 若配置了治理中心：解析优先走治理中心（仅返回健康细胞），并上报链路与 RED 指标
try:
    from platform_core.core.governance.client import (
        create_resolver_with_fallback,
        create_emit_with_ingest,
        _get_base as _governance_base,
    )
    if _governance_base():
        resolver = create_resolver_with_fallback(_env_resolver)
        emit = create_emit_with_ingest(_log_emit)
        logging.info("gateway using governance: %s", _governance_base())
    else:
        resolver = _env_resolver
        emit = _log_emit
except Exception as e:
    logging.warning("governance client not used: %s", e)
    resolver = _env_resolver
    emit = _log_emit

breakers = CircuitBreakerRegistry()
app = create_app(resolver, emit, circuit_breakers=breakers, use_dynamic_routes=True)
port = int(os.environ.get("GATEWAY_PORT", "8000"))
app.run(host="0.0.0.0", port=port)
