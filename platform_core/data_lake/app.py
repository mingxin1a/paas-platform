"""
数据湖统一 API：汇聚、元数据、血缘、质量、敏感标签、权限、报表与导出。
所有接口需 X-Tenant-Id、Authorization；数据按租户严格隔离。
"""
from __future__ import annotations

import os
from flask import Flask, request, jsonify, Response

from .store import get_store
from .ingest import normalize_batch
from .assets import (
    get_catalog,
    get_lineage,
    get_quality,
    get_sensitive,
    get_quality as get_quality_store,
    SENSITIVE_PII,
)
from .permission import get_permission_store, SCOPE_TABLE, SCOPE_ROW, SCOPE_FIELD
from .reports import get_report_store, run_report, export_csv


def _tenant() -> str:
    return (request.headers.get("X-Tenant-Id") or "").strip() or "default"


def _role() -> str:
    return (request.headers.get("X-Data-Role") or request.headers.get("X-Role") or "user").strip()


def _req_id() -> str:
    return request.headers.get("X-Request-ID", "")


def _error(code: str, message: str, details: str = "", status: int = 400) -> tuple:
    return jsonify({"code": code, "message": message, "details": details, "requestId": _req_id()}), status


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["JSON_AS_ASCII"] = False

    # ---------- 1. 多 Cell 数据汇聚（全量/增量、清洗、标准化） ----------
    @app.route("/api/datalake/ingest", methods=["POST"])
    def ingest():
        """标准化汇聚接口。body: { tenantId, cellId, table, syncType: full|incremental, records: [] }。不侵入 Cell，Cell 仅 POST 此接口。"""
        if not request.is_json:
            return _error("BAD_REQUEST", "Content-Type: application/json", status=400)
        body = request.get_json() or {}
        tenant_id = (body.get("tenantId") or body.get("tenant_id") or _tenant()).strip() or "default"
        cell_id = (body.get("cellId") or body.get("cell_id") or "").strip().lower()
        table = (body.get("table") or "").strip()
        sync_type = (body.get("syncType") or body.get("sync_type") or "incremental").strip().lower()
        if sync_type not in ("full", "incremental"):
            sync_type = "incremental"
        records = body.get("records") or body.get("data") or []
        if not cell_id or not table:
            return _error("BAD_REQUEST", "cellId 与 table 必填", status=400)
        if not isinstance(records, list):
            return _error("BAD_REQUEST", "records 须为数组", status=400)
        normalized = normalize_batch(records, tenant_id, cell_id, table, sync_type)
        count = get_store().ingest(tenant_id, cell_id, table, normalized, sync_type=sync_type)
        get_lineage().record(tenant_id, cell_id, table, source="push", sync_type=sync_type)
        return jsonify({"ok": True, "count": count, "syncType": sync_type}), 201

    @app.route("/api/datalake/query", methods=["GET"])
    def query():
        """查询已汇聚数据。query: tenantId, cellId?, table?, sinceTs?, limit=1000。按租户+权限过滤。"""
        tenant_id = request.args.get("tenantId") or _tenant() or "default"
        cell_id = request.args.get("cellId") or request.args.get("cell_id")
        table = request.args.get("table")
        since_ts = request.args.get("sinceTs")
        since_ts = float(since_ts) if since_ts else None
        limit = min(5000, max(1, int(request.args.get("limit", "1000") or 1000)))
        rows = get_store().query(tenant_id=tenant_id, cell_id=cell_id, table=table, since_ts=since_ts, limit=limit)
        role = _role()
        perm = get_permission_store()
        if cell_id and table and rows:
            rows = perm.apply_row_filter(tenant_id, role, cell_id, table, rows)
            cols = list((rows[0].get("payload") or rows[0]).keys()) if rows else []
            allowed = perm.filter_allowed_columns(tenant_id, role, cell_id, table, cols)
            if allowed != cols:
                rows = [{"payload": {k: (r.get("payload") or r).get(k) for k in allowed if k in (r.get("payload") or r)}} for r in rows]
        return jsonify({"data": rows, "total": len(rows)}), 200

    # ---------- 2. 元数据、血缘、质量、敏感标签 ----------
    @app.route("/api/datalake/metadata", methods=["GET", "PUT"])
    def metadata():
        """GET: 列表/单表元数据。PUT: 注册表元数据。body: { cellId, table, columns: [{ name, type, sensitive? }] }"""
        tenant_id = _tenant() or "default"
        if request.method == "GET":
            cell_id = request.args.get("cellId")
            table = request.args.get("table")
            if cell_id and table:
                m = get_catalog().get(tenant_id, cell_id, table)
                return (jsonify(m), 200) if m else _error("NOT_FOUND", "元数据不存在", status=404)
            return jsonify({"data": get_catalog().list_tables(tenant_id)}), 200
        if not request.is_json:
            return _error("BAD_REQUEST", "Content-Type: application/json", status=400)
        body = request.get_json() or {}
        cell_id = (body.get("cellId") or "").strip().lower()
        table = (body.get("table") or "").strip()
        columns = body.get("columns") or []
        if not cell_id or not table:
            return _error("BAD_REQUEST", "cellId 与 table 必填", status=400)
        get_catalog().register(tenant_id, cell_id, table, columns)
        return jsonify(get_catalog().get(tenant_id, cell_id, table)), 200

    @app.route("/api/datalake/lineage", methods=["GET"])
    def lineage():
        """血缘：?cellId=&table= 返回来源与同步类型。"""
        tenant_id = _tenant() or "default"
        cell_id = (request.args.get("cellId") or "").strip().lower()
        table = (request.args.get("table") or "").strip()
        if not cell_id or not table:
            return _error("BAD_REQUEST", "cellId 与 table 必填", status=400)
        L = get_lineage().get(tenant_id, cell_id, table)
        return (jsonify(L), 200) if L else _error("NOT_FOUND", "无血缘信息", status=404)

    @app.route("/api/datalake/quality/rules", methods=["GET", "POST"])
    def quality_rules():
        """GET: 规则列表。POST: 添加规则。body: { cellId, table, column, rule, params? }"""
        tenant_id = _tenant() or "default"
        if request.method == "GET":
            cell_id = request.args.get("cellId") or ""
            table = request.args.get("table") or ""
            if not cell_id or not table:
                return _error("BAD_REQUEST", "cellId 与 table 必填", status=400)
            return jsonify({"data": get_quality_store().get_rules(tenant_id, cell_id, table)}), 200
        if not request.is_json:
            return _error("BAD_REQUEST", "Content-Type: application/json", status=400)
        body = request.get_json() or {}
        get_quality_store().add_rule(
            tenant_id,
            body.get("cellId", ""),
            body.get("table", ""),
            body.get("column", ""),
            body.get("rule", "not_null"),
            body.get("params"),
        )
        return jsonify({"ok": True}), 201

    @app.route("/api/datalake/sensitive", methods=["GET", "PUT"])
    def sensitive():
        """GET: 列敏感标签。PUT: 打标签。body: { cellId, table, column, tag: pii|phone|idno|email }"""
        tenant_id = _tenant() or "default"
        if request.method == "GET":
            cell_id = request.args.get("cellId") or ""
            table = request.args.get("table") or ""
            if not cell_id or not table:
                return _error("BAD_REQUEST", "cellId 与 table 必填", status=400)
            return jsonify(get_sensitive().get_tags(tenant_id, cell_id, table)), 200
        if not request.is_json:
            return _error("BAD_REQUEST", "Content-Type: application/json", status=400)
        body = request.get_json() or {}
        get_sensitive().tag(tenant_id, body.get("cellId", ""), body.get("table", ""), body.get("column", ""), body.get("tag", SENSITIVE_PII))
        return jsonify({"ok": True}), 200

    # ---------- 3. 数据权限（表/行/字段） ----------
    @app.route("/api/datalake/permission", methods=["GET", "POST"])
    def permission():
        """GET: 当前租户+角色权限列表。POST: 添加规则。body: { role, cellId, table, scope, rowFilter?, allowedColumns? }"""
        tenant_id = _tenant() or "default"
        if request.method == "GET":
            role = request.args.get("role") or _role()
            return jsonify({"data": get_permission_store().get_rules(tenant_id, role)}), 200
        if not request.is_json:
            return _error("BAD_REQUEST", "Content-Type: application/json", status=400)
        body = request.get_json() or {}
        get_permission_store().add_rule(
            tenant_id,
            body.get("role", "user"),
            body.get("cellId", ""),
            body.get("table", ""),
            body.get("scope", SCOPE_TABLE),
            body.get("rowFilter"),
            body.get("allowedColumns"),
        )
        return jsonify({"ok": True}), 201

    # ---------- 4. 统一报表与导出 ----------
    @app.route("/api/datalake/reports", methods=["GET", "POST"])
    def reports_list_or_create():
        """GET: 报表列表。POST: 创建报表。body: { id, name, datasource: { cellId, table }, dimensions, metrics, filters? }"""
        tenant_id = _tenant() or "default"
        if request.method == "GET":
            return jsonify({"data": get_report_store().list_reports(tenant_id)}), 200
        if not request.is_json:
            return _error("BAD_REQUEST", "Content-Type: application/json", status=400)
        body = request.get_json() or {}
        rid = (body.get("id") or body.get("reportId") or "").strip()
        if not rid:
            return _error("BAD_REQUEST", "id 必填", status=400)
        r = get_report_store().save_report(
            rid, tenant_id,
            body.get("name", rid),
            body.get("datasource"),
            body.get("dimensions", []),
            body.get("metrics", []),
            body.get("filters"),
        )
        return jsonify(r), 201

    @app.route("/api/datalake/reports/<report_id>/data", methods=["GET"])
    def report_data(report_id):
        """执行报表，返回数据。format=csv 时导出 CSV。"""
        tenant_id = _tenant() or "default"
        role = _role()
        limit = min(5000, max(1, int(request.args.get("limit", "1000") or 1000)))
        data = run_report(report_id, tenant_id, role, limit=limit)
        fmt = (request.args.get("format") or "").strip().lower()
        if fmt == "csv":
            return Response(export_csv(data), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=report.csv"})
        return jsonify({"data": data, "total": len(data)}), 200

    @app.route("/api/datalake/dashboards", methods=["GET", "POST"])
    def dashboards():
        """大屏：GET 列表，POST 创建。body: { id, name, widgets: [], layout? }"""
        tenant_id = _tenant() or "default"
        if request.method == "GET":
            return jsonify({"data": get_report_store().list_dashboards(tenant_id)}), 200
        if not request.is_json:
            return _error("BAD_REQUEST", "Content-Type: application/json", status=400)
        body = request.get_json() or {}
        did = (body.get("id") or body.get("dashboardId") or "").strip()
        if not did:
            return _error("BAD_REQUEST", "id 必填", status=400)
        d = get_report_store().save_dashboard(did, tenant_id, body.get("name", did), body.get("widgets", []), body.get("layout"))
        return jsonify(d), 201

    @app.route("/api/datalake/export", methods=["POST"])
    def export():
        """通用导出。body: { cellId, table } 或 { reportId }，format: csv。"""
        if not request.is_json:
            return _error("BAD_REQUEST", "Content-Type: application/json", status=400)
        body = request.get_json() or {}
        tenant_id = _tenant() or "default"
        role = _role()
        if body.get("reportId"):
            data = run_report(body["reportId"], tenant_id, role, limit=5000)
        else:
            data = get_store().query(tenant_id=tenant_id, cell_id=body.get("cellId"), table=body.get("table"), limit=5000)
            data = get_permission_store().apply_row_filter(tenant_id, role, body.get("cellId", ""), body.get("table", ""), data)
            data = [r.get("payload") or r for r in data]
        csv_str = export_csv(data)
        return Response(csv_str, mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=export.csv"})

    @app.route("/health")
    def health():
        return jsonify({"status": "up", "service": "data_lake"}), 200

    return app
