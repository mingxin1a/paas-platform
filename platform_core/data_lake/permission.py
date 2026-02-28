"""
数据权限：表级/行级/字段级，按租户与角色控制可见数据。
校验在数据湖查询与报表输出时执行，不侵入 Cell。
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

# 权限类型
SCOPE_TABLE = "table"
SCOPE_ROW = "row"
SCOPE_FIELD = "field"


class DataPermissionStore:
    """
    权限规则：tenant_id + role -> [ { scope, table_pattern, row_filter, allowed_columns } ]。
    row_filter 为简单表达式，如 tenant_id=xxx 或 json 路径；实际过滤在 query 时应用。
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        # (tenant_id, role) -> [ { scope, cell_id, table, row_filter, allowed_columns } ]
        self._rules: Dict[tuple, List[Dict[str, Any]]] = {}

    def add_rule(
        self,
        tenant_id: str,
        role: str,
        cell_id: str,
        table: str,
        scope: str = SCOPE_TABLE,
        row_filter: Optional[str] = None,
        allowed_columns: Optional[List[str]] = None,
    ) -> None:
        with self._lock:
            key = (tenant_id or "default", role.strip())
            if key not in self._rules:
                self._rules[key] = []
            self._rules[key].append({
                "scope": scope,
                "cell_id": cell_id.strip().lower(),
                "table": table.strip(),
                "row_filter": row_filter,
                "allowed_columns": list(allowed_columns or []),
            })

    def get_rules(self, tenant_id: str, role: str) -> List[Dict[str, Any]]:
        with self._lock:
            key = (tenant_id or "default", role.strip())
            return list(self._rules.get(key, []))

    def filter_allowed_columns(self, tenant_id: str, role: str, cell_id: str, table: str, columns: List[str]) -> List[str]:
        """返回该租户+角色在此表上允许的列；若无规则则全部允许。"""
        rules = self.get_rules(tenant_id, role)
        for r in rules:
            if r.get("cell_id") == cell_id and r.get("table") == table:
                allowed = r.get("allowed_columns") or []
                if not allowed:
                    return list(columns)
                return [c for c in columns if c in allowed]
        return list(columns)

    def apply_row_filter(self, tenant_id: str, role: str, cell_id: str, table: str, records: List[Dict]) -> List[Dict]:
        """根据 row_filter 过滤记录（简单 key=value）。无规则则全部返回。"""
        rules = self.get_rules(tenant_id, role)
        row_filter = None
        for r in rules:
            if r.get("cell_id") == cell_id and r.get("table") == table and r.get("scope") == SCOPE_ROW:
                row_filter = r.get("row_filter")
                break
        if not row_filter:
            return list(records)
        # 简单解析 "key=value" 或 "key:value"
        parts = row_filter.replace(":", "=").split("=", 1)
        if len(parts) != 2:
            return list(records)
        k, v = parts[0].strip(), parts[1].strip()
        return [rec for rec in records if str(rec.get(k)) == v]


_perm_store: Optional[DataPermissionStore] = None
_perm_lock = threading.Lock()


def get_permission_store() -> DataPermissionStore:
    global _perm_store
    if _perm_store is None:
        with _perm_lock:
            if _perm_store is None:
                _perm_store = DataPermissionStore()
    return _perm_store
