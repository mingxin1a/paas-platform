"""
SRM 细胞事件发布：通过 HTTP 向平台事件总线发布领域事件，无 platform_core 依赖。
用于模块间联动（SRM→ERP/OA/数据湖），仅标准化接口，不产生细胞间代码耦合。
"""
from __future__ import annotations

import os
import uuid
import logging

logger = logging.getLogger("srm.events")

def _base_url() -> str:
    u = (os.environ.get("EVENT_BUS_URL") or os.environ.get("GATEWAY_URL") or "").strip().rstrip("/")
    return u

def publish(event_type: str, data: dict, trace_id: str = "", event_id: str = "") -> bool:
    base = _base_url()
    if not base:
        return False
    url = f"{base}/api/events"
    event_id = event_id or str(uuid.uuid4())
    body = {"eventId": event_id, "eventType": event_type, "data": data, "traceId": trace_id}
    token = os.environ.get("EVENT_BUS_TOKEN") or os.environ.get("GATEWAY_TOKEN") or "smoke-test"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    try:
        import urllib.request
        req = urllib.request.Request(url, data=__import__("json").dumps(body).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status in (200, 202):
                return True
    except Exception as e:
        logger.warning("event publish failed: %s %s", event_type, e)
    return False
