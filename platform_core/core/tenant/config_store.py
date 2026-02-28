"""
租户级配置中心：租户自定义系统参数、审批流程、界面风格等。
仅存储租户维度 key-value，不影响平台全局配置；数据按 tenant_id 隔离。
"""
import threading
from typing import Any, Dict, List, Optional

# 命名空间：系统参数、审批流程、界面
NS_SYSTEM = "system"
NS_APPROVAL = "approval"
NS_UI = "ui"


class TenantConfigStore:
    """租户配置：tenant_id -> namespace -> key -> value。"""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._config: Dict[str, Dict[str, Dict[str, Any]]] = {}  # tenant_id -> ns -> key -> value

    def get(self, tenant_id: str, namespace: str, key: str) -> Optional[Any]:
        with self._lock:
            if tenant_id not in self._config:
                return None
            if namespace not in self._config[tenant_id]:
                return None
            return self._config[tenant_id][namespace].get(key)

    def set(self, tenant_id: str, namespace: str, key: str, value: Any) -> None:
        with self._lock:
            if tenant_id not in self._config:
                self._config[tenant_id] = {}
            if namespace not in self._config[tenant_id]:
                self._config[tenant_id][namespace] = {}
            self._config[tenant_id][namespace][key] = value

    def get_namespace(self, tenant_id: str, namespace: str) -> Dict[str, Any]:
        with self._lock:
            if tenant_id not in self._config or namespace not in self._config[tenant_id]:
                return {}
            return dict(self._config[tenant_id][namespace])

    def set_namespace(self, tenant_id: str, namespace: str, kv: Dict[str, Any]) -> None:
        with self._lock:
            if tenant_id not in self._config:
                self._config[tenant_id] = {}
            self._config[tenant_id][namespace] = dict(kv)

    def list_namespaces(self, tenant_id: str) -> List[str]:
        with self._lock:
            if tenant_id not in self._config:
                return []
            return list(self._config[tenant_id].keys())


_config_store: Optional[TenantConfigStore] = None
_config_lock = threading.Lock()


def get_tenant_config_store() -> TenantConfigStore:
    global _config_store
    if _config_store is not None:
        return _config_store
    with _config_lock:
        if _config_store is not None:
            return _config_store
        _config_store = TenantConfigStore()
        return _config_store
