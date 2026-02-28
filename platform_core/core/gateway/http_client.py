"""
网关 HTTP 转发性能优化：连接池复用、可选 GET 缓存、压缩传输。
- 连接池：urllib3 PoolManager 复用 TCP 连接，降低转发耗时。
- GET 缓存：对 GET 请求且 2xx 响应做短 TTL 缓存，避免重复穿透细胞（可选）。
- 压缩：向上游发送 Accept-Encoding: gzip；向客户端返回时对较大 body 做 gzip 压缩（可选）。
不改变与 Cell 的接口契约，100% 兼容现有调用。
"""
import os
import time
import gzip
import logging
import threading
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("gateway.http_client")

# 连接池单例（懒加载）
_pool: Optional[Any] = None
_pool_lock = threading.Lock()

# GET 缓存：key -> (status, headers_list, body, expire_ts)
_get_cache: Dict[str, Tuple[int, List[Tuple[str, str]], bytes, float]] = {}
_get_cache_lock = threading.Lock()
_CACHE_MAX = int(os.environ.get("GATEWAY_GET_CACHE_MAX", "1000"))
_CACHE_TTL_SEC = float(os.environ.get("GATEWAY_GET_CACHE_TTL_SEC", "0"))  # 0=关闭缓存；建议 10 用于列表/健康等读多场景
_COMPRESS_MIN_BYTES = int(os.environ.get("GATEWAY_COMPRESS_MIN_BYTES", "256"))


def _get_pool():
    """获取或创建全局连接池。"""
    global _pool
    if _pool is not None:
        return _pool
    with _pool_lock:
        if _pool is not None:
            return _pool
        try:
            import urllib3
            # 商用默认：更大连接池以支持 500+ 并发，可通过环境变量覆盖
            num_pools = int(os.environ.get("GATEWAY_POOL_NUM_POOLS", "64"))
            maxsize = int(os.environ.get("GATEWAY_POOL_MAXSIZE", "16"))
            _pool = urllib3.PoolManager(num_pools=num_pools, maxsize=maxsize, block=False)
            logger.info("gateway http pool created num_pools=%s maxsize=%s", num_pools, maxsize)
        except ImportError:
            _pool = False  # 标记为无 urllib3
        return _pool


def _cache_key(cell: str, path: str, query: str) -> str:
    return f"{cell}:{path}:{query}"


def _get_cached(key: str) -> Optional[Tuple[int, Dict[str, str], bytes]]:
    """返回 (status, headers_dict, body) 或 None。"""
    with _get_cache_lock:
        if key not in _get_cache:
            return None
        status, headers_list, body, expire = _get_cache[key]
        if time.time() > expire:
            del _get_cache[key]
            return None
        return status, dict(headers_list), body


def _set_cache(key: str, status: int, headers: Dict[str, str], body: bytes) -> None:
    with _get_cache_lock:
        while len(_get_cache) >= _CACHE_MAX:
            oldest = min(_get_cache.keys(), key=lambda k: _get_cache[k][3])
            del _get_cache[oldest]
        headers_list = [(k, v) for k, v in headers.items() if k.lower() not in ("transfer-encoding", "connection")]
        _get_cache[key] = (status, headers_list, body, time.time() + _CACHE_TTL_SEC)


def _compress_if_needed(body: bytes, accept_encoding: str) -> Tuple[bytes, bool]:
    """若客户端支持 gzip 且 body 足够大则压缩，返回 (body, was_compressed)。"""
    if not body or len(body) < _COMPRESS_MIN_BYTES:
        return body, False
    if "gzip" not in (accept_encoding or "").lower():
        return body, False
    try:
        return gzip.compress(body, compresslevel=6), True
    except Exception:
        return body, False


def forward_request(
    base_url: str,
    path: str,
    method: str,
    body: Optional[bytes],
    headers: Dict[str, str],
    timeout: float = 30,
    max_retries: int = 2,
    cell: str = "",
    query_string: str = "",
    use_cache: bool = True,
    client_accept_encoding: Optional[str] = None,
) -> Tuple[int, Dict[str, str], bytes]:
    """
    使用连接池转发请求，可选 GET 缓存与响应压缩。
    返回 (status_code, response_headers, body_bytes)。
    """
    pool = _get_pool()
    if pool is False:
        return _fallback_forward(base_url, path, method, body, headers, timeout, max_retries, client_accept_encoding, query_string)

    method = method.upper()
    url = f"{base_url.rstrip('/')}/{path}" + (f"?{query_string}" if query_string else "")
    is_get = method == "GET"
    cache_key = _cache_key(cell, path, query_string or "") if is_get and use_cache else None

    if is_get and use_cache and _CACHE_TTL_SEC > 0 and cache_key:
        cached = _get_cached(cache_key)
        if cached:
            status, hdrs, b = cached
            b, compressed = _compress_if_needed(b, client_accept_encoding or "")
            if compressed:
                hdrs = {**hdrs, "Content-Encoding": "gzip"}
            return status, hdrs, b

    forward_headers = dict(headers)
    if "Accept-Encoding" not in [k for k in forward_headers if k.lower() == "accept-encoding"]:
        forward_headers["Accept-Encoding"] = "gzip"

    import urllib3 as _urllib3
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            resp = pool.request(
                method,
                url,
                body=body,
                headers=forward_headers,
                timeout=_urllib3.util.Timeout(connect=5, read=timeout),
                retries=False,
            )
            data = resp.data
            if resp.headers.get("Content-Encoding", "").lower() == "gzip" and data:
                try:
                    data = gzip.decompress(data)
                except Exception:
                    pass
            status = resp.status
            out_headers = {k: v for k, v in resp.headers.items() if k.lower() not in ("transfer-encoding", "connection")}

            if is_get and 200 <= status < 300 and use_cache and _CACHE_TTL_SEC > 0 and cache_key:
                _set_cache(cache_key, status, out_headers, data)

            data, compressed = _compress_if_needed(data, client_accept_encoding or "")
            if compressed:
                out_headers = {**out_headers, "Content-Encoding": "gzip"}

            if 500 <= status < 600 and attempt < max_retries:
                time.sleep(0.2 * (2 ** attempt))
                continue
            return status, out_headers, data
        except Exception as e:
            last_exc = e
            if attempt < max_retries:
                time.sleep(0.2 * (2 ** attempt))
                continue
            raise last_exc

    raise last_exc or RuntimeError("forward failed")


def _fallback_forward(
    base_url: str,
    path: str,
    method: str,
    body: Optional[bytes],
    headers: Dict[str, str],
    timeout: float,
    max_retries: int,
    client_accept_encoding: Optional[str],
    query_string: str = "",
) -> Tuple[int, Dict[str, str], bytes]:
    """无 urllib3 时回退到 urllib。"""
    import urllib.request
    import urllib.error
    url = f"{base_url.rstrip('/')}/{path}" + (f"?{query_string}" if query_string else "")
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(url, data=body, method=method.upper())
            for k, v in headers.items():
                req.add_header(k, v)
            if "Accept-Encoding" not in headers:
                req.add_header("Accept-Encoding", "gzip")
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = r.read()
                if r.headers.get("Content-Encoding", "").lower() == "gzip" and data:
                    try:
                        data = gzip.decompress(data)
                    except Exception:
                        pass
                out_h = {k: v for k, v in r.headers.items() if k.lower() not in ("transfer-encoding", "connection")}
                data, compressed = _compress_if_needed(data, client_accept_encoding or "")
                if compressed:
                    out_h = {**out_h, "Content-Encoding": "gzip"}
                return r.getcode(), out_h, data
        except urllib.error.HTTPError as e:
            last_exc = e
            data = e.read() if e.fp else b"{}"
            if attempt < max_retries and 500 <= e.code < 600:
                time.sleep(0.2 * (2 ** attempt))
                continue
            out_h = {"Content-Type": e.headers.get("Content-Type", "application/json")}
            return e.code, out_h, data
        except Exception as e:
            last_exc = e
            if attempt < max_retries:
                time.sleep(0.2 * (2 ** attempt))
                continue
            raise e
    raise last_exc or RuntimeError("forward failed")


