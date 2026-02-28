"""
治理中心：细胞健康定时巡检，更新注册表健康状态，实现故障自动隔离与自动恢复
不侵入细胞代码，仅对已注册细胞 GET /health。
性能优化：可选连接池复用，降低服务端资源占用；间隔与超时可调以减轻负载。
"""
import logging
import os
import threading
import time
from typing import Callable

logger = logging.getLogger("governance.health")

# 可选：连接池复用（需 urllib3）
_health_pool = None
_health_pool_lock = threading.Lock()


def _get_health_pool():
    global _health_pool
    if _health_pool is not None:
        return _health_pool
    with _health_pool_lock:
        if _health_pool is not None:
            return _health_pool
        try:
            import urllib3
            maxsize = int(os.environ.get("GOVERNANCE_HEALTH_POOL_MAXSIZE", "4"))
            _health_pool = urllib3.PoolManager(num_pools=32, maxsize=maxsize, block=False)
        except ImportError:
            _health_pool = False
        return _health_pool


def run_health_loop(
    get_cells_and_urls: Callable[[], list],
    set_healthy: Callable[[str, bool], None],
    interval_sec: float = 30,
    failure_threshold: int = 3,
    timeout_sec: float = 5,
) -> threading.Thread:
    """
    后台线程：周期性对 get_cells_and_urls() 返回的 (cell, base_url) 做 GET /health，
    连续 failure_threshold 次失败则 set_healthy(cell, False)，任一次成功则 set_healthy(cell, True)（故障自动恢复）。
    参数可由环境变量覆盖：GOVERNANCE_HEALTH_INTERVAL_SEC、GOVERNANCE_HEALTH_FAILURE_THRESHOLD、GOVERNANCE_HEALTH_TIMEOUT_SEC。
    """
    interval_sec = float(os.environ.get("GOVERNANCE_HEALTH_INTERVAL_SEC", str(interval_sec)))
    failure_threshold = int(os.environ.get("GOVERNANCE_HEALTH_FAILURE_THRESHOLD", str(failure_threshold)))
    timeout_sec = float(os.environ.get("GOVERNANCE_HEALTH_TIMEOUT_SEC", str(timeout_sec)))
    failures: dict = {}
    stop = [False]  # 可被外部置 True 以停止

    def _check_one(cell: str, base_url: str) -> bool:
        url = f"{base_url.rstrip('/')}/health"
        pool = _get_health_pool()
        if pool is not False:
            try:
                import urllib3
                r = pool.request("GET", url, timeout=urllib3.util.Timeout(connect=2, read=timeout_sec), retries=False)
                return 200 <= r.status < 300
            except Exception as e:
                logger.debug("health check failed cell=%s url=%s err=%s", cell, base_url, e)
                return False
        try:
            import urllib.request
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=timeout_sec) as r:
                return 200 <= r.status < 300
        except Exception as e:
            logger.debug("health check failed cell=%s url=%s err=%s", cell, base_url, e)
            return False

    def _loop():
        while not stop[0]:
            try:
                for cell, base_url in get_cells_and_urls():
                    if stop[0]:
                        break
                    ok = _check_one(cell, base_url)
                    if not ok:
                        failures[cell] = failures.get(cell, 0) + 1
                        set_healthy(cell, failures[cell] < failure_threshold)
                    else:
                        failures[cell] = 0
                        set_healthy(cell, True)  # 一次成功即恢复，支持故障自动恢复
            except Exception as e:
                logger.warning("health loop error: %s", e)
            time.sleep(interval_sec)

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    return t
