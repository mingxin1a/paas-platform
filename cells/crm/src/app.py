"""
CRM 细胞 Flask 应用 - 《接口设计说明书_V2.0》合规。
线索、商机、客户、联系人、360° 视图、预测与赢率分析。
"""
from __future__ import annotations

import csv
import io
import os
import time
import uuid
from datetime import datetime, timezone
from flask import Flask, request, jsonify, Response

from .store import get_store, STAGE_CONFIG, template_merge


def _human_audit(tenant_id: str, operation_desc: str, trace_id: str = "") -> None:
    """01 4.4 人性化日志：谁在何时对何资源做了何操作，与 trace_id 关联。"""
    user_id = request.headers.get("X-User-Id") or request.headers.get("X-Tenant-Id") or "system"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    trace_id = trace_id or request.headers.get("X-Trace-Id") or request.headers.get("X-Request-ID") or ""
    msg = f"【人性化审计】租户 {tenant_id} 用户 {user_id} 在 {ts} {operation_desc}，trace_id={trace_id}"
    import logging
    logging.getLogger("crm.audit").info(msg)

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False


def _tenant() -> str:
    return (request.headers.get("X-Tenant-Id") or "").strip() or "default"


def _request_id() -> str:
    return (request.headers.get("X-Request-ID") or "").strip() or str(uuid.uuid4())


def _err(code: str, message: str, details: str = "", request_id: str = "") -> tuple[dict, int]:
    return (
        {"code": code, "message": message, "details": details, "requestId": request_id or _request_id()},
        400 if code == "BAD_REQUEST" else 404 if code == "NOT_FOUND" else 500,
    )


@app.before_request
def _verify_gateway_signature():
    """01 5.2 / 00 #5 抗抵赖：可选验签，失败返回 403 并记安全审计（黑客入侵日志）。"""
    if os.environ.get("CELL_VERIFY_SIGNATURE") != "1":
        return
    if request.path == "/health":
        return
    try:
        from .signing_verify import verify_signature, write_security_audit
    except ImportError:
        return
    body = request.get_data() or b""
    headers = {
        "X-Signature": request.headers.get("X-Signature") or "",
        "X-Signature-Time": request.headers.get("X-Signature-Time") or "",
        "X-Request-ID": request.headers.get("X-Request-ID") or "",
        "X-Tenant-Id": request.headers.get("X-Tenant-Id") or "",
        "X-Trace-Id": request.headers.get("X-Trace-Id") or "",
    }
    ok, reason = verify_signature(request.method, request.path, body, headers)
    if not ok:
        trace_id = request.headers.get("X-Trace-Id") or request.headers.get("X-Request-ID") or ""
        write_security_audit("signature_verify_failed", reason, path=request.path, trace_id=trace_id)
        return jsonify({
            "code": "SIGNATURE_INVALID",
            "message": "验签失败",
            "details": "黑客入侵/验签失败",
            "requestId": headers.get("X-Request-ID", ""),
        }), 403


@app.before_request
def _start_timer():
    request._start_time = time.time()


@app.after_request
def _response_time(resp):
    if "X-Response-Time" not in resp.headers:
        elapsed = time.time() - getattr(request, "_start_time", time.time())
        resp.headers["X-Response-Time"] = f"{elapsed:.3f}"
    return resp


# ---------- Health ----------
@app.route("/health")
def health():
    return jsonify({"status": "up", "cell": "crm"}), 200


# ---------- Customers ----------
@app.route("/customers", methods=["GET"])
def list_customers():
    tenant_id = _tenant()
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("pageSize", 20))
    data_scope = (request.headers.get("X-Data-Scope") or "").strip()
    owner_id = request.headers.get("X-User-Id") if data_scope == "self" else None
    store = get_store()
    data, total = store.customer_list(tenant_id, page=page, page_size=page_size, owner_id=owner_id)
    return jsonify({"data": data, "total": total}), 200


@app.route("/customers", methods=["POST"])
def create_customer():
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    if store.idempotent_get(req_id):
        return jsonify(_err("IDEMPOTENT_CONFLICT", "幂等冲突，已存在同 X-Request-ID 的资源", "", req_id)), 409
    body = request.get_json() or {}
    name = (body.get("name") or "").strip()
    if not name:
        return jsonify(_err("BAD_REQUEST", "请填写客户名称", "", req_id)), 400
    owner_id = request.headers.get("X-User-Id") or None
    c = store.customer_create(
        tenant_id,
        name,
        body.get("contactPhone"),
        body.get("contactEmail"),
        owner_id=owner_id,
    )
    store.idempotent_set(req_id, c["customerId"])
    _human_audit(tenant_id, f"创建了客户 {name} (customerId={c['customerId']})", request.headers.get("X-Trace-Id") or req_id)
    return jsonify(c), 201


@app.route("/customers/<customer_id>", methods=["GET"])
def get_customer(customer_id: str):
    store = get_store()
    c = store.customer_get(_tenant(), customer_id)
    if not c:
        return jsonify(_err("NOT_FOUND", "客户不存在", "", _request_id())), 404
    return jsonify(c), 200


@app.route("/export/customers", methods=["GET"])
def export_customers():
    """客户列表标准化导出：format=csv 返回 CSV（Excel 可打开）。"""
    tenant_id = _tenant()
    store = get_store()
    data, _ = store.customer_list(tenant_id, page=1, page_size=5000)
    fmt = (request.args.get("format") or "csv").lower()
    if fmt == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["客户ID", "名称", "联系电话", "邮箱", "状态", "创建时间"])
        for c in data:
            w.writerow([c.get("customerId"), c.get("name"), c.get("contactPhone"), c.get("contactEmail"), c.get("status"), c.get("createdAt")])
        return Response(buf.getvalue(), mimetype="text/csv; charset=utf-8-sig", headers={"Content-Disposition": "attachment; filename=customers.csv"})
    return jsonify({"data": data, "total": len(data)}), 200


# ---------- Contacts ----------
@app.route("/contacts", methods=["GET"])
def list_contacts():
    tenant_id = _tenant()
    customer_id = request.args.get("customerId") or None
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("pageSize", 20))
    store = get_store()
    data, total = store.contact_list(tenant_id, customer_id=customer_id, page=page, page_size=page_size)
    return jsonify({"data": data, "total": total}), 200


@app.route("/contacts", methods=["POST"])
def create_contact():
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    if store.idempotent_get(req_id):
        return jsonify(_err("IDEMPOTENT_CONFLICT", "幂等冲突", "", req_id)), 409
    body = request.get_json() or {}
    customer_id = (body.get("customerId") or "").strip()
    name = (body.get("name") or "").strip()
    if not customer_id or not name:
        return jsonify(_err("BAD_REQUEST", "customerId 与 name 必填", "", req_id)), 400
    if not store.customer_get(tenant_id, customer_id):
        return jsonify(_err("BAD_REQUEST", "客户不存在", "", req_id)), 400
    c = store.contact_create(
        tenant_id,
        customer_id,
        name,
        body.get("phone"),
        body.get("email"),
        bool(body.get("isPrimary")),
    )
    store.idempotent_set(req_id, c["contactId"])
    _human_audit(tenant_id, f"创建了联系人 {name} (contactId={c['contactId']})，所属客户 {customer_id}", request.headers.get("X-Trace-Id") or req_id)
    return jsonify(c), 201


# ---------- Opportunities ----------
@app.route("/opportunities", methods=["GET"])
def list_opportunities():
    tenant_id = _tenant()
    customer_id = request.args.get("customerId") or None
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("pageSize", 20))
    data_scope = (request.headers.get("X-Data-Scope") or "").strip()
    owner_id = request.headers.get("X-User-Id") if data_scope == "self" else None
    store = get_store()
    data, total = store.opportunity_list(tenant_id, customer_id=customer_id, page=page, page_size=page_size, owner_id=owner_id)
    return jsonify({"data": data, "total": total}), 200


@app.route("/opportunities", methods=["POST"])
def create_opportunity():
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    if store.idempotent_get(req_id):
        return jsonify(_err("IDEMPOTENT_CONFLICT", "幂等冲突", "", req_id)), 409
    body = request.get_json() or {}
    customer_id = (body.get("customerId") or "").strip()
    title = (body.get("title") or "").strip()
    if not customer_id or not title:
        return jsonify(_err("BAD_REQUEST", "customerId 与 title 必填", "", req_id)), 400
    if not store.customer_get(tenant_id, customer_id):
        return jsonify(_err("BAD_REQUEST", "所选客户不存在，请先创建客户", "", req_id)), 400
    owner_id = request.headers.get("X-User-Id") or None
    o = store.opportunity_create(
        tenant_id,
        customer_id,
        title,
        int(body.get("amountCents") or 0),
        (body.get("currency") or "CNY").strip(),
        int(body.get("stage") or 1),
        owner_id=owner_id,
    )
    store.idempotent_set(req_id, o["opportunityId"])
    _human_audit(tenant_id, f"创建了商机 {title} (opportunityId={o['opportunityId']})，客户 {customer_id}", request.headers.get("X-Trace-Id") or req_id)
    return jsonify(o), 201


@app.route("/opportunities/forecast", methods=["GET"])
def forecast():
    store = get_store()
    summary = store.forecast_summary(_tenant())
    return jsonify(summary), 200


@app.route("/reports/sales-forecast", methods=["GET"])
def sales_forecast():
    """销售预测：按商机阶段汇总加权金额，供报表与看板使用。"""
    store = get_store()
    summary = store.forecast_summary(_tenant())
    return jsonify(summary), 200


@app.route("/opportunities/win-rate", methods=["GET"])
def win_rate():
    period_days = int(request.args.get("periodDays", 90))
    store = get_store()
    analysis = store.win_rate_analysis(_tenant(), period_days)
    return jsonify(analysis), 200


# ---------- Leads ----------
@app.route("/leads", methods=["GET"])
def list_leads():
    tenant_id = _tenant()
    status = request.args.get("status") or None
    assigned_to = request.args.get("assignedTo") or None
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("pageSize", 20))
    store = get_store()
    data, total = store.lead_list(tenant_id, status=status, assigned_to=assigned_to, page=page, page_size=page_size)
    return jsonify({"data": data, "total": total}), 200


@app.route("/leads", methods=["POST"])
def create_lead():
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    if store.idempotent_get(req_id):
        return jsonify(_err("IDEMPOTENT_CONFLICT", "幂等冲突", "", req_id)), 409
    body = request.get_json() or {}
    name = (body.get("name") or "").strip()
    if not name:
        return jsonify(_err("BAD_REQUEST", "name 必填", "", req_id)), 400
    lead = store.lead_create(
        tenant_id,
        name,
        body.get("company"),
        body.get("phone"),
        body.get("email"),
        body.get("source"),
    )
    store.idempotent_set(req_id, lead["leadId"])
    _human_audit(tenant_id, f"创建了线索 {name} (leadId={lead['leadId']})", request.headers.get("X-Trace-Id") or req_id)
    return jsonify(lead), 201


@app.route("/leads/<lead_id>", methods=["GET"])
def get_lead(lead_id: str):
    store = get_store()
    lead = store.lead_get(_tenant(), lead_id)
    if not lead:
        return jsonify(_err("NOT_FOUND", "线索不存在", "", _request_id())), 404
    return jsonify(lead), 200


@app.route("/leads/<lead_id>", methods=["PATCH"])
def assign_lead(lead_id: str):
    body = request.get_json() or {}
    assigned_to = (body.get("assignedTo") or "").strip()
    if not assigned_to:
        return jsonify(_err("BAD_REQUEST", "assignedTo 必填", "", _request_id())), 400
    store = get_store()
    lead = store.lead_assign(_tenant(), lead_id, assigned_to)
    if not lead:
        return jsonify(_err("NOT_FOUND", "线索不存在", "", _request_id())), 404
    return jsonify(lead), 200


@app.route("/leads/<lead_id>/convert", methods=["POST"])
def convert_lead(lead_id: str):
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    if store.idempotent_get(req_id):
        return jsonify(_err("IDEMPOTENT_CONFLICT", "幂等冲突", "", req_id)), 409
    body = request.get_json() or {}
    convert_to = (body.get("convertTo") or "both").strip().lower()
    if convert_to not in ("account", "opportunity", "both"):
        return jsonify(_err("BAD_REQUEST", "convertTo 须为 account|opportunity|both", "", req_id)), 400
    lead, customer_id, opportunity_id = store.lead_convert(
        tenant_id,
        lead_id,
        convert_to,
        body.get("createOpportunityTitle"),
        int(body.get("amountCents") or 0),
    )
    if not lead:
        return jsonify(_err("NOT_FOUND", "线索不存在或已转化", "", req_id)), 404
    store.idempotent_set(req_id, lead_id)
    return (
        jsonify({"leadId": lead_id, "customerId": customer_id or "", "opportunityId": opportunity_id or ""}),
        200,
    )


# ---------- 360 & Relationships ----------
@app.route("/customers/<customer_id>/360", methods=["GET"])
def customer_360(customer_id: str):
    store = get_store()
    c = store.customer_get(_tenant(), customer_id)
    if not c:
        return jsonify(_err("NOT_FOUND", "客户不存在", "", _request_id())), 404
    contacts, _ = store.contact_list(_tenant(), customer_id=customer_id, page=1, page_size=100)
    opps, _ = store.opportunity_list(_tenant(), customer_id=customer_id, page=1, page_size=100)
    _, edges = store.relationship_list(_tenant(), customer_id)
    return (
        jsonify({
            "customer": c,
            "contacts": contacts,
            "opportunities": opps,
            "relationships": edges,
        }),
        200,
    )


@app.route("/customers/<customer_id>/relationships", methods=["GET"])
def customer_relationships(customer_id: str):
    store = get_store()
    if not store.customer_get(_tenant(), customer_id):
        return jsonify(_err("NOT_FOUND", "客户不存在", "", _request_id())), 404
    nodes, edges = store.relationship_list(_tenant(), customer_id)
    return jsonify({"nodes": nodes, "edges": edges}), 200


# ---------- Activities ----------
@app.route("/activities", methods=["GET"])
def list_activities():
    store = get_store()
    tid = _tenant()
    data, total = store.activity_list(
        tid,
        related_opportunity_id=request.args.get("opportunityId") or None,
        related_customer_id=request.args.get("customerId") or None,
        activity_type=request.args.get("activityType") or None,
        status=int(request.args.get("status")) if request.args.get("status") else None,
        due_from=request.args.get("dueFrom") or None,
        due_to=request.args.get("dueTo") or None,
        page=int(request.args.get("page", 1)),
        page_size=int(request.args.get("pageSize", 20)),
    )
    return jsonify({"data": data, "total": total}), 200


@app.route("/activities", methods=["POST"])
def create_activity():
    tid, rid = _tenant(), _request_id()
    store = get_store()
    if store.idempotent_get(rid):
        return jsonify(_err("IDEMPOTENT_CONFLICT", "幂等冲突", "", rid)), 409
    body = request.get_json() or {}
    subject = (body.get("subject") or "").strip()
    if not subject:
        return jsonify(_err("BAD_REQUEST", "subject 必填", "", rid)), 400
    act_type = (body.get("activityType") or "task").strip().lower()
    if act_type not in ("call", "meeting", "task", "email"):
        act_type = "task"
    a = store.activity_create(
        tid, act_type, subject,
        body.get("relatedLeadId"), body.get("relatedOpportunityId"), body.get("relatedCustomerId"),
        body.get("dueAt"),
    )
    store.idempotent_set(rid, a["activityId"])
    return jsonify(a), 201


@app.route("/activities/<activity_id>/complete", methods=["POST"])
def complete_activity(activity_id: str):
    store = get_store()
    a = store.activity_complete(_tenant(), activity_id)
    if not a:
        return jsonify(_err("NOT_FOUND", "活动不存在", "", _request_id())), 404
    return jsonify(a), 200


@app.route("/activities/todo", methods=["GET"])
def activity_todo():
    store = get_store()
    due_before = request.args.get("dueBefore") or None
    data = store.activity_todo_list(_tenant(), due_before)
    return jsonify({"data": data, "total": len(data)}), 200


# ---------- Products ----------
@app.route("/products", methods=["GET"])
def list_products():
    store = get_store()
    data, total = store.product_list(_tenant(), page=int(request.args.get("page", 1)), page_size=int(request.args.get("pageSize", 20)))
    return jsonify({"data": data, "total": total}), 200


@app.route("/products", methods=["POST"])
def create_product():
    tid, rid = _tenant(), _request_id()
    store = get_store()
    if store.idempotent_get(rid):
        return jsonify(_err("IDEMPOTENT_CONFLICT", "幂等冲突", "", rid)), 409
    body = request.get_json() or {}
    code = (body.get("productCode") or "").strip()
    name = (body.get("name") or "").strip()
    if not code or not name:
        return jsonify(_err("BAD_REQUEST", "productCode 与 name 必填", "", rid)), 400
    p = store.product_create(tid, code, name, body.get("unit", "PCS"), int(body.get("standardPriceCents", 0)))
    store.idempotent_set(rid, p["productId"])
    return jsonify(p), 201


@app.route("/opportunities/<opportunity_id>/lines", methods=["GET"])
def list_opportunity_lines(opportunity_id: str):
    store = get_store()
    if not store.opportunity_get(_tenant(), opportunity_id):
        return jsonify(_err("NOT_FOUND", "商机不存在", "", _request_id())), 404
    data = store.opportunity_line_list(_tenant(), opportunity_id)
    return jsonify({"data": data, "total": len(data)}), 200


@app.route("/opportunities/<opportunity_id>/lines", methods=["POST"])
def add_opportunity_line(opportunity_id: str):
    tid, rid = _tenant(), _request_id()
    store = get_store()
    if store.idempotent_get(rid):
        return jsonify(_err("IDEMPOTENT_CONFLICT", "幂等冲突", "", rid)), 409
    body = request.get_json() or {}
    line = store.opportunity_line_add(
        tid, opportunity_id,
        body.get("productId", ""),
        float(body.get("quantity", 1)),
        int(body.get("unitPriceCents", 0)),
    )
    if not line:
        return jsonify(_err("BAD_REQUEST", "商机或产品不存在", "", rid)), 400
    store.idempotent_set(rid, line["lineId"])
    return jsonify(line), 201


@app.route("/opportunities/<opportunity_id>/lines/<line_id>", methods=["DELETE"])
def remove_opportunity_line(opportunity_id: str, line_id: str):
    store = get_store()
    ok = store.opportunity_line_remove(_tenant(), opportunity_id, line_id)
    if not ok:
        return jsonify(_err("NOT_FOUND", "行项目不存在", "", _request_id())), 404
    return jsonify({"ok": True}), 200


# ---------- Pipeline & Reports ----------
@app.route("/pipeline/summary", methods=["GET"])
def pipeline_summary():
    store = get_store()
    return jsonify(store.pipeline_summary(_tenant())), 200


@app.route("/pipeline/funnel", methods=["GET"])
def pipeline_funnel():
    store = get_store()
    return jsonify(store.funnel_data(_tenant())), 200


@app.route("/reports/activity-stats", methods=["GET"])
def reports_activity_stats():
    store = get_store()
    group_by = request.args.get("groupBy", "type")
    data = store.activity_stats(_tenant(), group_by)
    return jsonify({"data": data}), 200


# ---------- Approval ----------
@app.route("/approvals", methods=["GET"])
def list_approvals():
    store = get_store()
    data = store.approval_request_list(
        _tenant(),
        opportunity_id=request.args.get("opportunityId") or None,
        status=request.args.get("status") or None,
        pending_for_user=request.args.get("pendingForUser") or None,
    )
    return jsonify({"data": data, "total": len(data)}), 200


@app.route("/approvals", methods=["POST"])
def create_approval():
    tid, rid = _tenant(), _request_id()
    store = get_store()
    if store.idempotent_get(rid):
        return jsonify(_err("IDEMPOTENT_CONFLICT", "幂等冲突", "", rid)), 409
    body = request.get_json() or {}
    req = store.approval_request_create(
        tid,
        body.get("opportunityId", ""),
        body.get("requestType", "large_deal"),
        body.get("requestedBy", ""),
        body.get("requestedValueCents"),
        body.get("requestedDiscountPct"),
    )
    if not req:
        return jsonify(_err("BAD_REQUEST", "商机不存在", "", rid)), 400
    store.idempotent_set(rid, req["requestId"])
    return jsonify(req), 201


@app.route("/approvals/<request_id>/process", methods=["POST"])
def process_approval(request_id: str):
    body = request.get_json() or {}
    approved = body.get("approved", False)
    processed_by = (body.get("processedBy") or "").strip()
    if not processed_by:
        return jsonify(_err("BAD_REQUEST", "processedBy 必填", "", _request_id())), 400
    store = get_store()
    req = store.approval_process(_tenant(), request_id, approved, processed_by, body.get("comment", ""))
    if not req:
        return jsonify(_err("NOT_FOUND", "审批单不存在或已处理", "", _request_id())), 404
    return jsonify(req), 200


# ---------- Template Merge ----------
@app.route("/templates/merge", methods=["POST"])
def merge_template():
    body = request.get_json() or {}
    template = body.get("template", "")
    context = body.get("context", {})
    if not isinstance(context, dict):
        context = {}
    result = template_merge(template, context)
    return jsonify({"merged": result}), 200


def create_app() -> Flask:
    return app


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", "8001"))
    app.run(host="0.0.0.0", port=port)
