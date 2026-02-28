"""
治理中心标准化 API：注册发现、健康巡检、链路追踪、RED 指标
不侵入业务细胞，由网关/侧车上报或拉取。
"""
import os
import time
import logging
from flask import Flask, request, jsonify

from .store import GovernanceStore

logger = logging.getLogger("governance")
app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

_store: GovernanceStore = GovernanceStore()


def _seed_from_env():
    """从环境变量 CELL_*_URL 预填注册表，便于 Docker 一键启动。"""
    for key, val in os.environ.items():
        if key.startswith("CELL_") and key.endswith("_URL") and val:
            cell = key[5:-4].lower()
            _store.register(cell, val.strip().rstrip("/"))
            logger.info("governance seed cell=%s url=%s", cell, val)


def _start_health_loop():
    from .health_runner import run_health_loop
    run_health_loop(
        get_cells_and_urls=lambda: _store.get_cells_for_health_check(),
        set_healthy=lambda cell, healthy: _store.set_health(cell, healthy, time.time()),
        interval_sec=float(os.environ.get("GOVERNANCE_HEALTH_INTERVAL_SEC", "30")),
        failure_threshold=int(os.environ.get("GOVERNANCE_HEALTH_FAILURE_THRESHOLD", "3")),
        timeout_sec=float(os.environ.get("GOVERNANCE_HEALTH_TIMEOUT_SEC", "5")),
    )


# ---------- 注册与发现 ----------
@app.route("/api/governance/register", methods=["POST"])
def register():
    """注册细胞。body: { "cell": "crm", "base_url": "http://crm-cell:8001" }"""
    if not request.is_json:
        return jsonify({"code": "BAD_REQUEST", "message": "Content-Type: application/json"}), 400
    body = request.get_json() or {}
    cell = (body.get("cell") or "").strip().lower()
    base_url = (body.get("base_url") or "").strip()
    if not cell or not base_url:
        return jsonify({"code": "BAD_REQUEST", "message": "cell 与 base_url 必填"}), 400
    _store.register(cell, base_url)
    return jsonify({"ok": True, "cell": cell, "base_url": base_url.rstrip("/")}), 200


@app.route("/api/governance/register/<cell>", methods=["DELETE"])
def deregister(cell):
    """注销细胞。"""
    cell = cell.strip().lower()
    _store.deregister(cell)
    return jsonify({"ok": True, "cell": cell}), 200


@app.route("/api/governance/cells", methods=["GET"])
def list_cells():
    """细胞列表及健康状态。"""
    data = _store.list_cells()
    return jsonify({"data": data, "total": len(data)}), 200


@app.route("/api/governance/discovery/<cell>", methods=["GET"])
def discovery(cell):
    """服务发现：仅返回健康细胞的 base_url，否则 503（故障隔离）。"""
    cell = cell.strip().lower()
    base_url = _store.resolve(cell)
    if not base_url:
        return jsonify({"code": "CELL_UNAVAILABLE", "message": "细胞未注册或不可用"}), 503
    return jsonify({"base_url": base_url}), 200


# ---------- 数据上报（网关调用，不侵入细胞） ----------
@app.route("/api/governance/ingest", methods=["POST"])
def ingest():
    """网关上报：链路 span + RED 指标。body: trace_id, span_id, cell, path, status_code, duration_ms"""
    if not request.is_json:
        return jsonify({"code": "BAD_REQUEST", "message": "Content-Type: application/json"}), 400
    body = request.get_json() or {}
    trace_id = body.get("trace_id") or ""
    span_id = body.get("span_id") or ""
    cell = (body.get("cell") or "").strip().lower()
    path = body.get("path") or ""
    status_code = int(body.get("status_code", 0))
    duration_ms = int(body.get("duration_ms", 0))
    if not cell:
        return jsonify({"code": "BAD_REQUEST", "message": "cell 必填"}), 400
    _store.add_span(trace_id, span_id, cell, path, status_code, duration_ms)
    _store.ingest(cell, path, status_code, duration_ms)
    return jsonify({"ok": True}), 200


# ---------- 链路追踪 ----------
@app.route("/api/governance/traces", methods=["GET"])
def get_trace():
    """按 trace_id 查询链路。"""
    trace_id = request.args.get("trace_id", "").strip()
    if not trace_id:
        return jsonify({"code": "BAD_REQUEST", "message": "trace_id 必填"}), 400
    trace = _store.get_trace(trace_id)
    if not trace:
        return jsonify({"code": "NOT_FOUND", "message": "链路不存在或已过期"}), 404
    return jsonify(trace), 200


# ---------- RED 指标（对齐全量化体系） ----------
@app.route("/api/governance/metrics", methods=["GET"])
def get_metrics():
    """RED 指标：?cell=xxx 单细胞，否则全部。对齐全量化体系（request_total、success_rate、duration_ms_p50/p99）。"""
    cell = request.args.get("cell", "").strip().lower() or None
    out = _store.get_metrics(cell)
    if cell:
        if cell not in out:
            return jsonify({"code": "NOT_FOUND", "message": "细胞无指标"}), 404
        return jsonify(out[cell]), 200
    return jsonify(out), 200


# ---------- 健康 ----------
@app.route("/api/governance/health", methods=["GET"])
def health():
    """治理中心自身健康。"""
    return jsonify({"status": "up", "service": "governance"}), 200


@app.route("/api/governance/health/cells", methods=["GET"])
def health_cells():
    """各细胞健康状态摘要（与 /api/governance/cells 一致）。"""
    data = _store.list_cells()
    return jsonify({"data": data, "total": len(data)}), 200


def create_app(store: GovernanceStore = None):
    """工厂：注入 store 便于测试。"""
    global _store
    if store is not None:
        _store = store
    _seed_from_env()
    _start_health_loop()
    return app


# 直接运行时的入口
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _seed_from_env()
    _start_health_loop()
    port = int(os.environ.get("GOVERNANCE_PORT", "8005"))
    app.run(host="0.0.0.0", port=port)
