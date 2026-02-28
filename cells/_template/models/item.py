# 示例实体：复制模板后替换为订单、物料、工单等业务模型
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())


def _id() -> str:
    return str(uuid.uuid4()).replace("-", "")[:16]


# 内存存储示例（生产可换为 SQLite/MySQL 等）
_store: Dict[str, Dict[str, Any]] = {}
_idempotent: Dict[str, str] = {}


def list_items(tenant_id: str, page: int = 1, page_size: int = 20) -> tuple[list, int]:
    out = [v for v in _store.values() if v.get("tenantId") == tenant_id]
    total = len(out)
    start = (page - 1) * page_size
    return out[start : start + page_size], total


def get_item(tenant_id: str, item_id: str) -> Optional[Dict[str, Any]]:
    v = _store.get(item_id)
    if v and v.get("tenantId") == tenant_id:
        return v
    return None


def create_item(tenant_id: str, name: str, extra: Optional[Dict] = None) -> Dict[str, Any]:
    iid = _id()
    now = _ts()
    obj = {
        "itemId": iid,
        "tenantId": tenant_id,
        "name": name,
        "status": 1,
        "createdAt": now,
        "updatedAt": now,
        **(extra or {}),
    }
    _store[iid] = obj
    return obj


def update_item(tenant_id: str, item_id: str, name: Optional[str] = None, **kwargs) -> Optional[Dict[str, Any]]:
    obj = get_item(tenant_id, item_id)
    if not obj:
        return None
    if name is not None:
        obj["name"] = name
    for k, v in kwargs.items():
        if v is not None and k in obj:
            obj[k] = v
    obj["updatedAt"] = _ts()
    return obj


def delete_item(tenant_id: str, item_id: str) -> bool:
    obj = _store.get(item_id)
    if obj and obj.get("tenantId") == tenant_id:
        del _store[item_id]
        return True
    return False


def idempotent_get(request_id: str) -> Optional[str]:
    return _idempotent.get(request_id)


def idempotent_set(request_id: str, resource_id: str) -> None:
    _idempotent[request_id] = resource_id
