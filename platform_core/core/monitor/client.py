"""
全量化监控埋点客户端
遵循《00_最高宪法》第六审判：JSON 格式日志、trace_id；
《01_核心法律》CT 扫描原则：3 分钟内通过 trace_id 定位到代码行。
"""
import json
import logging
import time
from typing import Any, Optional

logger = logging.getLogger("suppaas.monitor")


def emit_span(trace_id: str, cell: str, operation: str, status: str, duration_ms: int, extra: Optional[dict] = None) -> None:
    """上报请求 span：trace_id、细胞、操作、状态、耗时。"""
    payload = {
        "trace_id": trace_id,
        "cell": cell,
        "operation": operation,
        "status": status,
        "duration_ms": duration_ms,
        "ts": time.time(),
    }
    if extra:
        payload.update(extra)
    logger.info(json.dumps(payload, ensure_ascii=False))


def emit_metric(name: str, value: float, tags: Optional[dict] = None) -> None:
    """上报指标（可对接 Prometheus/StatsD）。"""
    payload = {"metric": name, "value": value, "ts": time.time()}
    if tags:
        payload["tags"] = tags
    logger.info(json.dumps(payload, ensure_ascii=False))


def set_trace_id(trace_id: str) -> None:
    """将 trace_id 放入线程局部/上下文，供下游日志关联。"""
    pass  # 实际可挂到 contextvars 或 threading.local
