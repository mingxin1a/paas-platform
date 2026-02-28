# 鉴权：仅通过标准化 HTTP 调用平台认证，不依赖 platform_core 代码
from __future__ import annotations

import os
from typing import Optional

import urllib.request

from .config import PLATFORM_AUTH_URL, AUTH_STRICT


def validate_token(authorization: Optional[str]) -> tuple[bool, str]:
    """
    校验 Token。若配置 PLATFORM_AUTH_URL 则 GET {url}/api/auth/me 带 Authorization；
    未配置且非 AUTH_STRICT 时接受任意 Bearer（本地联调）。
    返回 (ok, message)。
    """
    if not authorization or not authorization.strip().startswith("Bearer "):
        return False, "缺少 Authorization 或 Bearer"
    if not PLATFORM_AUTH_URL:
        if AUTH_STRICT:
            return False, "未配置平台认证地址且已启用严格鉴权"
        return True, ""
    url = f"{PLATFORM_AUTH_URL.rstrip('/')}/api/auth/me"
    try:
        req = urllib.request.Request(url, method="GET", headers={"Authorization": authorization.strip()})
        with urllib.request.urlopen(req, timeout=5) as r:
            if 200 <= r.status < 300:
                return True, ""
            return False, "平台认证返回非 2xx"
    except Exception as e:
        return False, str(e)
