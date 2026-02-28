"""
全量化黄金指标埋点
《超级PaaS平台全量化体系书》/ RED + 饱和度：延迟、错误率、流量、饱和度。
每个核心接口自带可观测性，开箱即用。
"""
import json
import logging
import time
from typing import Optional

logger = logging.getLogger("suppaas.monitor.golden")

# 黄金指标名（与 Prometheus/OpenTelemetry 语义对齐）
METRIC_LATENCY = "suppaas_request_duration_ms"
METRIC_ERROR_RATE = "suppaas_request_errors_total"
METRIC_TRAFFIC = "suppaas_request_total"
METRIC_SATURATION = "suppaas_saturation"  # 如队列深度、连接池使用率


def emit_golden_metrics(
    cell: str,
    path: str,
    status_code: int,
    duration_ms: int,
    trace_id: str,
    saturation: Optional[float] = None,
) -> None:
    """
    为单次请求发射黄金指标（延迟、错误、流量、可选饱和度）。
    外部可聚合为：延迟分位、错误率、QPS、饱和度。
    """
    tags = {"cell": cell, "path": path, "trace_id": trace_id}
    ts = time.time()
    # 延迟
    logger.info(json.dumps({
        "metric": METRIC_LATENCY,
        "value": float(duration_ms),
        "tags": {**tags, "quantile": "raw"},
        "ts": ts,
    }, ensure_ascii=False))
    # 错误（1 或 0）
    err = 1 if status_code >= 500 else (1 if status_code >= 400 else 0)
    logger.info(json.dumps({
        "metric": METRIC_ERROR_RATE,
        "value": err,
        "tags": tags,
        "ts": ts,
    }, ensure_ascii=False))
    # 流量
    logger.info(json.dumps({
        "metric": METRIC_TRAFFIC,
        "value": 1,
        "tags": tags,
        "ts": ts,
    }, ensure_ascii=False))
    if saturation is not None:
        logger.info(json.dumps({
            "metric": METRIC_SATURATION,
            "value": saturation,
            "tags": tags,
            "ts": ts,
        }, ensure_ascii=False))


def create_gateway_emit_with_golden(monitor_emit=None):
    """返回可供 create_app(monitor_emit=...) 使用的包装器，在原有 emit 基础上增加黄金指标。"""
    def wrapper(trace_id: str, cell: str, path: str, status_code: int, duration_ms: int) -> None:
        emit_golden_metrics(cell, path, status_code, duration_ms, trace_id, saturation=None)
        if callable(monitor_emit):
            monitor_emit(trace_id, cell, path, status_code, duration_ms)
    return wrapper
