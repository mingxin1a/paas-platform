"""
动态路由配置
《接口设计说明书》3.3：熔断 10s 内 50% 异常率开启；半开探测后恢复。
零心智负担：开箱即用，从环境变量或默认文件加载。
支持 JSON（routes 对象）与 YAML（gateway_route_spec 格式：routes 数组 id/path_prefix/upstream）。
"""
import os
import json
import re
from typing import Dict

CONFIG_PATH = os.environ.get("GATEWAY_ROUTES_PATH", "")
DEFAULT_ROUTES: Dict[str, str] = {}


def _cell_from_route_item(item: dict) -> str:
    """从 gateway_route_spec 单条（id 或 path_prefix）解析 cell_id。"""
    # path_prefix 如 /api/cells/crm -> crm
    path_prefix = (item.get("path_prefix") or "").strip()
    if path_prefix:
        m = re.match(r"^/api/cells/([a-z0-9_-]+)", path_prefix)
        if m:
            return m.group(1).lower()
    # id 如 cell-crm -> crm
    rid = (item.get("id") or "").strip().lower()
    if rid.startswith("cell-"):
        return rid[5:].split("-")[0] if len(rid) > 5 else rid
    return rid.replace("_", "-") if rid else ""


def _load_routes_from_file(path: str) -> Dict[str, str]:
    """从文件加载路由：支持 .json（routes 对象）或 .yaml/.yml（gateway_route_spec 格式）。"""
    routes: Dict[str, str] = {}
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    path_lower = path.lower()
    if path_lower.endswith(".yaml") or path_lower.endswith(".yml"):
        try:
            import yaml
            data = yaml.safe_load(content) or {}
        except Exception:
            data = {}
        items = data.get("routes") or []
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                cell = _cell_from_route_item(item)
                upstream = (item.get("upstream") or "").strip().rstrip("/")
                if cell and upstream:
                    routes[cell] = upstream
        elif isinstance(items, dict):
            routes.update({k: (v or "").rstrip("/") for k, v in items.items() if k and v})
    else:
        data = json.loads(content) if content.strip() else {}
        raw = data.get("routes", {})
        if isinstance(raw, dict):
            routes.update({k: (v or "").rstrip("/") for k, v in raw.items() if k and v})
    return routes


def load_routes() -> Dict[str, str]:
    """加载 cell -> base_url 映射；优先环境变量 CELL_*_URL，再文件（JSON 或 YAML）。"""
    routes: Dict[str, str] = {}
    for key, val in os.environ.items():
        if key.startswith("CELL_") and key.endswith("_URL"):
            cell = key[5:-4].lower()
            routes[cell] = (val or "").rstrip("/")
    if CONFIG_PATH and os.path.isfile(CONFIG_PATH):
        file_routes = _load_routes_from_file(CONFIG_PATH)
        for cell, url in file_routes.items():
            routes.setdefault(cell, url)
    for cell, url in DEFAULT_ROUTES.items():
        routes.setdefault(cell, url)
    return routes
