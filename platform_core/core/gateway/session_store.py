"""
网关会话/Token 存储抽象（高可用：支持多实例共享；性能：本地缓存与黑名单）。
- 单实例：内存存储，无外部依赖。
- 集群：GATEWAY_SESSION_STORE_URL 指向 Redis 时，多网关实例共享 Token，支持无状态水平扩展与故障转移。
- 性能：可选本地 LRU 缓存减少 Redis 往返；黑名单避免对已失效 Token 重复查询。
不引入业务逻辑，仅提供 token -> user_info 的读写与 TTL。
"""
import os
import json
import logging
import threading
import time
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("gateway.session")

# 本地缓存与黑名单配置（性能优化）
_TOKEN_CACHE_MAX = int(os.environ.get("GATEWAY_TOKEN_CACHE_MAX", "2000"))
_TOKEN_CACHE_TTL_SEC = float(os.environ.get("GATEWAY_TOKEN_CACHE_TTL_SEC", "60"))
_BLACKLIST_TTL_SEC = float(os.environ.get("GATEWAY_TOKEN_BLACKLIST_TTL_SEC", "300"))


def _memory_store() -> "MemoryTokenStore":
    """默认内存存储，单实例或未配置 Redis 时使用。"""
    return MemoryTokenStore()


def _redis_store(url: str) -> Optional["RedisTokenStore"]:
    """可选 Redis 存储，需安装 redis 包；失败时回退内存。"""
    try:
        return RedisTokenStore(url)
    except Exception as e:
        logger.warning("Redis session store init failed, fallback to memory: %s", e)
        return None


class MemoryTokenStore:
    """进程内 Token 存储，不跨实例共享。"""

    def __init__(self) -> None:
        self._data: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    def get(self, token: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._data.get(token)

    def set(self, token: str, user_info: Dict[str, Any], ttl_sec: int = 86400) -> None:
        with self._lock:
            self._data[token] = user_info

    def delete(self, token: str) -> None:
        with self._lock:
            self._data.pop(token, None)


class RedisTokenStore:
    """Redis Token 存储，多网关实例共享，支持会话持久化与故障转移。"""

    def __init__(self, url: str, key_prefix: str = "gateway:token:", default_ttl_sec: int = 86400) -> None:
        import redis
        self._client = redis.from_url(url, decode_responses=True)
        self._prefix = key_prefix
        self._ttl = default_ttl_sec

    def get(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            key = self._prefix + token
            raw = self._client.get(key)
            if not raw:
                return None
            return json.loads(raw)
        except Exception as e:
            logger.debug("redis token get failed: %s", e)
            return None

    def set(self, token: str, user_info: Dict[str, Any], ttl_sec: int = 86400) -> None:
        try:
            key = self._prefix + token
            self._client.setex(key, ttl_sec or self._ttl, json.dumps(user_info, ensure_ascii=False))
        except Exception as e:
            logger.warning("redis token set failed: %s", e)

    def delete(self, token: str) -> None:
        try:
            self._client.delete(self._prefix + token)
        except Exception as e:
            logger.debug("redis token delete failed: %s", e)


class TokenStoreWithCache:
    """包装后端存储：本地 LRU 缓存 + 黑名单，降低重复查询与无效 Token 穿透。"""

    def __init__(self, backend: Any, max_size: int = 2000, cache_ttl_sec: float = 60, blacklist_ttl_sec: float = 300) -> None:
        self._backend = backend
        self._max_size = max_size
        self._cache_ttl = cache_ttl_sec
        self._blacklist_ttl = blacklist_ttl_sec
        self._cache: Dict[str, Tuple[Dict[str, Any], float]] = {}
        self._blacklist: Dict[str, float] = {}
        self._lock = threading.RLock()
        self._order: list = []  # LRU 顺序

    def get(self, token: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            if not token:
                return None
            now = time.time()
            if token in self._blacklist:
                if now < self._blacklist[token]:
                    return None
                del self._blacklist[token]
            if token in self._cache:
                data, exp = self._cache[token]
                if now < exp:
                    self._order.remove(token)
                    self._order.append(token)
                    return data
                del self._cache[token]
                self._order.remove(token)
            data = self._backend.get(token)
            if data is not None:
                while len(self._cache) >= self._max_size and self._order:
                    evict = self._order.pop(0)
                    self._cache.pop(evict, None)
                self._cache[token] = (data, now + self._cache_ttl)
                self._order.append(token)
            else:
                self._blacklist[token] = now + self._blacklist_ttl
            return data

    def set(self, token: str, user_info: Dict[str, Any], ttl_sec: int = 86400) -> None:
        with self._lock:
            self._blacklist.pop(token, None)
            self._backend.set(token, user_info, ttl_sec)
            now = time.time()
            while len(self._cache) >= self._max_size and self._order:
                evict = self._order.pop(0)
                self._cache.pop(evict, None)
            self._cache[token] = (user_info, now + min(self._cache_ttl, float(ttl_sec)))
            if token in self._order:
                self._order.remove(token)
            self._order.append(token)

    def delete(self, token: str) -> None:
        with self._lock:
            self._blacklist[token] = time.time() + self._blacklist_ttl
            self._cache.pop(token, None)
            if token in self._order:
                self._order.remove(token)
            self._backend.delete(token)


def create_token_store():
    """
    根据环境变量创建 Token 存储：
    - GATEWAY_SESSION_STORE_URL 为空：内存存储（单机）。
    - 设置为 redis://... ：Redis 存储（集群多实例共享、会话持久化），并包装本地缓存与黑名单以提升校验性能。
    """
    url = (os.environ.get("GATEWAY_SESSION_STORE_URL") or "").strip()
    if not url:
        return _memory_store()
    if url.startswith("redis://") or url.startswith("rediss://"):
        store = _redis_store(url)
        if store:
            logger.info("gateway session store: redis (cluster-ready) with local cache and blacklist")
            return TokenStoreWithCache(
                store,
                max_size=_TOKEN_CACHE_MAX,
                cache_ttl_sec=_TOKEN_CACHE_TTL_SEC,
                blacklist_ttl_sec=_BLACKLIST_TTL_SEC,
            )
    return _memory_store()
