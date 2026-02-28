"""
依赖注入：数据库会话、当前用户
性能优化：Token 本地缓存与黑名单，避免重复 JWT 校验与数据库查询。
"""
from __future__ import annotations

import os
import time
import threading
from typing import Dict, Generator, Optional

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .database import SessionLocal
from .security import decode_access_token
from .services import UserService

# 本地缓存与黑名单（性能：减少重复 JWT 校验与无效 token 穿透）
_TOKEN_CACHE: Dict[str, tuple] = {}  # token -> (user_id, expire_ts)
_BLACKLIST: Dict[str, float] = {}   # token -> expire_ts
_CACHE_LOCK = threading.RLock()
_AUTH_CACHE_TTL = float(os.environ.get("AUTH_TOKEN_CACHE_TTL_SEC", "60"))
_AUTH_BLACKLIST_TTL = float(os.environ.get("AUTH_BLACKLIST_TTL_SEC", "300"))
_AUTH_CACHE_MAX = int(os.environ.get("AUTH_TOKEN_CACHE_MAX", "5000"))


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """从 Authorization Bearer <token> 解析用户，失败 401。带本地缓存与黑名单，避免重复 JWT 与无效 token 查库。"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少或无效 Authorization")
    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="缺少 token")

    now = time.time()
    with _CACHE_LOCK:
        if token in _BLACKLIST and now < _BLACKLIST[token]:
            raise HTTPException(status_code=401, detail="token 已失效")
        if token in _BLACKLIST:
            del _BLACKLIST[token]
        if token in _TOKEN_CACHE:
            user_id, exp = _TOKEN_CACHE[token]
            if now < exp:
                us = UserService(db)
                user = us.get_by_id(user_id)
                if user and getattr(user, "is_active", True):
                    return user
                del _TOKEN_CACHE[token]
            else:
                del _TOKEN_CACHE[token]

    payload = decode_access_token(token)
    if not payload:
        with _CACHE_LOCK:
            _BLACKLIST[token] = now + _AUTH_BLACKLIST_TTL
        raise HTTPException(status_code=401, detail="token 无效或已过期")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="token 无效")

    us = UserService(db)
    user = us.get_by_id(user_id)
    if not user or not getattr(user, "is_active", True):
        with _CACHE_LOCK:
            _BLACKLIST[token] = now + _AUTH_BLACKLIST_TTL
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")

    with _CACHE_LOCK:
        while len(_TOKEN_CACHE) >= _AUTH_CACHE_MAX:
            _TOKEN_CACHE.pop(next(iter(_TOKEN_CACHE)), None)
        _TOKEN_CACHE[token] = (user_id, now + _AUTH_CACHE_TTL)
    return user


def get_optional_request_id(x_request_id: Optional[str] = Header(None, alias="X-Request-ID")) -> Optional[str]:
    return x_request_id
