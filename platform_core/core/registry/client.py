"""
细胞注册与发现中心客户端
供网关解析 /api/v1/{cell} 时获取细胞 base_url；支持熔断时按注册表摘除/恢复。
遵循《03_超级_PaaS_平台逻辑全景图》：注册中心服务名 {cell}-cell。
"""
import threading
from typing import Optional


class RegistryClient:
    """细胞注册表：服务名 -> base_url；线程安全。"""

    def __init__(self):
        self._cells = {}
        self._lock = threading.Lock()

    def register(self, cell_name: str, base_url: str) -> None:
        """注册细胞。cell_name 如 crm, erp；base_url 如 https://crm-cell:8001。"""
        with self._lock:
            self._cells[cell_name] = base_url.rstrip("/")

    def deregister(self, cell_name: str) -> None:
        """注销细胞。"""
        with self._lock:
            self._cells.pop(cell_name, None)

    def resolve(self, cell_name: str) -> Optional[str]:
        """解析细胞 base_url；未注册返回 None（网关可返回 503）。"""
        with self._lock:
            return self._cells.get(cell_name)

    def list_cells(self):
        """返回已注册细胞名列表。"""
        with self._lock:
            return list(self._cells.keys())


# 单例，供网关与测试使用
_default_registry: Optional[RegistryClient] = None


def get_registry() -> RegistryClient:
    global _default_registry
    if _default_registry is None:
        _default_registry = RegistryClient()
    return _default_registry
