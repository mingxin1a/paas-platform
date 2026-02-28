"""
租户级权限：租户管理员、自定义角色、菜单/按钮/数据级三级权限配置。
存储按 tenant_id 隔离；权限校验由网关或认证中心/细胞根据此配置执行。
"""
import threading
from typing import Any, Dict, List, Optional

# 角色码
ROLE_TENANT_ADMIN = "tenant_admin"
ROLE_CUSTOM_PREFIX = "custom_"
# 权限层级
SCOPE_MENU = "menu"
SCOPE_BUTTON = "button"
SCOPE_DATA = "data"


class TenantRoleStore:
    """租户角色与权限：tenant_id -> roles[] (code, name, menus, buttons, data_scope)。"""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        # tenant_id -> [ { "code", "name", "menus": [], "buttons": [], "data_scope": "all|self|dept" } ]
        self._roles: Dict[str, List[Dict[str, Any]]] = {}

    def list_roles(self, tenant_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._roles.get(tenant_id, []))

    def get_role(self, tenant_id: str, role_code: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            for r in self._roles.get(tenant_id, []):
                if r.get("code") == role_code:
                    return dict(r)
            return None

    def set_role(self, tenant_id: str, role_code: str, name: str,
                 menus: Optional[List[str]] = None, buttons: Optional[List[str]] = None,
                 data_scope: Optional[str] = None) -> Dict[str, Any]:
        """设置或更新角色。menus/buttons 为菜单 ID、按钮 ID 列表；data_scope 为 all/self/dept。"""
        with self._lock:
            if tenant_id not in self._roles:
                self._roles[tenant_id] = []
            roles = self._roles[tenant_id]
            for r in roles:
                if r.get("code") == role_code:
                    r["name"] = name or role_code
                    if menus is not None:
                        r["menus"] = list(menus)
                    if buttons is not None:
                        r["buttons"] = list(buttons)
                    if data_scope is not None:
                        r["data_scope"] = data_scope
                    return dict(r)
            role = {
                "code": role_code,
                "name": name or role_code,
                "menus": list(menus or []),
                "buttons": list(buttons or []),
                "data_scope": data_scope or "self",
            }
            roles.append(role)
            return dict(role)

    def delete_role(self, tenant_id: str, role_code: str) -> bool:
        with self._lock:
            if tenant_id not in self._roles:
                return False
            self._roles[tenant_id] = [r for r in self._roles[tenant_id] if r.get("code") != role_code]
            return True

    def ensure_tenant_admin(self, tenant_id: str) -> None:
        """确保租户存在租户管理员角色（默认全部菜单/按钮、data_scope=all）。"""
        with self._lock:
            if tenant_id not in self._roles:
                self._roles[tenant_id] = []
            if not any(r.get("code") == ROLE_TENANT_ADMIN for r in self._roles[tenant_id]):
                self._roles[tenant_id].append({
                    "code": ROLE_TENANT_ADMIN,
                    "name": "租户管理员",
                    "menus": ["*"],
                    "buttons": ["*"],
                    "data_scope": "all",
                })


_role_store: Optional[TenantRoleStore] = None
_role_lock = threading.Lock()


def get_tenant_role_store() -> TenantRoleStore:
    global _role_store
    if _role_store is not None:
        return _role_store
    with _role_lock:
        if _role_store is not None:
            return _role_store
        _role_store = TenantRoleStore()
        return _role_store
