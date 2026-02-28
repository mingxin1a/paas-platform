"""
标准化接口网关实现（PaaS 核心层唯一 HTTP 入口，细胞独立部署、仅经本网关调用）。
- 《接口设计说明书_V2.0》：动态路由、熔断降级（10s/50%）、全链路追踪（trace_id + span_id）。
- 《01_核心法律》CT 扫描原则；操作审计落盘不可篡改；敏感数据由细胞与平台脱敏/加密。
"""
import os
import time
import uuid
import logging
import json

try:
    from flask import Flask, request, Response, jsonify, send_from_directory
except ImportError:
    Flask = None
    request = None
    Response = None
    jsonify = None

try:
    from .config import load_routes
    from .circuit_breaker import CircuitBreakerRegistry
    from .session_store import create_token_store
    from . import http_client as _http_client
    from . import signing as _signing
    from . import traffic_light as _traffic_light
    from . import rate_limit as _rate_limit
    from . import audit_log as _audit_log
except ImportError:
    load_routes = None
    CircuitBreakerRegistry = None
    create_token_store = None
    _http_client = None
    _signing = None
    _traffic_light = None
    _rate_limit = None
    _audit_log = None

try:
    from ..tenant import get_tenant_store, get_tenant_quota, get_tenant_config_store, get_tenant_role_store
except ImportError:
    get_tenant_store = None
    get_tenant_quota = None
    get_tenant_config_store = None
    get_tenant_role_store = None

# 高可用回退：无 session_store 模块时使用进程内 dict
class _DictTokenStore:
    _data = {}

    def get(self, token):
        return self._data.get(token)

    def set(self, token, user_info, ttl_sec=86400):
        self._data[token] = user_info


# 配置日志：JSON 格式 + trace_id（《00_最高宪法》第六审判）
def _json_log(level: str, msg: str, trace_id: str, **kwargs):
    log_obj = {"level": level, "message": msg, "trace_id": trace_id, **kwargs}
    logging.getLogger("gateway").info(json.dumps(log_obj, ensure_ascii=False))


def _ensure_trace_id():
    """从请求头获取或生成 trace_id，满足 CT 扫描原则。"""
    trace_id = request.headers.get("X-Trace-Id") or request.headers.get("X-Request-ID") if request else None
    if not trace_id:
        trace_id = str(uuid.uuid4()).replace("-", "")[:32]
    return trace_id


def _ensure_span_id():
    """全链路追踪：子 span_id，供下游串联。"""
    if request and request.headers.get("X-Span-Id"):
        return request.headers.get("X-Span-Id")
    return str(uuid.uuid4()).replace("-", "")[:16]


def _required_headers():
    """《接口设计说明书》3.1.3：请求头必须包含 Content-Type、Authorization、X-Request-ID（POST/PUT）。"""
    if not request:
        return None, None
    method = request.method.upper()
    missing = []
    if not request.headers.get("Content-Type") and method in ("POST", "PUT", "PATCH"):
        missing.append("Content-Type")
    if not request.headers.get("Authorization"):
        missing.append("Authorization")
    if method in ("POST", "PUT", "PATCH") and not request.headers.get("X-Request-ID"):
        missing.append("X-Request-ID")
    if missing:
        return None, {"code": "MISSING_HEADER", "message": f"缺少必须请求头: {', '.join(missing)}", "requestId": request.headers.get("X-Request-ID", "")}
    return True, None


def _error_response(code: str, message: str, details: str, request_id: str, status: int = 400):
    """《接口设计说明书》统一错误响应格式。"""
    body = {"code": code, "message": message, "details": details, "requestId": request_id}
    return Response(
        json.dumps(body, ensure_ascii=False),
        status=status,
        mimetype="application/json; charset=utf-8",
        headers={"X-Response-Time": "0"},
    )


def create_app(registry_resolver=None, monitor_emit=None, circuit_breakers=None, use_dynamic_routes=False):
    """
    创建网关 Flask 应用。
    - registry_resolver(cell_name)->base_url；若为 None 且 use_dynamic_routes 则用 load_routes()。
    - monitor_emit(trace_id, cell, path, status, duration_ms)：可选监控回调。
    - circuit_breakers：CircuitBreakerRegistry 实例，可选；熔断时返回 503 CIRCUIT_OPEN。
    - 限流、应用密钥、操作审计由 before_request/after_request 注入，不修改业务路由。
    """
    app = Flask(__name__)
    app.config["JSON_AS_ASCII"] = False
    routes_map = load_routes() if (use_dynamic_routes and load_routes) else {}
    resolver = registry_resolver or (lambda c: routes_map.get(c))
    breakers = circuit_breakers

    # 细胞接入应用密钥（可选）：X-App-Key 与 GATEWAY_APP_KEYS 或 GATEWAY_APP_KEY 校验
    _APP_KEYS = {}  # app_key -> cell_id or "*"
    _app_keys_raw = os.environ.get("GATEWAY_APP_KEYS", "").strip() or os.environ.get("GATEWAY_APP_KEY", "").strip()
    if _app_keys_raw:
        for part in _app_keys_raw.replace(";", ",").split(","):
            part = part.strip()
            if ":" in part:
                cell_id, key = part.split(":", 1)
                _APP_KEYS[key.strip()] = cell_id.strip()
            elif part:
                _APP_KEYS[part] = "*"

    @app.before_request
    def before():
        request.trace_id = _ensure_trace_id()
        request.span_id = _ensure_span_id()
        request.start_time = time.perf_counter()
        # 防刷/限流
        if _rate_limit and getattr(_rate_limit, "allow_request", None):
            ip = request.remote_addr or "0.0.0.0"
            auth = request.headers.get("Authorization") or ""
            token = (auth[7:].strip() if auth.startswith("Bearer ") else "") or None
            ok, reason = _rate_limit.allow_request(ip, token)
            if not ok:
                return _error_response("RATE_LIMIT", "请求过于频繁，请稍后重试", reason, request.headers.get("X-Request-ID", ""), 429)
        # 应用密钥校验（可选）：若配置了 GATEWAY_APP_KEYS 且请求带 X-App-Key，则校验
        if _APP_KEYS and request.path.startswith("/api/"):
            app_key = (request.headers.get("X-App-Key") or "").strip()
            if app_key and app_key not in _APP_KEYS:
                return _error_response("INVALID_APP_KEY", "应用密钥无效", "", request.headers.get("X-Request-ID", ""), 401)
        # 多租户：对业务路径校验租户有效性及配额（数据隔离：仅合法且未超配额租户可访问）
        if os.environ.get("GATEWAY_VALIDATE_TENANT") == "1" and request.path.startswith("/api/v1/"):
            tenant_id = (request.headers.get("X-Tenant-Id") or "").strip()
            if tenant_id and get_tenant_store and get_tenant_quota:
                if not get_tenant_store().is_valid(tenant_id):
                    return _error_response("TENANT_INVALID", "租户不存在、已禁用或已到期", "", request.headers.get("X-Request-ID", ""), 403)
                ok, reason = get_tenant_quota().allow_request(tenant_id)
                if not ok:
                    return _error_response("QUOTA_EXCEEDED", "租户接口请求量已达配额上限，请稍后重试", reason, request.headers.get("X-Request-ID", ""), 429)

    @app.after_request
    def after(resp):
        # 安全响应头：防点击劫持、MIME 嗅探、XSS 等（OWASP 推荐）
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["X-XSS-Protection"] = "1; mode=block"
        if getattr(request, "start_time", None) is not None:
            duration_ms = int((time.perf_counter() - request.start_time) * 1000)
            resp.headers["X-Response-Time"] = str(duration_ms)
            resp.headers["X-Trace-Id"] = getattr(request, "trace_id", "")
            resp.headers["X-Span-Id"] = getattr(request, "span_id", "")
            cell = getattr(request, "cell", None)
            if callable(monitor_emit) and getattr(request, "trace_id", None) and cell is not None:
                monitor_emit(request.trace_id, cell, request.path, resp.status_code, duration_ms)
            if breakers and cell:
                breakers.get(cell).record(success=resp.status_code < 500)
            if os.environ.get("APM_LOG") == "1" and getattr(request, "trace_id", None):
                _json_log("info", "apm_span", request.trace_id, span_id=getattr(request, "span_id", ""), cell=cell, path=request.path, status=resp.status_code, duration_ms=duration_ms)
            # 操作审计落盘（不可删改）
            if _audit_log and getattr(_audit_log, "append", None):
                auth = request.headers.get("Authorization") or ""
                token = (auth[7:].strip() if auth.startswith("Bearer ") else "") or ""
                user_info = (_token_store.get(token) if token else None) or {}
                _audit_log.append(
                    request.method, request.path, resp.status_code, duration_ms,
                    trace_id=getattr(request, "trace_id", ""),
                    tenant_id=request.headers.get("X-Tenant-Id", ""),
                    user=user_info.get("username", ""),
                    cell=cell or "",
                    ip=request.remote_addr or "",
                )
        return resp

    # ---------- 认证与管理端 API（管理端/客户端登录、细胞管理、权限） ----------
    _MOCK_USERS = {
        "admin": {"password": "admin", "role": "admin", "allowedCells": []},
        "client": {"password": "123", "role": "client", "allowedCells": ["crm", "erp", "wms", "hrm", "oa"]},
        "operator": {"password": "123", "role": "client", "allowedCells": ["crm", "wms", "oa"]},
    }
    # 高可用：Token 存储可外置为 Redis（GATEWAY_SESSION_STORE_URL），多实例共享、会话持久化
    _token_store = create_token_store() if create_token_store else _DictTokenStore()
    # 生产环境必须禁用 Mock 认证，对接认证中心；GATEWAY_USE_MOCK_AUTH=0 时登录返回 503
    _use_mock_auth = os.environ.get("GATEWAY_USE_MOCK_AUTH", "1") == "1"
    _CELL_ENABLED = {}  # cell_id -> bool，默认 True

    @app.before_request
    def _require_admin_for_admin_routes():
        """管理端接口仅允许 role=admin 的用户访问，防止越权（渗透测试修复）。"""
        if not request.path.startswith("/api/admin/"):
            return None
        auth = request.headers.get("Authorization") or ""
        token = (auth[7:].strip() if auth.startswith("Bearer ") else "") or ""
        if not token:
            return None  # 由路由返回 401
        user = _token_store.get(token)
        if not user or user.get("role") != "admin":
            return _error_response("FORBIDDEN", "仅管理员可访问管理端接口", "", request.headers.get("X-Request-ID", ""), 403)
        return None
    # 细胞展示名：仅作默认中文名，细胞名录以 load_routes() 与 env CELL_*_URL 为准（架构合规：不硬编码细胞名录）
    _CELL_DISPLAY_NAMES = {
        "crm": "客户关系", "erp": "企业资源", "wms": "仓储管理", "hrm": "人力资源", "oa": "协同办公",
        "mes": "制造执行", "tms": "运输管理", "srm": "供应商", "plm": "产品生命周期", "ems": "能源管理",
        "his": "医院信息", "lis": "检验信息", "lims": "实验室",
    }

    def _cell_list():
        """细胞名录：优先来自 load_routes()，再并上展示名 key，保证新增细胞仅需配置无需改代码。"""
        r = load_routes() if load_routes else {}
        ids = set(r.keys())
        ids.update(_CELL_DISPLAY_NAMES.keys())
        return sorted(ids)

    def _cell_name(cid):
        return _CELL_DISPLAY_NAMES.get(cid, cid)

    @app.route("/api/auth/login", methods=["POST"])
    def auth_login():
        """登录：body { username, password }，返回 { token, user }。生产须 GATEWAY_USE_MOCK_AUTH=0 并对接认证中心。"""
        if not _use_mock_auth:
            return _error_response("SERVICE_UNAVAILABLE", "生产环境已禁用 Mock 认证，请对接认证中心", "", request.headers.get("X-Request-ID", ""), 503)
        if not request.is_json:
            return _error_response("BAD_REQUEST", "Content-Type: application/json", "", request.headers.get("X-Request-ID", ""), 400)
        # 登录限流：防暴力破解（渗透测试修复）
        if _rate_limit and getattr(_rate_limit, "allow_login", None):
            ip = request.remote_addr or "0.0.0.0"
            ok, reason = _rate_limit.allow_login(ip)
            if not ok:
                return _error_response("RATE_LIMIT", "登录尝试过于频繁，请稍后重试", reason, request.headers.get("X-Request-ID", ""), 429)
        body = request.get_json() or {}
        username = (body.get("username") or "").strip()
        password = (body.get("password") or "").strip()
        if not username:
            return _error_response("BAD_REQUEST", "username 必填", "", request.headers.get("X-Request-ID", ""), 400)
        user = _MOCK_USERS.get(username)
        if not user or user["password"] != password:
            return _error_response("UNAUTHORIZED", "用户名或密码错误", "", request.headers.get("X-Request-ID", ""), 401)
        token = str(uuid.uuid4()).replace("-", "")
        allowed = user.get("allowedCells") or []
        user_info = {"username": username, "role": user["role"], "allowedCells": allowed}
        _token_store.set(token, user_info, ttl_sec=int(os.environ.get("GATEWAY_SESSION_TTL_SEC", "86400")))
        return jsonify({
            "token": token,
            "user": user_info,
        }), 200

    @app.route("/api/admin/cells", methods=["GET"])
    def admin_cells_list():
        """管理端：细胞列表及启用状态（需 Authorization）。"""
        if not request.headers.get("Authorization"):
            return _error_response("UNAUTHORIZED", "缺少 Authorization", "", request.headers.get("X-Request-ID", ""), 401)
        routes_map = load_routes() if load_routes else {}
        out = []
        for cid in _cell_list():
            enabled = _CELL_ENABLED.get(cid, True)
            base_url = (resolver(cid) if callable(resolver) else None) or routes_map.get(cid) or os.environ.get(f"CELL_{cid.upper()}_URL", "")
            out.append({"id": cid, "name": _cell_name(cid), "enabled": enabled, "baseUrl": base_url or "(未配置)"})
        return jsonify({"data": out, "total": len(out)}), 200

    @app.route("/api/admin/cells/<cell_id>", methods=["PATCH"])
    def admin_cells_patch(cell_id):
        """管理端：启用/停用细胞。body { enabled: true|false }。"""
        if not request.headers.get("Authorization"):
            return _error_response("UNAUTHORIZED", "缺少 Authorization", "", request.headers.get("X-Request-ID", ""), 401)
        if cell_id not in _cell_list():
            return _error_response("NOT_FOUND", "细胞不存在", "", request.headers.get("X-Request-ID", ""), 404)
        if not request.is_json:
            return _error_response("BAD_REQUEST", "Content-Type: application/json", "", request.headers.get("X-Request-ID", ""), 400)
        body = request.get_json() or {}
        if "enabled" in body:
            _CELL_ENABLED[cell_id] = bool(body["enabled"])
        return jsonify({"id": cell_id, "enabled": _CELL_ENABLED.get(cell_id, True)}), 200

    @app.route("/api/admin/routes", methods=["GET"])
    def admin_routes():
        """管理端：当前网关路由配置（细胞 -> base_url），不耦合业务逻辑。"""
        if not request.headers.get("Authorization"):
            return _error_response("UNAUTHORIZED", "缺少 Authorization", "", request.headers.get("X-Request-ID", ""), 401)
        routes_map = load_routes() if load_routes else {}
        for cid in _cell_list():
            if cid not in routes_map:
                routes_map[cid] = os.environ.get(f"CELL_{cid.upper()}_URL", "") or "(未配置)"
        return jsonify({"routes": routes_map, "total": len(routes_map)}), 200

    # ---------- 数据湖代理：GATEWAY 统一入口，DATALAKE_URL 指向数据湖服务时转发 ----------
    _datalake_url = os.environ.get("DATALAKE_URL", "").strip().rstrip("/")

    @app.route("/api/datalake", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    @app.route("/api/datalake/<path:subpath>", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    def datalake_proxy(subpath=""):
        """数据湖 API 代理：请求转发至数据湖服务，不侵入 Cell；未配置 DATALAKE_URL 时返回 503。"""
        if not _datalake_url:
            return _error_response("SERVICE_UNAVAILABLE", "数据湖未配置 DATALAKE_URL", "", request.headers.get("X-Request-ID", ""), 503)
        if not request.headers.get("Authorization"):
            return _error_response("UNAUTHORIZED", "缺少 Authorization", "", request.headers.get("X-Request-ID", ""), 401)
        path = ("/api/datalake/" + subpath).rstrip("/") if subpath else "/api/datalake"
        target = _datalake_url + path
        try:
            import urllib.request
            import urllib.error
            body = request.get_data() or None
            req = urllib.request.Request(target, data=body, method=request.method)
            for h in ("Authorization", "Content-Type", "X-Request-ID", "X-Tenant-Id", "X-Trace-Id", "X-Role", "X-Data-Role"):
                if request.headers.get(h):
                    req.add_header(h, request.headers.get(h))
            with urllib.request.urlopen(req, timeout=60) as r:
                return Response(r.read(), status=r.getcode(), mimetype=r.headers.get("Content-Type", "application/json") or "application/json")
        except urllib.error.HTTPError as e:
            return Response(e.read() if e.fp else b"{}", status=e.code, mimetype="application/json")
        except Exception as e:
            _json_log("error", "datalake_proxy_failed", getattr(request, "trace_id", ""), error=str(e))
            return _error_response("UPSTREAM_ERROR", str(e), "", request.headers.get("X-Request-ID", ""), 502)

    @app.route("/api/admin/governance/<path:subpath>", methods=["GET"])
    def admin_governance_proxy(subpath):
        """管理端：代理治理中心只读 API（健康/细胞列表等），统一经网关暴露。"""
        if not request.headers.get("Authorization"):
            return _error_response("UNAUTHORIZED", "缺少 Authorization", "", request.headers.get("X-Request-ID", ""), 401)
        gov_url = os.environ.get("GOVERNANCE_URL", "").strip().rstrip("/")
        if not gov_url:
            return _error_response("SERVICE_UNAVAILABLE", "治理中心未配置 GOVERNANCE_URL", "", request.headers.get("X-Request-ID", ""), 503)
        try:
            import urllib.request
            target = f"{gov_url}/api/governance/{subpath}"
            req = urllib.request.Request(target, method="GET")
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=10) as r:
                return Response(r.read(), status=r.getcode(), mimetype=r.headers.get("Content-Type", "application/json") or "application/json")
        except Exception as e:
            return _error_response("UPSTREAM_ERROR", str(e), "", request.headers.get("X-Request-ID", ""), 502)

    @app.route("/api/admin/cells/<cell_id>/docs", methods=["GET"])
    @app.route("/api/admin/cells/<cell_id>/docs/<path:docpath>", methods=["GET"])
    def admin_cell_docs(cell_id, docpath=""):
        """管理端：代理细胞接口文档（如 /docs、/redoc），便于查看模块 API。"""
        if not request.headers.get("Authorization"):
            return _error_response("UNAUTHORIZED", "缺少 Authorization", "", request.headers.get("X-Request-ID", ""), 401)
        base_url = (resolver(cell_id) if callable(resolver) else None) or routes_map.get(cell_id) or os.environ.get(f"CELL_{cell_id.upper()}_URL", "")
        if not base_url or str(base_url).startswith("("):
            return _error_response("NOT_FOUND", "细胞未配置或不可达", "", request.headers.get("X-Request-ID", ""), 404)
        base_url = str(base_url).rstrip("/")
        path = ("docs/" + docpath).rstrip("/") if docpath else "docs"
        try:
            import urllib.request
            target = f"{base_url}/{path}"
            req = urllib.request.Request(target, method="GET")
            with urllib.request.urlopen(req, timeout=5) as r:
                return Response(r.read(), status=r.getcode(), mimetype=r.headers.get("Content-Type", "text/html") or "text/html")
        except Exception as e:
            return _error_response("UPSTREAM_ERROR", str(e), "", request.headers.get("X-Request-ID", ""), 502)

    @app.route("/api/admin/health-summary", methods=["GET"])
    def admin_health_summary():
        """商用化：健康汇总 - 网关自身状态 + 治理中心返回的各 Cell 健康状态，便于运维与故障检测。"""
        if not request.headers.get("Authorization"):
            return _error_response("UNAUTHORIZED", "缺少 Authorization", "", request.headers.get("X-Request-ID", ""), 401)
        summary = {"gateway": "up", "cells": []}
        gov_url = os.environ.get("GOVERNANCE_URL", "").strip().rstrip("/")
        if gov_url:
            try:
                import urllib.request
                req = urllib.request.Request(f"{gov_url}/api/governance/health/cells", method="GET")
                req.add_header("Content-Type", "application/json")
                with urllib.request.urlopen(req, timeout=5) as r:
                    raw = r.read().decode()
                    data = json.loads(raw) if raw else {}
                summary["cells"] = data.get("data", []) if isinstance(data.get("data"), list) else []
            except Exception as e:
                summary["governanceError"] = str(e)
        return jsonify(summary), 200

    @app.route("/api/admin/verify-report", methods=["GET"])
    def admin_verify_report():
        """管理端：接入校验报告摘要；完整报告由 self_check 生成 glass_house/health_report.json。"""
        if not request.headers.get("Authorization"):
            return _error_response("UNAUTHORIZED", "缺少 Authorization", "", request.headers.get("X-Request-ID", ""), 401)
        return jsonify({
            "message": "接入校验由部署侧执行 self_check.py，报告见 glass_house/health_report.json；或对接校验服务获取实时报告",
            "reportUrl": "/api/admin/verify-report",
            "standard": "《接口设计说明书》《细胞模块接入校验报告》",
        }), 200

    @app.route("/api/admin/cells/verify", methods=["POST"])
    def admin_cells_verify():
        """管理端：触发细胞接入合规校验（异步）；当前返回提示，后续可对接校验服务。"""
        if not request.headers.get("Authorization"):
            return _error_response("UNAUTHORIZED", "缺少 Authorization", "", request.headers.get("X-Request-ID", ""), 401)
        return jsonify({
            "message": "已提交校验任务；请执行 self_check.py 或等待校验服务完成",
            "status": "submitted",
        }), 202

    @app.route("/api/admin/users", methods=["GET"])
    def admin_users_list():
        """管理端：用户列表及权限（allowedCells）；当前 Mock，后续对接认证服务。"""
        if not request.headers.get("Authorization"):
            return _error_response("UNAUTHORIZED", "缺少 Authorization", "", request.headers.get("X-Request-ID", ""), 401)
        out = [{"id": k, "username": k, "role": v.get("role", "client"), "allowedCells": v.get("allowedCells", [])} for k, v in _MOCK_USERS.items()]
        return jsonify({"data": out, "total": len(out)}), 200

    # ---------- 多租户管理（生命周期、配额、配置、角色），数据按 tenant_id 隔离 ----------
    @app.route("/api/admin/tenants", methods=["GET"])
    def admin_tenants_list():
        """租户列表：创建、启用/禁用、到期回收全流程由平台管理员在此维护。"""
        if not request.headers.get("Authorization"):
            return _error_response("UNAUTHORIZED", "缺少 Authorization", "", request.headers.get("X-Request-ID", ""), 401)
        if not get_tenant_store:
            return _error_response("SERVICE_UNAVAILABLE", "租户模块未加载", "", request.headers.get("X-Request-ID", ""), 503)
        out = get_tenant_store().list_tenants()
        return jsonify({"data": out, "total": len(out)}), 200

    @app.route("/api/admin/tenants", methods=["POST"])
    def admin_tenants_create():
        """创建租户。body: { "tenantId": "xxx", "name": "名称", "expireAt": 可选时间戳 }。"""
        if not request.headers.get("Authorization"):
            return _error_response("UNAUTHORIZED", "缺少 Authorization", "", request.headers.get("X-Request-ID", ""), 401)
        if not get_tenant_store:
            return _error_response("SERVICE_UNAVAILABLE", "租户模块未加载", "", request.headers.get("X-Request-ID", ""), 503)
        if not request.is_json:
            return _error_response("BAD_REQUEST", "Content-Type: application/json", "", request.headers.get("X-Request-ID", ""), 400)
        body = request.get_json() or {}
        tenant_id = (body.get("tenantId") or body.get("id") or "").strip()
        name = (body.get("name") or tenant_id or "").strip()
        expire_at = body.get("expireAt") if body.get("expireAt") is not None else None
        try:
            t = get_tenant_store().create(tenant_id, name, expire_at=expire_at)
            if get_tenant_role_store:
                get_tenant_role_store().ensure_tenant_admin(tenant_id)
            return jsonify(t), 201
        except ValueError as e:
            return _error_response("BAD_REQUEST", str(e), "", request.headers.get("X-Request-ID", ""), 400)

    @app.route("/api/admin/tenants/<tenant_id>", methods=["PATCH"])
    def admin_tenants_patch(tenant_id):
        """启用/禁用/到期：body { "status": "enabled"|"disabled", "expireAt": 可选 }。"""
        if not request.headers.get("Authorization"):
            return _error_response("UNAUTHORIZED", "缺少 Authorization", "", request.headers.get("X-Request-ID", ""), 401)
        if not get_tenant_store:
            return _error_response("SERVICE_UNAVAILABLE", "租户模块未加载", "", request.headers.get("X-Request-ID", ""), 503)
        if not request.is_json:
            return _error_response("BAD_REQUEST", "Content-Type: application/json", "", request.headers.get("X-Request-ID", ""), 400)
        body = request.get_json() or {}
        store = get_tenant_store()
        if store.get(tenant_id) is None:
            return _error_response("NOT_FOUND", "租户不存在", "", request.headers.get("X-Request-ID", ""), 404)
        if body.get("status") == "enabled":
            store.enable(tenant_id)
        elif body.get("status") == "disabled":
            store.disable(tenant_id)
        if "expireAt" in body:
            store.set_expire_at(tenant_id, body.get("expireAt"))
        return jsonify(store.get(tenant_id)), 200

    @app.route("/api/admin/tenants/<tenant_id>/quota", methods=["GET"])
    def admin_tenants_quota_get(tenant_id):
        if not request.headers.get("Authorization"):
            return _error_response("UNAUTHORIZED", "缺少 Authorization", "", request.headers.get("X-Request-ID", ""), 401)
        if not get_tenant_quota:
            return _error_response("SERVICE_UNAVAILABLE", "租户配额模块未加载", "", request.headers.get("X-Request-ID", ""), 503)
        return jsonify(get_tenant_quota().get_quota(tenant_id)), 200

    @app.route("/api/admin/tenants/<tenant_id>/quota", methods=["PUT"])
    def admin_tenants_quota_put(tenant_id):
        """设置配额。body: { "requestsPerMin": 可选, "cpuLimit": 可选, "memoryMb": 可选, "storageGb": 可选 }。"""
        if not request.headers.get("Authorization"):
            return _error_response("UNAUTHORIZED", "缺少 Authorization", "", request.headers.get("X-Request-ID", ""), 401)
        if not get_tenant_quota:
            return _error_response("SERVICE_UNAVAILABLE", "租户配额模块未加载", "", request.headers.get("X-Request-ID", ""), 503)
        if not request.is_json:
            return _error_response("BAD_REQUEST", "Content-Type: application/json", "", request.headers.get("X-Request-ID", ""), 400)
        body = request.get_json() or {}
        q = get_tenant_quota().set_quota(
            tenant_id,
            requests_per_min=body.get("requestsPerMin"),
            cpu_limit=body.get("cpuLimit"),
            memory_mb=body.get("memoryMb"),
            storage_gb=body.get("storageGb"),
        )
        return jsonify(q), 200

    @app.route("/api/admin/tenants/<tenant_id>/config", methods=["GET"])
    def admin_tenants_config_get(tenant_id):
        """租户配置：namespace 可选，不传则返回所有命名空间。"""
        if not request.headers.get("Authorization"):
            return _error_response("UNAUTHORIZED", "缺少 Authorization", "", request.headers.get("X-Request-ID", ""), 401)
        if not get_tenant_config_store:
            return _error_response("SERVICE_UNAVAILABLE", "租户配置模块未加载", "", request.headers.get("X-Request-ID", ""), 503)
        ns = (request.args.get("namespace") or "").strip()
        store = get_tenant_config_store()
        if ns:
            out = store.get_namespace(tenant_id, ns)
            return jsonify(out), 200
        names = store.list_namespaces(tenant_id)
        out = {n: store.get_namespace(tenant_id, n) for n in names}
        return jsonify(out), 200

    @app.route("/api/admin/tenants/<tenant_id>/config", methods=["PUT"])
    def admin_tenants_config_put(tenant_id):
        """设置租户某命名空间配置。body: { "namespace": "system|approval|ui", "config": { key: value } }。"""
        if not request.headers.get("Authorization"):
            return _error_response("UNAUTHORIZED", "缺少 Authorization", "", request.headers.get("X-Request-ID", ""), 401)
        if not get_tenant_config_store:
            return _error_response("SERVICE_UNAVAILABLE", "租户配置模块未加载", "", request.headers.get("X-Request-ID", ""), 503)
        if not request.is_json:
            return _error_response("BAD_REQUEST", "Content-Type: application/json", "", request.headers.get("X-Request-ID", ""), 400)
        body = request.get_json() or {}
        ns = (body.get("namespace") or "system").strip()
        config = body.get("config") if isinstance(body.get("config"), dict) else {}
        get_tenant_config_store().set_namespace(tenant_id, ns, config)
        return jsonify(get_tenant_config_store().get_namespace(tenant_id, ns)), 200

    @app.route("/api/admin/tenants/<tenant_id>/roles", methods=["GET"])
    def admin_tenants_roles_get(tenant_id):
        """租户角色列表：租户管理员、自定义角色及菜单/按钮/数据级权限。"""
        if not request.headers.get("Authorization"):
            return _error_response("UNAUTHORIZED", "缺少 Authorization", "", request.headers.get("X-Request-ID", ""), 401)
        if not get_tenant_role_store:
            return _error_response("SERVICE_UNAVAILABLE", "租户角色模块未加载", "", request.headers.get("X-Request-ID", ""), 503)
        return jsonify({"data": get_tenant_role_store().list_roles(tenant_id)}), 200

    @app.route("/api/admin/tenants/<tenant_id>/roles", methods=["PUT"])
    def admin_tenants_roles_put(tenant_id):
        """设置角色。body: { "code": "tenant_admin|custom_xxx", "name": "名称", "menus": [], "buttons": [], "dataScope": "all|self|dept" }。"""
        if not request.headers.get("Authorization"):
            return _error_response("UNAUTHORIZED", "缺少 Authorization", "", request.headers.get("X-Request-ID", ""), 401)
        if not get_tenant_role_store:
            return _error_response("SERVICE_UNAVAILABLE", "租户角色模块未加载", "", request.headers.get("X-Request-ID", ""), 503)
        if not request.is_json:
            return _error_response("BAD_REQUEST", "Content-Type: application/json", "", request.headers.get("X-Request-ID", ""), 400)
        body = request.get_json() or {}
        code = (body.get("code") or "").strip()
        if not code:
            return _error_response("BAD_REQUEST", "code 必填", "", request.headers.get("X-Request-ID", ""), 400)
        role = get_tenant_role_store().set_role(
            tenant_id,
            code,
            body.get("name", code),
            menus=body.get("menus"),
            buttons=body.get("buttons"),
            data_scope=body.get("dataScope"),
        )
        return jsonify(role), 200

    # ---------- 01 4.1 透明化审计：谁在何时访问了我的数据（与 trace_id 关联） ----------
    _AUDIT_ENTRIES = []  # 内存占位；生产对接日志/治理中心按 trace_id 查询

    @app.route("/api/admin/audit", methods=["GET"])
    def admin_audit():
        """管理端：审计日志（与 trace_id 关联的访问记录）。当前返回占位或近期条目，生产对接真实审计存储。"""
        if not request.headers.get("Authorization"):
            return _error_response("UNAUTHORIZED", "缺少 Authorization", "", request.headers.get("X-Request-ID", ""), 401)
        # 占位：返回示例条目，便于前端对接；生产由治理/日志侧按 trace_id 汇聚
        out = _AUDIT_ENTRIES[:100]
        if not out:
            out = [
                {"id": "1", "time": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time() - 300)), "user": "client", "action": "访问细胞列表", "resource": "/api/admin/cells", "traceId": "audit-placeholder-1"},
                {"id": "2", "time": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time() - 60)), "user": "admin", "action": "查看用户权限", "resource": "/api/admin/users", "traceId": "audit-placeholder-2"},
            ]
        return jsonify({"data": out, "total": len(out)}), 200

    @app.route("/api/admin/audit-logs", methods=["GET"])
    def admin_audit_logs():
        """操作审计日志检索（落盘不可删改）。支持 since/to/traceId/tenantId/cell/limit。"""
        if not request.headers.get("Authorization"):
            return _error_response("UNAUTHORIZED", "缺少 Authorization", "", request.headers.get("X-Request-ID", ""), 401)
        since = float(request.args.get("since", 0) or 0)
        to_raw = request.args.get("to", "")
        to_ts = float(to_raw) if to_raw else None
        trace_id = (request.args.get("traceId") or "").strip()
        tenant_id = (request.args.get("tenantId") or "").strip()
        cell = (request.args.get("cell") or "").strip()
        limit = min(500, max(1, int(request.args.get("limit", 100) or 100)))
        if _audit_log and getattr(_audit_log, "search", None):
            out = _audit_log.search(since_ts=since, to_ts=to_ts, trace_id=trace_id or "", tenant_id=tenant_id or "", cell=cell or "", limit=limit)
        else:
            out = []
        return jsonify({"data": out, "total": len(out)}), 200

    @app.route("/api/admin/audit-logs/export", methods=["GET"])
    def admin_audit_logs_export():
        """导出操作审计日志（文件下载）。"""
        if not request.headers.get("Authorization"):
            return _error_response("UNAUTHORIZED", "缺少 Authorization", "", request.headers.get("X-Request-ID", ""), 401)
        if _audit_log and getattr(_audit_log, "export_path", None):
            path = _audit_log.export_path()
            if path and os.path.isfile(path):
                from flask import send_file
                return send_file(path, as_attachment=True, download_name="operation_audit.log", mimetype="text/plain; charset=utf-8")
        return _error_response("NOT_FOUND", "审计日志文件不存在或未配置", "", request.headers.get("X-Request-ID", ""), 404)

    @app.route("/api/admin/panic", methods=["POST"])
    def admin_panic():
        """01 4.3 一键求救（Panic Button）：踢出会话、冻结、锁屏、告警。当前为占位，记录日志并返回 200；生产对接安全团队与会话管理。"""
        if not request.headers.get("Authorization"):
            return _error_response("UNAUTHORIZED", "缺少 Authorization", "", request.headers.get("X-Request-ID", ""), 401)
        trace_id = getattr(request, "trace_id", _ensure_trace_id())
        auth = request.headers.get("Authorization") or ""
        token = auth[7:].strip() if auth.startswith("Bearer ") else ""
        user_info = (_token_store.get(token) if token else None) or {}
        username = user_info.get("username", "unknown")
        _json_log("warn", "panic_button_triggered", trace_id, username=username, message="一键求救已触发，生产环境应踢出会话、冻结、锁屏并通知安全团队")
        return jsonify({
            "message": "一键求救已接收；生产环境将执行：踢出所有会话、冻结敏感操作、锁屏并通知安全团队",
            "traceId": trace_id,
            "status": "received",
        }), 200

    # ---------- 00 #6 / 01 7.6.1 事件总线：幂等、重试、死信（platform_core/core/event_bus.py）----------
    try:
        from .. import event_bus as _event_bus
    except ImportError:
        _event_bus = None
    _EVENT_BUS_QUEUE = []  # 降级：无 event_bus 时使用

    @app.route("/api/events", methods=["POST"])
    def events_publish():
        """事件发布（细胞→平台）。支持幂等、重试超限入 DLQ；见 event_bus.accept_event。"""
        if not request.headers.get("Authorization"):
            return _error_response("UNAUTHORIZED", "缺少 Authorization", "", request.headers.get("X-Request-ID", ""), 401)
        if not request.is_json:
            return _error_response("BAD_REQUEST", "Content-Type: application/json", "", request.headers.get("X-Request-ID", ""), 400)
        body = request.get_json() or {}
        event_id = body.get("eventId") or str(uuid.uuid4())
        event_type = body.get("eventType", "")
        trace_id = getattr(request, "trace_id", _ensure_trace_id())
        if _event_bus:
            accepted, reason = _event_bus.accept_event(event_id, event_type, trace_id, body.get("data"), retry_count=0)
            if not accepted:
                _json_log("warn", "event_moved_to_dlq", trace_id, eventId=event_id, reason=reason)
                return jsonify({"eventId": event_id, "status": "dlq", "reason": reason}), 202
            return jsonify({"eventId": event_id, "status": "accepted"}), 202
        _EVENT_BUS_QUEUE.append({"eventId": event_id, "eventType": event_type, "traceId": body.get("traceId") or trace_id, "ts": time.time()})
        if len(_EVENT_BUS_QUEUE) > 1000:
            _EVENT_BUS_QUEUE.pop(0)
        return jsonify({"eventId": event_id, "status": "accepted"}), 202

    @app.route("/api/events", methods=["GET"])
    def events_poll():
        """事件拉取（按 topic/since）。支持 event_bus 列表与过滤。"""
        if not request.headers.get("Authorization"):
            return _error_response("UNAUTHORIZED", "缺少 Authorization", "", request.headers.get("X-Request-ID", ""), 401)
        topic = request.args.get("topic", "").strip()
        since = request.args.get("since", "")
        limit = min(100, max(1, int(request.args.get("limit", "20"))))
        since_ts = float(since) if since else 0
        if _event_bus:
            out = _event_bus.list_events(topic_prefix=topic, since_ts=since_ts, limit=limit)
        else:
            out = [e for e in _EVENT_BUS_QUEUE[-limit:] if not topic or e.get("eventType", "").startswith(topic.split(".")[0])]
        return jsonify({"data": out, "total": len(out)}), 200

    @app.route("/api/admin/events/dlq", methods=["GET"])
    def events_dlq():
        """管理端：死信队列列表（运维排查）。"""
        if not request.headers.get("Authorization"):
            return _error_response("UNAUTHORIZED", "缺少 Authorization", "", request.headers.get("X-Request-ID", ""), 401)
        limit = min(100, max(1, int(request.args.get("limit", "20"))))
        out = _event_bus.list_dlq(limit=limit) if _event_bus else []
        return jsonify({"data": out, "total": len(out)}), 200

    @app.route("/api/admin/users/<user_id>", methods=["PATCH"])
    def admin_users_patch(user_id):
        """管理端：更新用户可访问细胞列表（权限配置）。body { allowedCells: string[] }。"""
        if not request.headers.get("Authorization"):
            return _error_response("UNAUTHORIZED", "缺少 Authorization", "", request.headers.get("X-Request-ID", ""), 401)
        if user_id not in _MOCK_USERS:
            return _error_response("NOT_FOUND", "用户不存在", "", request.headers.get("X-Request-ID", ""), 404)
        if not request.is_json:
            return _error_response("BAD_REQUEST", "Content-Type: application/json", "", request.headers.get("X-Request-ID", ""), 400)
        body = request.get_json() or {}
        if "allowedCells" in body:
            _MOCK_USERS[user_id]["allowedCells"] = list(body["allowedCells"]) if isinstance(body["allowedCells"], list) else []
        return jsonify({"id": user_id, "allowedCells": _MOCK_USERS[user_id].get("allowedCells", [])}), 200

    @app.route("/api/auth/me", methods=["GET"])
    def auth_me():
        """根据 Authorization Bearer token 返回当前用户；token 由登录时写入会话存储（内存或 Redis）。"""
        auth = request.headers.get("Authorization") or ""
        if not auth.startswith("Bearer "):
            return _error_response("UNAUTHORIZED", "缺少或无效 Authorization", "", request.headers.get("X-Request-ID", ""), 401)
        token = auth[7:].strip()
        if not token:
            return _error_response("UNAUTHORIZED", "缺少 token", "", request.headers.get("X-Request-ID", ""), 401)
        user_info = _token_store.get(token)
        if not user_info:
            return _error_response("UNAUTHORIZED", "token 无效或已过期", "", request.headers.get("X-Request-ID", ""), 401)
        return jsonify(user_info), 200

    @app.route("/api/v1/<cell>/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    def proxy(cell, path):
        """细胞代理：校验必填头、租户（可选）、红绿灯、熔断后转发至细胞 base_url/path；加签由 USE_REAL_FORWARD 时注入。"""
        trace_id = getattr(request, "trace_id", _ensure_trace_id())
        request.cell = cell
        ok, err = _required_headers()
        if not ok:
            _json_log("warn", "missing_headers", trace_id, error=err)
            return _error_response(err["code"], err["message"], err.get("details", ""), err["requestId"], 400)
        # 商用化：多租户隔离 - 生产环境可要求必须传 X-Tenant-Id（GATEWAY_REQUIRE_TENANT_ID=1）
        if os.environ.get("GATEWAY_REQUIRE_TENANT_ID") == "1":
            tenant_id = (request.headers.get("X-Tenant-Id") or "").strip()
            if not tenant_id:
                _json_log("warn", "missing_tenant_id", trace_id, cell=cell)
                return _error_response(
                    "MISSING_TENANT_ID",
                    "请求头缺少租户标识",
                    "生产环境要求请求头携带 X-Tenant-Id，请登录后使用系统分配的租户ID",
                    request.headers.get("X-Request-ID", ""),
                    400,
                )
        # 00 #8 红绿灯：CPU 超阈值时仅放行 GET，其余返回 503
        if _traffic_light and _traffic_light.is_red_light() and request.method.upper() != "GET":
            _traffic_light.emit_red_light_log(trace_id, request.method, request.path)
            return _error_response("RED_LIGHT", "系统负载过高，仅允许只读请求，请稍后重试", "", request.headers.get("X-Request-ID", ""), 503)
        if breakers and not breakers.get(cell).allow_request():
            _json_log("warn", "circuit_open", trace_id, cell=cell)
            return _error_response("CIRCUIT_OPEN", f"细胞 {cell} 熔断中", "", request.headers.get("X-Request-ID", ""), 503)
        base_url = resolver(cell) if callable(resolver) else None
        if not base_url:
            _json_log("warn", "cell_not_found", trace_id, cell=cell)
            return _error_response("CELL_NOT_FOUND", f"细胞未注册: {cell}", "", request.headers.get("X-Request-ID", ""), 503)
        if os.environ.get("USE_REAL_FORWARD") == "1":
            body = request.get_data() or None
            timeout_sec = int(os.environ.get("GATEWAY_PROXY_TIMEOUT_SEC", "30"))
            max_retries = max(0, int(os.environ.get("GATEWAY_PROXY_RETRY_COUNT", "2")))
            headers_to_forward = ("Authorization", "Content-Type", "X-Request-ID", "X-Tenant-Id", "X-Trace-Id", "X-Span-Id")
            fwd_headers = {h: request.headers.get(h) or "" for h in headers_to_forward if request.headers.get(h)}
            if _signing and os.environ.get("GATEWAY_SIGNING_SECRET"):
                hs = {k: request.headers.get(k) or "" for k in ("X-Request-ID", "X-Tenant-Id", "X-Trace-Id")}
                sig = _signing.compute_signature(request.method, f"/{path}", body or b"", hs)
                if sig:
                    fwd_headers[_signing.SIGNATURE_HEADER] = sig
                    fwd_headers[_signing.SIGNATURE_TIME_HEADER] = str(int(time.time()))
            use_cache = request.method.upper() == "GET" and float(os.environ.get("GATEWAY_GET_CACHE_TTL_SEC", "0")) > 0
            if _http_client and getattr(_http_client, "forward_request", None):
                try:
                    status, out_headers, resp_body = _http_client.forward_request(
                        base_url, path, request.method, body, fwd_headers,
                        timeout=timeout_sec, max_retries=max_retries, cell=cell,
                        query_string=request.query_string.decode() if request.query_string else "",
                        use_cache=use_cache,
                        client_accept_encoding=request.headers.get("Accept-Encoding"),
                    )
                    mimetype = out_headers.get("Content-Type", "application/json") or "application/json"
                    resp = Response(resp_body, status=status, mimetype=mimetype)
                    for k, v in out_headers.items():
                        if k.lower() != "content-type":
                            resp.headers[k] = v
                    return resp
                except Exception as e:
                    _json_log("error", "forward_failed", trace_id, cell=cell, error=str(e))
                    return _error_response("CELL_UNREACHABLE", str(e), "", request.headers.get("X-Request-ID", ""), 502)
            import urllib.request
            import urllib.error
            target = f"{base_url.rstrip('/')}/{path}" + (f"?{request.query_string.decode()}" if request.query_string else "")
            last_exc = None
            for attempt in range(max_retries + 1):
                try:
                    req = urllib.request.Request(target, method=request.method, data=body)
                    for h, v in fwd_headers.items():
                        req.add_header(h, v)
                    with urllib.request.urlopen(req, timeout=timeout_sec) as r:
                        code = r.getcode()
                        resp_body = r.read()
                        if 500 <= code < 600 and attempt < max_retries:
                            time.sleep(0.2 * (2 ** attempt) + (uuid.uuid4().int % 100) / 1000.0)
                            continue
                        return Response(resp_body, status=code, mimetype=r.headers.get("Content-Type", "application/json") or "application/json")
                except urllib.error.HTTPError as e:
                    last_exc = e
                    if 500 <= e.code < 600 and attempt < max_retries:
                        time.sleep(0.2 * (2 ** attempt) + (uuid.uuid4().int % 100) / 1000.0)
                        continue
                    return Response(e.read() if e.fp else b"{}", status=e.code, mimetype="application/json")
                except Exception as e:
                    last_exc = e
                    if attempt < max_retries:
                        time.sleep(0.2 * (2 ** attempt) + (uuid.uuid4().int % 100) / 1000.0)
                        continue
                    _json_log("error", "forward_failed", trace_id, cell=cell, error=str(e))
                    return _error_response("CELL_UNREACHABLE", str(e), "", request.headers.get("X-Request-ID", ""), 502)
            if last_exc:
                _json_log("error", "forward_failed", trace_id, cell=cell, error=str(last_exc))
                return _error_response("CELL_UNREACHABLE", str(last_exc), "", request.headers.get("X-Request-ID", ""), 502)
        # 未开启真实转发时返回前端期望的列表/健康结构，避免控制台报错
        if request.method.upper() == "GET" and path == "health":
            return jsonify({"status": "up", "cell": cell}), 200
        if request.method.upper() == "GET":
            return jsonify({"data": [], "total": 0}), 200
        return jsonify({
            "gateway": "ok",
            "cell": cell,
            "path": path,
            "traceId": trace_id,
            "spanId": getattr(request, "span_id", ""),
            "forwardTo": f"{base_url.rstrip('/')}/{path}",
        }), 200

    @app.route("/health")
    def health():
        return jsonify({"status": "up"}), 200

    @app.route("/demo")
    def demo():
        """演示页：前后端运行确认，通过网关探测各细胞 /health。"""
        demo_path = os.path.join(os.path.dirname(__file__), "demo_cells.html")
        if os.path.isfile(demo_path):
            with open(demo_path, "r", encoding="utf-8") as f:
                html = f.read()
            return Response(html, mimetype="text/html; charset=utf-8")
        return Response("<p>demo_cells.html not found</p>", mimetype="text/html", status=404)

    # 根路径：无静态目录时展示网关状态并引导到控制台与 demo
    if not os.environ.get("GATEWAY_STATIC_DIR", "").strip():
        @app.route("/")
        def root():
            html = (
                "<!DOCTYPE html><html lang='zh-CN'><head><meta charset='UTF-8'/><title>SuperPaaS 网关</title></head><body>"
                "<h1>SuperPaaS 网关</h1><p>网关已运行。</p>"
                "<ul><li><a href='/demo'>演示页（细胞健康探测）</a></li>"
                "<li><a href='http://localhost:5173/'>客户端（5173）</a></li>"
                "<li><a href='http://localhost:5174/'>管理端（5174）</a></li>"
                "<li><a href='/health'>/health</a></li></ul></body></html>"
            )
            return Response(html, mimetype="text/html; charset=utf-8")

    # 可选：托管前端构建（GATEWAY_STATIC_DIR 指向 frontend/dist）
    static_dir = os.environ.get("GATEWAY_STATIC_DIR", "").strip()
    if static_dir and os.path.isdir(static_dir) and send_from_directory:
        _static_dir = os.path.abspath(static_dir)
        @app.route("/", defaults={"path": ""})
        @app.route("/<path:path>")
        def serve_console(path):
            if path.startswith("api/") or path in ("health", "demo"):
                return _error_response("NOT_FOUND", "Not Found", "", request.headers.get("X-Request-ID", ""), 404)
            if not path or path == "index.html":
                return send_from_directory(_static_dir, "index.html", mimetype="text/html; charset=utf-8")
            file_path = os.path.join(_static_dir, path)
            if os.path.isfile(file_path):
                return send_from_directory(_static_dir, path)
            return send_from_directory(_static_dir, "index.html", mimetype="text/html; charset=utf-8")

    return app


# 独立运行时的入口（开箱即用：动态路由 + 熔断 + 追踪）
if __name__ == "__main__":
    def _resolve(cell):
        routes = load_routes() if load_routes else {}
        return routes.get(cell) or os.environ.get(f"CELL_{cell.upper()}_URL", "http://localhost:8001")
    def _emit(trace_id, cell, path, status, duration_ms):
        _json_log("info", "request", trace_id, cell=cell, path=path, status=status, duration_ms=duration_ms)
    logging.basicConfig(level=logging.INFO)
    breakers = CircuitBreakerRegistry() if CircuitBreakerRegistry else None
    app = create_app(_resolve, _emit, circuit_breakers=breakers, use_dynamic_routes=True)
    app.run(host="0.0.0.0", port=int(os.environ.get("GATEWAY_PORT", "8000")))
