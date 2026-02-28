"""
租户级资源配额：接口请求量、CPU/内存/存储配额配置。
网关仅强制「接口请求量」限流，超配额返回 429；CPU/内存/存储为配置项，由细胞或基础设施按配置执行隔离。
"""
from __future__ import annotations

import os
import time
import threading
from typing import Any, Dict, Optional

# 默认：每租户每分钟请求上限（0 表示不限制）
DEFAULT_REQUESTS_PER_MIN = int(os.environ.get("TENANT_QUOTA_DEFAULT_REQUESTS_PER_MIN", "0"))
_WINDOW_SEC = 60.0


class TenantQuota:
    """租户配额：请求量滑动窗口限流 + 配额配置（CPU/内存/存储为配置，供下游使用）。"""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._quota_config: Dict[str, Dict[str, Any]] = {}  # tenant_id -> { requests_per_min, cpu_limit, memory_mb, storage_gb }
        self._request_ts: Dict[str, list] = {}  # tenant_id -> [ts, ts, ...]
        self._max_ts_entries = 10000

    def _prune(self, ts_list: list) -> list:
        now = time.time()
        return [t for t in ts_list if now - t < _WINDOW_SEC]

    def set_quota(self, tenant_id: str, requests_per_min: Optional[int] = None,
                  cpu_limit: Optional[str] = None, memory_mb: Optional[int] = None,
                  storage_gb: Optional[int] = None) -> Dict[str, Any]:
        """设置租户配额。requests_per_min 由网关限流；其余为配置项。"""
        with self._lock:
            if tenant_id not in self._quota_config:
                self._quota_config[tenant_id] = {}
            q = self._quota_config[tenant_id]
            if requests_per_min is not None:
                q["requests_per_min"] = requests_per_min
            if cpu_limit is not None:
                q["cpu_limit"] = cpu_limit
            if memory_mb is not None:
                q["memory_mb"] = memory_mb
            if storage_gb is not None:
                q["storage_gb"] = storage_gb
            return dict(q)

    def get_quota(self, tenant_id: str) -> Dict[str, Any]:
        with self._lock:
            return dict(self._quota_config.get(tenant_id, {}))

    def allow_request(self, tenant_id: str) -> tuple[bool, str]:
        """
        检查是否允许本次请求（请求量配额）。
        返回 (允许, 原因)；超配额返回 (False, "QUOTA_EXCEEDED")。
        """
        if not tenant_id:
            return True, ""
        with self._lock:
            q = self._quota_config.get(tenant_id, {})
            limit = q.get("requests_per_min")
            if limit is None:
                limit = DEFAULT_REQUESTS_PER_MIN
            if limit <= 0:
                return True, ""
            if tenant_id not in self._request_ts:
                self._request_ts[tenant_id] = []
            self._request_ts[tenant_id] = self._prune(self._request_ts[tenant_id])
            if len(self._request_ts[tenant_id]) >= limit:
                return False, "QUOTA_EXCEEDED"
            self._request_ts[tenant_id].append(time.time())
            if len(self._request_ts) > self._max_ts_entries:
                for k in list(self._request_ts.keys())[:100]:
                    del self._request_ts[k]
            return True, ""


_quota: Optional[TenantQuota] = None
_quota_lock = threading.Lock()


def get_tenant_quota() -> TenantQuota:
    global _quota
    if _quota is not None:
        return _quota
    with _quota_lock:
        if _quota is not None:
            return _quota
        _quota = TenantQuota()
        return _quota
