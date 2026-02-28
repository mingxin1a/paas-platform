# 鉴权拦截器 + 请求上下文：《接口设计说明书》请求头 Content-Type、Authorization、X-Request-ID
from __future__ import annotations

import os
import time
import uuid
from contextvars import ContextVar
from typing import Optional

from fastapi import Header, HTTPException, Request

# 请求级上下文
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")
tenant_id_ctx: ContextVar[str] = ContextVar("tenant_id", default="default")


def get_request_id() -> str:
    return request_id_ctx.get()


def get_tenant_id() -> str:
    return tenant_id_ctx.get()


def validate_token(authorization: Optional[str]) -> tuple[bool, str]:
    """通过 HTTP 调用平台认证（不依赖 platform_core）；未配置时接受 Bearer。"""
    if not authorization or not (authorization.strip().startswith("Bearer ") or authorization.strip().startswith("bearer ")):
        return False, "缺少 Authorization 或 Bearer"
    auth_url = os.environ.get("PLATFORM_AUTH_URL", "").strip()
    if not auth_url:
        if os.environ.get("CELL_AUTH_STRICT", "0") == "1":
            return False, "未配置平台认证且已启用严格鉴权"
        return True, ""
    try:
        import urllib.request
        req = urllib.request.Request(f"{auth_url.rstrip('/')}/api/auth/me", method="GET", headers={"Authorization": authorization.strip()})
        with urllib.request.urlopen(req, timeout=5) as r:
            return (200 <= r.status < 300), "" if 200 <= r.status < 300 else "平台认证失败"
    except Exception as e:
        return False, str(e)


async def require_auth(authorization: Optional[str] = Header(None)):
    """鉴权依赖：未通过时返回 401，body 为统一错误格式。"""
    ok, msg = validate_token(authorization)
    if not ok:
        raise HTTPException(
            status_code=401,
            detail={"code": "UNAUTHORIZED", "message": msg or "鉴权失败", "details": "", "requestId": get_request_id()},
        )
    return authorization


def require_request_id(request: Request, method: str) -> None:
    """POST/PUT/PATCH 必须带 X-Request-ID（幂等）。"""
    if method in ("POST", "PUT", "PATCH"):
        rid = request.headers.get("X-Request-ID", "").strip()
        if not rid:
            raise HTTPException(
                status_code=400,
                detail={"code": "BAD_REQUEST", "message": "POST/PUT/PATCH 必须包含 X-Request-ID", "details": "", "requestId": get_request_id()},
            )
