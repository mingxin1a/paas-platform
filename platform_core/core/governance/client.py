"""
治理中心客户端：供网关做服务发现与指标/链路上报
不侵入细胞；网关可选启用（GOVERNANCE_URL 配置）。
高可用：resolve 支持重试与退避，提升故障自动恢复能力。
"""
import logging
import os
import time
import urllib.request
import urllib.error
import json
from typing import Callable, Optional

logger = logging.getLogger("gateway.governance")

# 默认超时与重试
DISCOVERY_TIMEOUT = 5
INGEST_TIMEOUT = 2
DISCOVERY_RETRY_COUNT = 2  # 可被 GOVERNANCE_DISCOVERY_RETRY 覆盖


def _get_base() -> str:
    base = (os.environ.get("GOVERNANCE_URL") or "").strip().rstrip("/")
    return base if base else ""


def _retry_delay(attempt: int) -> float:
    """指数退避 + 轻微抖动（秒）。"""
    try:
        base = float(os.environ.get("GOVERNANCE_DISCOVERY_BACKOFF_BASE", "0.2"))
    except (TypeError, ValueError):
        base = 0.2
    return base * (2 ** attempt) + (hash(str(time.time())) % 50) / 1000.0


def resolve(cell: str) -> Optional[str]:
    """从治理中心解析细胞 base_url（仅健康实例）；失败或未配置返回 None。支持重试与退避。"""
    base = _get_base()
    if not base:
        return None
    url = f"{base}/api/governance/discovery/{cell}"
    max_retries = max(0, int(os.environ.get("GOVERNANCE_DISCOVERY_RETRY", str(DISCOVERY_RETRY_COUNT))))
    timeout = int(os.environ.get("GOVERNANCE_DISCOVERY_TIMEOUT", str(DISCOVERY_TIMEOUT)))
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as r:
                if r.status != 200:
                    last_err = f"status={r.status}"
                    if attempt < max_retries:
                        time.sleep(_retry_delay(attempt))
                        continue
                    return None
                data = json.loads(r.read().decode("utf-8"))
                return (data.get("base_url") or "").strip() or None
        except Exception as e:
            last_err = e
            logger.debug("governance resolve attempt=%s cell=%s err=%s", attempt + 1, cell, e)
            if attempt < max_retries:
                time.sleep(_retry_delay(attempt))
                continue
    return None


def ingest(trace_id: str, span_id: str, cell: str, path: str, status_code: int, duration_ms: int) -> None:
    """上报 span + RED 指标到治理中心；失败仅打日志，不阻塞请求。"""
    base = _get_base()
    if not base:
        return
    url = f"{base}/api/governance/ingest"
    payload = {
        "trace_id": trace_id,
        "span_id": span_id,
        "cell": cell,
        "path": path,
        "status_code": status_code,
        "duration_ms": duration_ms,
    }
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=INGEST_TIMEOUT)
    except Exception as e:
        logger.debug("governance ingest failed trace_id=%s cell=%s err=%s", trace_id, cell, e)


def create_resolver_with_fallback(env_or_file_resolver: Callable[[str], Optional[str]]):
    """返回解析函数：优先治理中心，失败时回退到 env/文件。"""
    def resolve_with_fallback(cell: str) -> Optional[str]:
        u = resolve(cell)
        if u:
            return u
        return env_or_file_resolver(cell)
    return resolve_with_fallback


def create_emit_with_ingest(log_emit: Optional[Callable] = None):
    """返回 monitor_emit 函数：写日志 + 上报治理中心。"""
    def emit(trace_id: str, cell: str, path: str, status_code: int, duration_ms: int) -> None:
        span_id = ""
        try:
            from flask import request as flask_req
            if flask_req:
                span_id = getattr(flask_req, "span_id", "") or ""
        except Exception:
            pass
        if log_emit:
            log_emit(trace_id, cell, path, status_code, duration_ms)
        ingest(trace_id, span_id, cell, path, status_code, duration_ms)
    return emit
