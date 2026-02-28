"""
网关防刷/限流：按 IP 与按 Token 双维度，内存滑动窗口。
不修改核心路由逻辑；未配置时跳过限流。
"""
from __future__ import annotations

import os
import time
import threading
from typing import Dict, Optional, Tuple

# 默认：每 IP 每分钟 120 次；每 Token 每分钟 200 次
RATE_LIMIT_IP_PER_MIN = int(os.environ.get("GATEWAY_RATE_LIMIT_IP_PER_MIN", "120"))
RATE_LIMIT_TOKEN_PER_MIN = int(os.environ.get("GATEWAY_RATE_LIMIT_TOKEN_PER_MIN", "200"))
# 是否启用限流（0 关闭）
RATE_LIMIT_ENABLED = os.environ.get("GATEWAY_RATE_LIMIT_ENABLED", "1") == "1"

_lock = threading.Lock()
_ip_ts: Dict[str, list] = {}  # ip -> [ts, ts, ...]
_token_ts: Dict[str, list] = {}  # token -> [ts, ts, ...]
_WINDOW = 60.0  # 秒


def _prune(ts_list: list, window: float) -> list:
    now = time.time()
    return [t for t in ts_list if now - t < window]


def allow_request(ip: str, token: Optional[str]) -> Tuple[bool, str]:
    """
    返回 (是否放行, 原因)。
    若未启用限流则始终放行。
    """
    if not RATE_LIMIT_ENABLED:
        return True, ""
    now = time.time()
    with _lock:
        # 按 IP
        _ip_ts[ip] = _prune(_ip_ts.get(ip, []), _WINDOW)
        if len(_ip_ts[ip]) >= RATE_LIMIT_IP_PER_MIN:
            return False, "RATE_LIMIT_IP"
        _ip_ts[ip].append(now)
        # 按 Token（若有）
        if token:
            _token_ts[token] = _prune(_token_ts.get(token, []), _WINDOW)
            if len(_token_ts[token]) >= RATE_LIMIT_TOKEN_PER_MIN:
                return False, "RATE_LIMIT_TOKEN"
            _token_ts[token].append(now)
    return True, ""


def record_request(ip: str, token: Optional[str]) -> None:
    """已由 allow_request 记录；此接口保留用于扩展。"""
    pass

# 登录接口专用：每 IP 每分钟尝试次数，防暴力破解
LOGIN_RATE_PER_IP_PER_MIN = int(os.environ.get("GATEWAY_LOGIN_RATE_PER_IP_PER_MIN", "10"))
_login_ip_ts: Dict[str, list] = {}
_LOGIN_LOCK = threading.Lock()


def allow_login(ip: str) -> Tuple[bool, str]:
    """登录接口限流：每 IP 每分钟最多 LOGIN_RATE_PER_IP_PER_MIN 次。"""
    if not RATE_LIMIT_ENABLED:
        return True, ""
    now = time.time()
    with _LOGIN_LOCK:
        _login_ip_ts[ip] = _prune(_login_ip_ts.get(ip, []), _WINDOW)
        if len(_login_ip_ts[ip]) >= LOGIN_RATE_PER_IP_PER_MIN:
            return False, "LOGIN_RATE_LIMIT"
        _login_ip_ts[ip].append(now)
    return True, ""
