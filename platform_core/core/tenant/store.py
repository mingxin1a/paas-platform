"""
租户生命周期管理：创建、启用/禁用、到期回收、数据隔离校验。
存储仅租户元数据（id/name/status/expire_at），不存业务数据；不同租户数据 100% 隔离。
"""
import os
import time
import threading
from typing import Any, Dict, List, Optional

# 状态
STATUS_ENABLED = "enabled"
STATUS_DISABLED = "disabled"
# 默认租户，始终存在且启用
DEFAULT_TENANT_ID = "default"


class TenantStore:
    """租户注册表：tenant_id -> { id, name, status, expire_at, created_at }。"""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._tenants: Dict[str, Dict[str, Any]] = {}
        self._ensure_default()

    def _ensure_default(self) -> None:
        with self._lock:
            if DEFAULT_TENANT_ID not in self._tenants:
                self._tenants[DEFAULT_TENANT_ID] = {
                    "id": DEFAULT_TENANT_ID,
                    "name": "默认租户",
                    "status": STATUS_ENABLED,
                    "expire_at": None,
                    "created_at": time.time(),
                }

    def create(self, tenant_id: str, name: str, expire_at: Optional[float] = None) -> Dict[str, Any]:
        """创建租户，默认启用。返回租户信息。"""
        tenant_id = (tenant_id or "").strip()
        name = (name or tenant_id or "").strip()
        if not tenant_id:
            raise ValueError("tenant_id 必填")
        with self._lock:
            if tenant_id in self._tenants:
                raise ValueError("租户已存在")
            self._tenants[tenant_id] = {
                "id": tenant_id,
                "name": name,
                "status": STATUS_ENABLED,
                "expire_at": expire_at,
                "created_at": time.time(),
            }
            return dict(self._tenants[tenant_id])

    def get(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return dict(self._tenants[tenant_id]) if tenant_id in self._tenants else None

    def is_valid(self, tenant_id: str) -> bool:
        """是否有效：存在、启用、未到期。用于网关校验，确保仅合法租户可访问。"""
        if not tenant_id:
            return False
        with self._lock:
            t = self._tenants.get(tenant_id)
            if not t:
                return False
            if t.get("status") != STATUS_ENABLED:
                return False
            exp = t.get("expire_at")
            if exp is not None and time.time() > exp:
                return False
            return True

    def enable(self, tenant_id: str) -> None:
        with self._lock:
            if tenant_id in self._tenants:
                self._tenants[tenant_id]["status"] = STATUS_ENABLED

    def disable(self, tenant_id: str) -> None:
        with self._lock:
            if tenant_id == DEFAULT_TENANT_ID:
                return
            if tenant_id in self._tenants:
                self._tenants[tenant_id]["status"] = STATUS_DISABLED

    def set_expire_at(self, tenant_id: str, expire_at: Optional[float]) -> None:
        with self._lock:
            if tenant_id in self._tenants:
                self._tenants[tenant_id]["expire_at"] = expire_at

    def list_tenants(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [dict(t) for t in self._tenants.values()]

    def delete(self, tenant_id: str) -> bool:
        """删除租户（仅元数据）；禁止删除 default。"""
        with self._lock:
            if tenant_id == DEFAULT_TENANT_ID:
                return False
            if tenant_id in self._tenants:
                del self._tenants[tenant_id]
                return True
            return False


_store: Optional[TenantStore] = None
_store_lock = threading.Lock()


def get_tenant_store() -> TenantStore:
    global _store
    if _store is not None:
        return _store
    with _store_lock:
        if _store is not None:
            return _store
        _store = TenantStore()
        return _store
