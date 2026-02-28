"""
事件总线：重试、死信队列、消息幂等（平台层通用能力，无业务逻辑）。
供网关 POST/GET /api/events 使用；生产可对接 Kafka/RabbitMQ，此处为内存 Stub。
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

# 幂等：已接受的 eventId 集合，避免重复入库（TTL 简化：保留最近 N 条）
_IDEM_MAX = int(os.environ.get("EVENT_BUS_IDEM_MAX", "5000"))
_IDEM: Dict[str, float] = {}
_EVENTS: List[Dict[str, Any]] = []
_DLQ: List[Dict[str, Any]] = []
_MAX_EVENTS = int(os.environ.get("EVENT_BUS_MAX_EVENTS", "1000"))
_MAX_DLQ = int(os.environ.get("EVENT_BUS_MAX_DLQ", "500"))
_RETRY_COUNT = int(os.environ.get("EVENT_BUS_RETRY_COUNT", "3"))


def _trim_idem():
    if len(_IDEM) <= _IDEM_MAX:
        return
    by_ts = sorted(_IDEM.items(), key=lambda x: x[1])
    for k, _ in by_ts[: len(_IDEM) - _IDEM_MAX]:
        del _IDEM[k]


def accept_event(
    event_id: str,
    event_type: str,
    trace_id: str = "",
    payload: Optional[Dict[str, Any]] = None,
    retry_count: int = 0,
) -> tuple[bool, str]:
    """
    接受事件：幂等（同一 eventId 仅接受一次）；超限或重试失败入 DLQ。
    返回 (accepted, reason)。
    """
    _trim_idem()
    if event_id in _IDEM:
        return True, "idempotent_accepted"
    if retry_count > _RETRY_COUNT:
        entry = {
            "eventId": event_id,
            "eventType": event_type,
            "traceId": trace_id,
            "payload": payload,
            "reason": "max_retry_exceeded",
            "ts": time.time(),
        }
        _DLQ.append(entry)
        while len(_DLQ) > _MAX_DLQ:
            _DLQ.pop(0)
        return False, "moved_to_dlq"
    _IDEM[event_id] = time.time()
    entry = {
        "eventId": event_id,
        "eventType": event_type,
        "traceId": trace_id,
        "payload": payload or {},
        "ts": time.time(),
    }
    _EVENTS.append(entry)
    while len(_EVENTS) > _MAX_EVENTS:
        _EVENTS.pop(0)
    return True, "accepted"


def list_events(topic_prefix: str = "", since_ts: float = 0, limit: int = 100) -> List[Dict[str, Any]]:
    """按 topic 前缀、时间戳过滤，返回最近事件。性能：按 ts 有序，二分查找 since_ts 起点。"""
    import bisect
    if not _EVENTS:
        return []
    ts_list = [e.get("ts", 0) for e in _EVENTS]
    i = bisect.bisect_left(ts_list, since_ts)
    out = _EVENTS[i:]
    if topic_prefix:
        prefix = (topic_prefix.split(".")[0] or "").strip()
        if prefix:
            out = [e for e in out if (e.get("eventType") or "").startswith(prefix)]
    return out[-limit:]


def list_dlq(limit: int = 100) -> List[Dict[str, Any]]:
    """死信队列列表（运维排查）。"""
    return _DLQ[-limit:]
