# 请求级依赖：request_id、tenant_id、鉴权，供 main 与 routers 使用，避免循环导入
from __future__ import annotations

from contextvars import ContextVar
from typing import Optional

from fastapi import Header, HTTPException

from .auth import validate_token

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")
tenant_id_ctx: ContextVar[str] = ContextVar("tenant_id", default="default")


def get_request_id() -> str:
    return request_id_ctx.get()


def get_tenant_id() -> str:
    return tenant_id_ctx.get()


def get_owner_id(x_user_id: Optional[str] = Header(None, alias="X-User-Id")) -> Optional[str]:
    """数据权限：返回当前用户 ID（销售只能看自己的客户时用），来自请求头 X-User-Id。"""
    return (x_user_id or "").strip() or None


def get_data_scope_owner(
    x_data_scope: Optional[str] = Header(None, alias="X-Data-Scope"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
) -> Optional[str]:
    """行级数据权限：当 X-Data-Scope=self 时仅返回本人数据，返回 X-User-Id 作为 owner_id；否则返回 None（看全部）。"""
    if (x_data_scope or "").strip().lower() == "self":
        return (x_user_id or "").strip() or None
    return None


async def require_auth(authorization: Optional[str] = Header(None)):
    """《接口设计说明书》3.1.3：请求头必须包含 Authorization。"""
    ok, msg = validate_token(authorization)
    if not ok:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "UNAUTHORIZED",
                "message": msg or "鉴权失败",
                "details": "",
                "requestId": get_request_id(),
            },
        )
    return authorization
