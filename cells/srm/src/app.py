"""
SRM 细胞 Flask 应用 - 供应商与采购订单，01 合规（验签、人性化审计、敏感数据脱敏）。
《敏感数据加密与脱敏规范》：供应商 contact 可能含电话，列表/详情返回时脱敏。
"""
from __future__ import annotations
import os
import re
import time
import uuid
from datetime import datetime, timezone
import csv
import io
from flask import Flask, request, jsonify, Response
from .store import get_store

def _human_audit(tenant_id: str, operation_desc: str, trace_id: str = "") -> None:
    user_id = request.headers.get("X-User-Id") or request.headers.get("X-Tenant-Id") or "system"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    trace_id = trace_id or request.headers.get("X-Trace-Id") or request.headers.get("X-Request-ID") or ""
    import logging
    logging.getLogger("srm.audit").info(f"【人性化审计】租户 {tenant_id} 用户 {user_id} 在 {ts} {operation_desc}，trace_id={trace_id}")

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

def _tenant() -> str:
    return (request.headers.get("X-Tenant-Id") or "").strip() or "default"

def _mask_contact(s: str | None) -> str:
    """联系人/电话脱敏：13800138000 -> 138****8000。"""
    if not s or not isinstance(s, str):
        return ""
    digits = re.sub(r"\D", "", s)
    if len(digits) < 7:
        return "***"
    return digits[:3] + "****" + digits[-4:]

def _supplier_masking(row: dict) -> dict:
    """供应商返回体脱敏：contact 字段。"""
    out = dict(row)
    if out.get("contact"):
        out["contact"] = _mask_contact(out["contact"])
    return out

def _request_id() -> str:
    return (request.headers.get("X-Request-ID") or "").strip() or str(uuid.uuid4())

def _user_id() -> str:
    return (request.headers.get("X-User-Id") or request.headers.get("X-Tenant-Id") or "system").strip() or "system"

@app.before_request
def _verify_gateway_signature():
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
        return jsonify({"code": "SIGNATURE_INVALID", "message": "验签失败", "details": "", "requestId": headers.get("X-Request-ID", "")}), 403

@app.before_request
def _start_timer():
    request._start_time = time.time()

@app.after_request
def _response_time(resp):
    if "X-Response-Time" not in resp.headers:
        elapsed = time.time() - getattr(request, "_start_time", time.time())
        resp.headers["X-Response-Time"] = f"{elapsed:.3f}"
    return resp

@app.route("/health")
def health():
    return jsonify({"status": "up", "cell": "srm"}), 200

@app.route("/suppliers", methods=["GET"])
def list_suppliers():
    tenant_id = _tenant()
    data = get_store().supplier_list(tenant_id)
    data = [_supplier_masking(d) for d in data]
    _human_audit(tenant_id, "查询供应商列表")
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/suppliers", methods=["POST"])
def create_supplier():
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    if store.idem_get(req_id):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "details": "", "requestId": req_id}), 409
    body = request.get_json() or {}
    name = (body.get("name") or "").strip()
    if not name:
        return jsonify({"code": "BAD_REQUEST", "message": "name 必填", "details": "请填写供应商名称", "requestId": req_id}), 400
    s = store.supplier_create(tenant_id, name, body.get("code", ""), body.get("contact", ""))
    store.idem_set(req_id, s["supplierId"])
    store.audit_append(tenant_id, _user_id(), "supplier.create", "supplier", s["supplierId"], req_id)
    _human_audit(tenant_id, f"创建供应商 {s['supplierId']}", req_id)
    return jsonify(s), 201

@app.route("/purchase-orders", methods=["GET"])
def list_purchase_orders():
    tenant_id = _tenant()
    data = get_store().purchase_order_list(tenant_id)
    _human_audit(tenant_id, "查询采购订单列表")
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/purchase-orders", methods=["POST"])
def create_purchase_order():
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    if store.idem_get(req_id):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "details": "", "requestId": req_id}), 409
    body = request.get_json() or {}
    o = store.purchase_order_create(tenant_id, body.get("supplierId", ""), body.get("orderNo", ""), int(body.get("amountCents", 0)))
    store.idem_set(req_id, o["orderId"])
    _human_audit(tenant_id, f"创建采购订单 {o['orderId']}", req_id)
    return jsonify(o), 201

@app.route("/suppliers/<supplier_id>", methods=["GET"])
def get_supplier(supplier_id: str):
    s = get_store().supplier_get(_tenant(), supplier_id)
    if not s:
        return jsonify({"code": "NOT_FOUND", "message": "供应商不存在", "details": "请检查供应商编号或刷新列表后重试", "requestId": _request_id()}), 404
    _human_audit(_tenant(), f"查询供应商 {supplier_id}")
    return jsonify(_supplier_masking(s)), 200

@app.route("/purchase-orders/<order_id>", methods=["GET"])
def get_purchase_order(order_id: str):
    o = get_store().purchase_order_get(_tenant(), order_id)
    if not o:
        return jsonify({"code": "NOT_FOUND", "message": "采购订单不存在", "requestId": _request_id()}), 404
    _human_audit(_tenant(), f"查询采购订单 {order_id}")
    return jsonify(o), 200

@app.route("/purchase-orders/<order_id>", methods=["PATCH"])
def update_purchase_order(order_id: str):
    body = request.get_json() or {}
    status = body.get("status")
    if status is None:
        return jsonify({"code": "BAD_REQUEST", "message": "status 必填", "details": "请传递 status 字段", "requestId": _request_id()}), 400
    o = get_store().purchase_order_update_status(_tenant(), order_id, int(status))
    if not o:
        return jsonify({"code": "NOT_FOUND", "message": "采购订单不存在", "details": "请检查 orderId", "requestId": _request_id()}), 404
    _human_audit(_tenant(), f"更新采购订单 {order_id} 状态为 {status}")
    return jsonify(o), 200

# ---------- 询价 RFQ ----------
@app.route("/rfqs", methods=["GET"])
def list_rfqs():
    tenant_id = _tenant()
    page = max(1, int(request.args.get("page", 1)))
    page_size = max(1, min(100, int(request.args.get("pageSize", 20))))
    data, total = get_store().rfq_list(tenant_id, page=page, page_size=page_size)
    _human_audit(tenant_id, "查询询价单列表")
    return jsonify({"data": data, "total": total, "page": page, "pageSize": page_size}), 200

@app.route("/rfqs", methods=["POST"])
def create_rfq():
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    if store.idem_get(req_id):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "requestId": req_id}), 409
    body = request.get_json() or {}
    r = store.rfq_create(tenant_id, body.get("demandId", ""))
    store.idem_set(req_id, r["rfqId"])
    _human_audit(tenant_id, f"创建询价单 {r['rfqId']}", req_id)
    return jsonify(r), 201

# ---------- 报价 Quote（幂等） ----------
@app.route("/quotes", methods=["GET"])
def list_quotes():
    tenant_id = _tenant()
    rfq_id = request.args.get("rfqId")
    page = max(1, int(request.args.get("page", 1)))
    page_size = max(1, min(100, int(request.args.get("pageSize", 20))))
    data, total = get_store().quote_list(tenant_id, rfq_id=rfq_id, page=page, page_size=page_size)
    _human_audit(tenant_id, "查询报价列表")
    return jsonify({"data": data, "total": total, "page": page, "pageSize": page_size}), 200

@app.route("/quotes", methods=["POST"])
def create_quote():
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    if store.idem_get(req_id):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "requestId": req_id}), 409
    body = request.get_json() or {}
    rfq_id = (body.get("rfqId") or "").strip()
    supplier_id = (body.get("supplierId") or "").strip()
    if not rfq_id or not supplier_id:
        return jsonify({"code": "BAD_REQUEST", "message": "rfqId 与 supplierId 必填", "details": "请填写必填字段", "requestId": req_id}), 400
    if not store.rfq_get(tenant_id, rfq_id):
        return jsonify({"code": "BUSINESS_RULE_VIOLATION", "message": "询价单不存在", "details": "请先创建询价单", "requestId": req_id}), 400
    q = store.quote_create(tenant_id, rfq_id, supplier_id, int(body.get("amountCents", 0)), body.get("currency", "CNY"), body.get("validUntil", ""))
    store.idem_set(req_id, q["quoteId"])
    _human_audit(tenant_id, f"提交报价 {q['quoteId']}", req_id)
    return jsonify(q), 201


@app.route("/quotes/<quote_id>/award", methods=["POST"])
def award_quote(quote_id: str):
    """报价中标：标记该报价为中标并发布 srm.quote.awarded，供联动 Worker 回传 ERP 生成采购订单。"""
    tenant_id = _tenant()
    q = get_store().quote_award(tenant_id, quote_id)
    if not q:
        return jsonify({"code": "NOT_FOUND", "message": "报价不存在", "details": "请检查报价编号", "requestId": _request_id()}), 404
    try:
        from . import event_publisher as _ev
        _ev.publish(
            "srm.quote.awarded",
            {"quoteId": quote_id, "tenantId": tenant_id, "rfqId": q.get("rfqId", ""), "supplierId": q.get("supplierId", ""), "amountCents": q.get("amountCents", 0), "currency": q.get("currency", "CNY")},
            trace_id=_request_id(),
        )
    except Exception:
        pass
    _human_audit(tenant_id, f"报价中标 {quote_id}", _request_id())
    return jsonify(q), 200


# ---------- 供应商评估 ----------
@app.route("/evaluations", methods=["GET"])
def list_evaluations():
    tenant_id = _tenant()
    supplier_id = request.args.get("supplierId")
    page = max(1, int(request.args.get("page", 1)))
    page_size = max(1, min(100, int(request.args.get("pageSize", 20))))
    data, total = get_store().evaluation_list(tenant_id, supplier_id=supplier_id, page=page, page_size=page_size)
    _human_audit(tenant_id, "查询供应商评估列表")
    return jsonify({"data": data, "total": total, "page": page, "pageSize": page_size}), 200

@app.route("/evaluations", methods=["POST"])
def create_evaluation():
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    if store.idem_get(req_id):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "requestId": req_id}), 409
    body = request.get_json() or {}
    supplier_id = (body.get("supplierId") or "").strip()
    score = int(body.get("score", 0))
    if not supplier_id:
        return jsonify({"code": "BAD_REQUEST", "message": "supplierId 必填", "details": "请填写供应商ID", "requestId": req_id}), 400
    if not store.supplier_get(tenant_id, supplier_id):
        return jsonify({"code": "BUSINESS_RULE_VIOLATION", "message": "供应商不存在", "details": "请先完成供应商准入", "requestId": req_id}), 400
    e = store.evaluation_create(tenant_id, supplier_id, score, body.get("dimension", ""), body.get("comment", ""))
    store.idem_set(req_id, e["evaluationId"])
    _human_audit(tenant_id, f"创建供应商评估 {e['evaluationId']}", req_id)
    return jsonify(e), 201


# ---------- 供应商招投标（项目） ----------
@app.route("/bidding/projects", methods=["GET"])
def list_bidding_projects():
    tenant_id = _tenant()
    status = request.args.get("status")
    page = max(1, int(request.args.get("page", 1)))
    page_size = max(1, min(100, int(request.args.get("pageSize", 20))))
    data, total = get_store().bidding_project_list(tenant_id, status=status, page=page, page_size=page_size)
    _human_audit(tenant_id, "查询招投标项目列表")
    return jsonify({"data": data, "total": total, "page": page, "pageSize": page_size}), 200


@app.route("/bidding/projects", methods=["POST"])
def create_bidding_project():
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    if store.idem_get(req_id):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "请勿重复提交", "details": "同一请求已创建过招投标项目", "requestId": req_id}), 409
    body = request.get_json() or {}
    title = (body.get("title") or "").strip()
    if not title:
        return jsonify({"code": "BAD_REQUEST", "message": "请填写项目名称", "details": "招投标项目标题不能为空", "requestId": req_id}), 400
    p = store.bidding_project_create(tenant_id, title, body.get("description", ""), body.get("rfqIds"))
    store.idem_set(req_id, p["projectId"])
    _human_audit(tenant_id, f"创建招投标项目 {p['projectId']}", req_id)
    return jsonify(p), 201


@app.route("/bidding/projects/<project_id>", methods=["GET"])
def get_bidding_project(project_id: str):
    p = get_store().bidding_project_get(_tenant(), project_id)
    if not p:
        return jsonify({"code": "NOT_FOUND", "message": "招投标项目不存在", "details": "请检查项目编号或联系管理员", "requestId": _request_id()}), 404
    _human_audit(_tenant(), f"查询招投标项目 {project_id}")
    return jsonify(p), 200


@app.route("/bidding/projects/<project_id>", methods=["PATCH"])
def update_bidding_project_status(project_id: str):
    body = request.get_json() or {}
    status = (body.get("status") or "").strip()
    if status not in ("open", "closed", "awarded"):
        return jsonify({"code": "BAD_REQUEST", "message": "状态值无效", "details": "仅支持 open（进行中）、closed（已关闭）、awarded（已中标）", "requestId": _request_id()}), 400
    p = get_store().bidding_project_update_status(_tenant(), project_id, status)
    if not p:
        return jsonify({"code": "NOT_FOUND", "message": "招投标项目不存在", "details": "请检查项目编号", "requestId": _request_id()}), 404
    _human_audit(_tenant(), f"更新招投标项目 {project_id} 状态为 {status}")
    return jsonify(p), 200


@app.route("/audit-logs", methods=["GET"])
def list_audit_logs():
    tenant_id = _tenant()
    page = max(1, int(request.args.get("page", 1)))
    page_size = max(1, min(200, int(request.args.get("pageSize", 50))))
    resource_type = (request.args.get("resourceType") or "").strip() or None
    data, total = get_store().audit_list(tenant_id, page=page, page_size=page_size, resource_type=resource_type)
    return jsonify({"data": data, "total": total, "page": page, "pageSize": page_size}), 200


@app.route("/suppliers/import", methods=["POST"])
def import_suppliers():
    """批量导入供应商。body.items 每项 {name, code?, contact?}；单次建议不超过 1000 条。"""
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    body = request.get_json() or {}
    items = body.get("items") or body.get("data") or []
    if not items or not isinstance(items, list):
        return jsonify({"code": "BAD_REQUEST", "message": "请提供 items 数组", "details": "请求体需包含 items 或 data 字段", "requestId": req_id}), 400
    if len(items) > 2000:
        return jsonify({"code": "BAD_REQUEST", "message": "单次导入不超过 2000 条", "details": "请分批导入以保证系统稳定", "requestId": req_id}), 400
    created, errors = [], []
    for i, row in enumerate(items):
        name = (row.get("name") or "").strip()
        if not name:
            errors.append({"index": i, "reason": "供应商名称为空"})
            continue
        try:
            s = store.supplier_create(tenant_id, name, row.get("code", ""), row.get("contact", ""))
            created.append({"index": i, "supplierId": s["supplierId"], "name": name})
        except Exception as e:
            errors.append({"index": i, "reason": str(e), "name": name})
    _human_audit(tenant_id, f"批量导入供应商，成功 {len(created)} 条，失败 {len(errors)} 条", req_id)
    return jsonify({"accepted": True, "created": len(created), "errors": len(errors), "details": created, "errorsDetail": errors}), 202


# ---------- 核心单据导出（Excel/CSV、打印用） ----------
@app.route("/export/purchase-orders", methods=["GET"])
def export_purchase_orders():
    """采购订单标准化导出：format=csv 返回 CSV（Excel 可打开）。"""
    tenant_id = _tenant()
    fmt = (request.args.get("format") or "csv").lower()
    data = get_store().purchase_order_list(tenant_id)
    _human_audit(tenant_id, "导出采购订单")
    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["订单编号", "供应商ID", "金额(分)", "状态", "创建时间"])
        for o in data:
            writer.writerow([
                o.get("orderNo", ""),
                o.get("supplierId", ""),
                o.get("amountCents", 0),
                o.get("status", ""),
                o.get("createdAt", ""),
            ])
        return Response(buf.getvalue(), mimetype="text/csv; charset=utf-8-sig", headers={"Content-Disposition": "attachment; filename=purchase_orders.csv"})
    return jsonify({"data": data, "total": len(data)}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8008))
    app.run(host="0.0.0.0", port=port, debug=False)
