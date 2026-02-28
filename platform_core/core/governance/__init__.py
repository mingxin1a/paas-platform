# 治理中心：注册发现、健康巡检、故障隔离、链路追踪、RED 指标
from .store import GovernanceStore
from .app import app as governance_app
from .client import resolve, ingest, create_resolver_with_fallback, create_emit_with_ingest

__all__ = [
    "GovernanceStore",
    "governance_app",
    "resolve",
    "ingest",
    "create_resolver_with_fallback",
    "create_emit_with_ingest",
]
