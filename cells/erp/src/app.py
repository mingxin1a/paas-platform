"""
ERP 细胞 Flask 应用 - GL、AR/AP、MM、PP。遵循《接口设计说明书》必须头、幂等、金额-分。
01 5.2/00 #5 验签；01 4.4 人性化审计。企业级优化：统一错误体、必填/业务校验、审计落库、分页、软删除。
"""
from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from .store import get_store
from . import validators

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

def _tenant() -> str:
    return (request.headers.get("X-Tenant-Id") or "").strip() or "default"
def _req_id() -> str:
    return (request.headers.get("X-Request-ID") or "").strip() or str(uuid.uuid4())

def _user_id() -> str:
    return (request.headers.get("X-User-Id") or request.headers.get("X-Tenant-Id") or "system").strip() or "system"

def _trace_id() -> str:
    return (request.headers.get("X-Trace-Id") or request.headers.get("X-Request-ID") or _req_id()).strip() or ""

def _err(code: str, message: str, status: int = 400, details: str | None = None):
    """统一错误响应体：《接口设计说明书》3.1.3 四字段必备 code, message, details, requestId。"""
    body = {"code": code, "message": message, "details": details if details else "", "requestId": _req_id()}
    return jsonify(body), status

def _human_audit(tenant_id: str, operation_desc: str, trace_id: str = "") -> None:
    """01 4.4 人性化日志：谁在何时对何资源做了何操作，与 trace_id 关联。"""
    import logging
    user_id = request.headers.get("X-User-Id") or request.headers.get("X-Tenant-Id") or "system"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    trace_id = trace_id or request.headers.get("X-Trace-Id") or request.headers.get("X-Request-ID") or ""
    logging.getLogger("erp.audit").info(f"【人性化审计】租户 {tenant_id} 用户 {user_id} 在 {ts} {operation_desc}，trace_id={trace_id}")


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
    headers = {"X-Signature": request.headers.get("X-Signature") or "", "X-Signature-Time": request.headers.get("X-Signature-Time") or "", "X-Request-ID": request.headers.get("X-Request-ID") or "", "X-Tenant-Id": request.headers.get("X-Tenant-Id") or "", "X-Trace-Id": request.headers.get("X-Trace-Id") or ""}
    ok, reason = verify_signature(request.method, request.path, body, headers)
    if not ok:
        trace_id = request.headers.get("X-Trace-Id") or request.headers.get("X-Request-ID") or ""
        write_security_audit("signature_verify_failed", reason, path=request.path, trace_id=trace_id)
        return _err("SIGNATURE_INVALID", "验签失败", 403, "黑客入侵/验签失败")


@app.before_request
def _start():
    request._start_time = time.time()
@app.after_request
def _resp_time(r):
    if "X-Response-Time" not in r.headers:
        r.headers["X-Response-Time"] = f"{time.time() - getattr(request, '_start_time', 0):.3f}"
    return r

@app.route("/health")
def health():
    return jsonify({"status": "up", "cell": "erp"}), 200

def _audit(tenant_id: str, op: str, result: int, resource_type: str = "", resource_id: str = ""):
    get_store().audit_append(tenant_id, _user_id(), op, result, _trace_id(), resource_type, resource_id)

@app.route("/orders", methods=["GET"])
def orders_list():
    page = max(1, int(request.args.get("page", 1)))
    page_size = max(1, min(100, int(request.args.get("pageSize", 20))))
    data, total = get_store().order_list(_tenant(), page, page_size)
    return jsonify({"data": data, "total": total, "page": page, "pageSize": page_size}), 200
@app.route("/orders/<order_id>", methods=["GET"])
def order_get(order_id: str):
    o = get_store().order_get(_tenant(), order_id)
    if not o:
        return _err("NOT_FOUND", "订单不存在", 404)
    return jsonify(o), 200
@app.route("/orders/<order_id>", methods=["PATCH"])
def order_patch(order_id: str):
    """联动回写：审批完成后更新订单状态。body { "orderStatus": 1|2|3 }。"""
    tid = _tenant()
    b = request.get_json() or {}
    status = b.get("orderStatus")
    if status is None:
        return _err("BAD_REQUEST", "orderStatus 必填", 400)
    o = get_store().order_update_status(tid, order_id, int(status))
    if not o:
        return _err("NOT_FOUND", "订单不存在", 404)
    return jsonify(o), 200

@app.route("/orders/<order_id>", methods=["DELETE"])
def order_delete(order_id: str):
    tid = _tenant()
    if not get_store().order_soft_delete(tid, order_id):
        return _err("NOT_FOUND", "订单不存在或已删除", 404)
    _human_audit(tid, f"软删除订单 {order_id}", _trace_id())
    _audit(tid, "order.delete", 1, "order", order_id)
    return jsonify({"deleted": True, "orderId": order_id}), 200
@app.route("/orders", methods=["POST"])
def orders_create():
    tid, rid = _tenant(), _req_id()
    s = get_store()
    if s.idem_get(rid):
        return _err("IDEMPOTENT_CONFLICT", "幂等冲突", 409)
    b = request.get_json() or {}
    err_msg = validators.validate_required(b, "orders_create")
    if err_msg:
        return _err("VALIDATION_ERROR", "请求参数校验失败", 400, err_msg)
    order_lines = b.get("orderLines") or b.get("items")
    o = s.order_create(tid, b.get("customerId", ""), int(b.get("totalAmountCents", 0)), b.get("currency", "CNY"), order_lines=order_lines)
    s.idem_set(rid, o["orderId"])
    _human_audit(tid, f"创建了销售订单 (orderId={o['orderId']})，客户 {b.get('customerId', '')}", _trace_id())
    _audit(tid, "order.create", 1, "order", o["orderId"])
    try:
        from . import event_publisher as _ev
        payload = {"orderId": o["orderId"], "tenantId": tid, "customerId": o.get("customerId", ""), "totalAmountCents": o.get("totalAmountCents", 0), "currency": o.get("currency", "CNY")}
        if o.get("orderLines"):
            payload["orderLines"] = o["orderLines"]
        _ev.publish("erp.order.created", payload, trace_id=_trace_id())
    except Exception:
        pass
    return jsonify(o), 201

@app.route("/gl/accounts", methods=["GET"])
def gl_accounts():
    page = max(1, int(request.args.get("page", 1)))
    page_size = max(1, min(100, int(request.args.get("pageSize", 20))))
    data, total = get_store().gl_account_list(_tenant(), page, page_size)
    return jsonify({"data": data, "total": total, "page": page, "pageSize": page_size}), 200
@app.route("/gl/accounts/<account_code>", methods=["GET"])
def gl_account_get(account_code: str):
    a = get_store().gl_account_get(_tenant(), account_code)
    if not a:
        return _err("NOT_FOUND", "科目不存在", 404)
    return jsonify(a), 200
@app.route("/gl/accounts/<account_code>", methods=["DELETE"])
def gl_account_delete(account_code: str):
    tid = _tenant()
    if not get_store().gl_account_soft_delete(tid, account_code):
        return _err("NOT_FOUND", "科目不存在或已删除", 404)
    _human_audit(tid, f"软删除科目 {account_code}", _trace_id())
    _audit(tid, "gl_account.delete", 1, "gl_account", account_code)
    return jsonify({"deleted": True, "accountCode": account_code}), 200
@app.route("/gl/accounts", methods=["POST"])
def gl_accounts_create():
    tid, rid = _tenant(), _req_id()
    s = get_store()
    if s.idem_get(rid):
        return _err("IDEMPOTENT_CONFLICT", "幂等冲突", 409)
    b = request.get_json() or {}
    err_msg = validators.validate_required(b, "gl_accounts_create")
    if err_msg:
        return _err("VALIDATION_ERROR", "请求参数校验失败", 400, err_msg)
    a = s.gl_account_create(tid, b.get("accountCode", ""), b.get("name", ""), int(b.get("accountType", 1)))
    s.idem_set(rid, a["accountCode"])
    _human_audit(tid, f"创建了总账科目 {b.get('accountCode', '')} ({b.get('name', '')})", _trace_id())
    _audit(tid, "gl_account.create", 1, "gl_account", a["accountCode"])
    return jsonify(a), 201
@app.route("/gl/journal-entries", methods=["GET"])
def gl_entries():
    page = max(1, int(request.args.get("page", 1)))
    page_size = max(1, min(100, int(request.args.get("pageSize", 20))))
    data, total = get_store().gl_entry_list_filtered(
        _tenant(), request.args.get("dateFrom"), request.args.get("dateTo"), page, page_size
    )
    return jsonify({"data": data, "total": total, "page": page, "pageSize": page_size}), 200
@app.route("/gl/journal-entries/<entry_id>", methods=["GET"])
def gl_entry_get(entry_id: str):
    e = get_store().gl_entry_get(_tenant(), entry_id)
    if not e:
        return _err("NOT_FOUND", "分录不存在", 404)
    return jsonify(e), 200
@app.route("/gl/journal-entries", methods=["POST"])
def gl_entries_create():
    tid, rid = _tenant(), _req_id()
    s = get_store()
    if s.idem_get(rid):
        return _err("IDEMPOTENT_CONFLICT", "幂等冲突", 409)
    b = request.get_json() or {}
    err_msg = validators.validate_required(b, "gl_entries_create")
    if err_msg:
        return _err("VALIDATION_ERROR", "请求参数校验失败", 400, err_msg)
    lines = b.get("lines", [])
    err_msg = validators.validate_gl_entry_lines(lines)
    if err_msg:
        return _err("BUSINESS_RULE_VIOLATION", "业务规则校验失败", 400, err_msg)
    e = s.gl_entry_create(tid, b.get("documentNo", ""), b.get("postingDate", ""), lines)
    s.idem_set(rid, e["entryId"])
    _human_audit(tid, f"创建了分录 (entryId={e['entryId']})，凭证号 {b.get('documentNo', '')}", _trace_id())
    _audit(tid, "gl_entry.create", 1, "gl_entry", e["entryId"])
    return jsonify(e), 201

@app.route("/ar/invoices", methods=["GET"])
def ar_list():
    page = max(1, int(request.args.get("page", 1)))
    page_size = max(1, min(100, int(request.args.get("pageSize", 20))))
    data, total = get_store().ar_list(_tenant(), page, page_size)
    return jsonify({"data": data, "total": total, "page": page, "pageSize": page_size}), 200
@app.route("/ar/invoices/<invoice_id>", methods=["GET"])
def ar_get(invoice_id: str):
    inv = get_store().ar_get(_tenant(), invoice_id)
    if not inv:
        return _err("NOT_FOUND", "应收发票不存在", 404)
    return jsonify(inv), 200
@app.route("/ar/invoices/<invoice_id>", methods=["DELETE"])
def ar_delete(invoice_id: str):
    tid = _tenant()
    if not get_store().ar_soft_delete(tid, invoice_id):
        return _err("NOT_FOUND", "应收发票不存在或已删除", 404)
    _human_audit(tid, f"软删除应收发票 {invoice_id}", _trace_id())
    _audit(tid, "ar_invoice.delete", 1, "ar_invoice", invoice_id)
    return jsonify({"deleted": True, "invoiceId": invoice_id}), 200
@app.route("/ar/invoices", methods=["POST"])
def ar_create():
    tid, rid = _tenant(), _req_id()
    s = get_store()
    if s.idem_get(rid):
        return _err("IDEMPOTENT_CONFLICT", "幂等冲突", 409)
    b = request.get_json() or {}
    err_msg = validators.validate_required(b, "ar_create")
    if err_msg:
        return _err("VALIDATION_ERROR", "请求参数校验失败", 400, err_msg)
    inv = s.ar_create(tid, b.get("customerId", ""), b.get("documentNo", ""), int(b.get("amountCents", 0)), b.get("currency", "CNY"), b.get("dueDate"))
    s.idem_set(rid, inv["invoiceId"])
    _human_audit(tid, f"创建了应收发票 (invoiceId={inv['invoiceId']})，客户 {b.get('customerId', '')}", _trace_id())
    _audit(tid, "ar_invoice.create", 1, "ar_invoice", inv["invoiceId"])
    return jsonify(inv), 201
@app.route("/ap/invoices", methods=["GET"])
def ap_list():
    page = max(1, int(request.args.get("page", 1)))
    page_size = max(1, min(100, int(request.args.get("pageSize", 20))))
    data, total = get_store().ap_list(_tenant(), page, page_size)
    return jsonify({"data": data, "total": total, "page": page, "pageSize": page_size}), 200
@app.route("/ap/invoices/<invoice_id>", methods=["GET"])
def ap_get(invoice_id: str):
    inv = get_store().ap_get(_tenant(), invoice_id)
    if not inv:
        return _err("NOT_FOUND", "应付发票不存在", 404)
    return jsonify(inv), 200
@app.route("/ap/invoices/<invoice_id>", methods=["DELETE"])
def ap_delete(invoice_id: str):
    tid = _tenant()
    if not get_store().ap_soft_delete(tid, invoice_id):
        return _err("NOT_FOUND", "应付发票不存在或已删除", 404)
    _human_audit(tid, f"软删除应付发票 {invoice_id}", _trace_id())
    _audit(tid, "ap_invoice.delete", 1, "ap_invoice", invoice_id)
    return jsonify({"deleted": True, "invoiceId": invoice_id}), 200
@app.route("/ap/invoices", methods=["POST"])
def ap_create():
    tid, rid = _tenant(), _req_id()
    s = get_store()
    if s.idem_get(rid):
        return _err("IDEMPOTENT_CONFLICT", "幂等冲突", 409)
    b = request.get_json() or {}
    err_msg = validators.validate_required(b, "ap_create")
    if err_msg:
        return _err("VALIDATION_ERROR", "请求参数校验失败", 400, err_msg)
    inv = s.ap_create(tid, b.get("supplierId", ""), b.get("documentNo", ""), int(b.get("amountCents", 0)), b.get("currency", "CNY"), b.get("dueDate"))
    s.idem_set(rid, inv["invoiceId"])
    _human_audit(tid, f"创建了应付发票 (invoiceId={inv['invoiceId']})，供应商 {b.get('supplierId', '')}", _trace_id())
    _audit(tid, "ap_invoice.create", 1, "ap_invoice", inv["invoiceId"])
    return jsonify(inv), 201

@app.route("/mm/materials", methods=["GET"])
def mm_materials():
    page = max(1, int(request.args.get("page", 1)))
    page_size = max(1, min(100, int(request.args.get("pageSize", 20))))
    data, total = get_store().material_list(_tenant(), page, page_size)
    return jsonify({"data": data, "total": total, "page": page, "pageSize": page_size}), 200
@app.route("/mm/materials/<material_id>", methods=["GET"])
def mm_material_get(material_id: str):
    m = get_store().material_get(_tenant(), material_id)
    if not m:
        return _err("NOT_FOUND", "物料不存在", 404)
    return jsonify(m), 200
@app.route("/mm/materials/<material_id>", methods=["DELETE"])
def mm_material_delete(material_id: str):
    tid = _tenant()
    if not get_store().material_soft_delete(tid, material_id):
        return _err("NOT_FOUND", "物料不存在或已删除", 404)
    _human_audit(tid, f"软删除物料 {material_id}", _trace_id())
    _audit(tid, "material.delete", 1, "material", material_id)
    return jsonify({"deleted": True, "materialId": material_id}), 200
@app.route("/mm/materials", methods=["POST"])
def mm_materials_create():
    tid, rid = _tenant(), _req_id()
    s = get_store()
    if s.idem_get(rid):
        return _err("IDEMPOTENT_CONFLICT", "幂等冲突", 409)
    b = request.get_json() or {}
    err_msg = validators.validate_required(b, "mm_materials_create")
    if err_msg:
        return _err("VALIDATION_ERROR", "请求参数校验失败", 400, err_msg)
    m = s.material_create(tid, b.get("materialCode", ""), b.get("name", ""), b.get("unit", "PCS"))
    s.idem_set(rid, m["materialId"])
    _human_audit(tid, f"创建了物料 {b.get('materialCode', '')} ({b.get('name', '')})", _trace_id())
    _audit(tid, "material.create", 1, "material", m["materialId"])
    return jsonify(m), 201
@app.route("/mm/purchase-requisitions", methods=["POST"])
def mm_requisition_create():
    """采购申请：创建后发布 erp.purchase_requisition.created，供联动 Worker 同步至 SRM 生成询报价单。"""
    tid, rid = _tenant(), _req_id()
    s = get_store()
    if s.idem_get(rid):
        return _err("IDEMPOTENT_CONFLICT", "幂等冲突", 409)
    b = request.get_json() or {}
    req = s.requisition_create(tid, b.get("demandDesc", ""), int(b.get("totalAmountCents", 0)))
    s.idem_set(rid, req["requisitionId"])
    _human_audit(tid, f"创建了采购申请 {req['requisitionId']}", _trace_id())
    _audit(tid, "requisition.create", 1, "requisition", req["requisitionId"])
    try:
        from . import event_publisher as _ev
        _ev.publish("erp.purchase_requisition.created", {"requisitionId": req["requisitionId"], "tenantId": tid, "demandDesc": req.get("demandDesc", ""), "totalAmountCents": req.get("totalAmountCents", 0)}, trace_id=_trace_id())
    except Exception:
        pass
    return jsonify(req), 201

@app.route("/mm/purchase-orders", methods=["GET"])
def mm_po_list():
    page = max(1, int(request.args.get("page", 1)))
    page_size = max(1, min(100, int(request.args.get("pageSize", 20))))
    data, total = get_store().po_list(_tenant(), page, page_size)
    return jsonify({"data": data, "total": total, "page": page, "pageSize": page_size}), 200
@app.route("/mm/purchase-orders/<po_id>", methods=["GET"])
def mm_po_get(po_id: str):
    po = get_store().po_get(_tenant(), po_id)
    if not po:
        return _err("NOT_FOUND", "采购订单不存在", 404)
    return jsonify(po), 200
@app.route("/mm/purchase-orders/<po_id>", methods=["PATCH"])
def mm_po_patch(po_id: str):
    """联动回写：审批完成后更新采购订单状态。body { "status": 1|2 }。"""
    tid = _tenant()
    b = request.get_json() or {}
    status = b.get("status")
    if status is None:
        return _err("BAD_REQUEST", "status 必填", 400)
    po = get_store().po_update_status(tid, po_id, int(status))
    if not po:
        return _err("NOT_FOUND", "采购订单不存在", 404)
    return jsonify(po), 200

@app.route("/mm/purchase-orders/<po_id>", methods=["DELETE"])
def mm_po_delete(po_id: str):
    tid = _tenant()
    if not get_store().po_soft_delete(tid, po_id):
        return _err("NOT_FOUND", "采购订单不存在或已删除", 404)
    _human_audit(tid, f"软删除采购订单 {po_id}", _trace_id())
    _audit(tid, "purchase_order.delete", 1, "purchase_order", po_id)
    return jsonify({"deleted": True, "poId": po_id}), 200
@app.route("/mm/purchase-orders", methods=["POST"])
def mm_po_create():
    tid, rid = _tenant(), _req_id()
    s = get_store()
    if s.idem_get(rid):
        return _err("IDEMPOTENT_CONFLICT", "幂等冲突", 409)
    b = request.get_json() or {}
    err_msg = validators.validate_required(b, "mm_po_create")
    if err_msg:
        return _err("VALIDATION_ERROR", "请求参数校验失败", 400, err_msg)
    po = s.po_create(tid, b.get("supplierId", ""), b.get("documentNo", ""), int(b.get("totalAmountCents", 0)))
    s.idem_set(rid, po["poId"])
    _human_audit(tid, f"创建了采购订单 (poId={po['poId']})，凭证号 {b.get('documentNo', '')}", _trace_id())
    _audit(tid, "purchase_order.create", 1, "purchase_order", po["poId"])
    try:
        from . import event_publisher as _ev
        _ev.publish("erp.purchase_order.created", {"poId": po["poId"], "tenantId": tid, "supplierId": po.get("supplierId", ""), "documentNo": po.get("documentNo", ""), "totalAmountCents": po.get("totalAmountCents", 0)}, trace_id=_trace_id())
    except Exception:
        pass
    return jsonify(po), 201

@app.route("/pp/boms", methods=["GET"])
def pp_boms():
    page = max(1, int(request.args.get("page", 1)))
    page_size = max(1, min(100, int(request.args.get("pageSize", 20))))
    data, total = get_store().bom_list(_tenant(), page, page_size)
    return jsonify({"data": data, "total": total, "page": page, "pageSize": page_size}), 200
@app.route("/pp/boms/<bom_id>", methods=["GET"])
def pp_bom_get(bom_id: str):
    b = get_store().bom_get(_tenant(), bom_id)
    if not b:
        return _err("NOT_FOUND", "BOM不存在", 404)
    return jsonify(b), 200
@app.route("/pp/boms/<bom_id>", methods=["DELETE"])
def pp_bom_delete(bom_id: str):
    tid = _tenant()
    if not get_store().bom_soft_delete(tid, bom_id):
        return _err("NOT_FOUND", "BOM不存在或已删除", 404)
    _human_audit(tid, f"软删除BOM {bom_id}", _trace_id())
    _audit(tid, "bom.delete", 1, "bom", bom_id)
    return jsonify({"deleted": True, "bomId": bom_id}), 200
@app.route("/pp/boms", methods=["POST"])
def pp_bom_create():
    tid, rid = _tenant(), _req_id()
    s = get_store()
    if s.idem_get(rid):
        return _err("IDEMPOTENT_CONFLICT", "幂等冲突", 409)
    b = request.get_json() or {}
    err_msg = validators.validate_required(b, "pp_bom_create")
    if err_msg:
        return _err("VALIDATION_ERROR", "请求参数校验失败", 400, err_msg)
    bom = s.bom_create(tid, b.get("productMaterialId", ""), int(b.get("version", 1)))
    s.idem_set(rid, bom["bomId"])
    _human_audit(tid, f"创建了 BOM (bomId={bom['bomId']})，产品 {b.get('productMaterialId', '')}", _trace_id())
    _audit(tid, "bom.create", 1, "bom", bom["bomId"])
    return jsonify(bom), 201
@app.route("/pp/work-orders", methods=["GET"])
def pp_wo_list():
    page = max(1, int(request.args.get("page", 1)))
    page_size = max(1, min(100, int(request.args.get("pageSize", 20))))
    data, total = get_store().work_order_list(_tenant(), page, page_size)
    return jsonify({"data": data, "total": total, "page": page, "pageSize": page_size}), 200
@app.route("/pp/work-orders/<work_order_id>", methods=["GET"])
def pp_wo_get(work_order_id: str):
    wo = get_store().work_order_get(_tenant(), work_order_id)
    if not wo:
        return _err("NOT_FOUND", "工单不存在", 404)
    return jsonify(wo), 200
@app.route("/pp/work-orders/<work_order_id>", methods=["DELETE"])
def pp_wo_delete(work_order_id: str):
    tid = _tenant()
    if not get_store().work_order_soft_delete(tid, work_order_id):
        return _err("NOT_FOUND", "工单不存在或已删除", 404)
    _human_audit(tid, f"软删除工单 {work_order_id}", _trace_id())
    _audit(tid, "work_order.delete", 1, "work_order", work_order_id)
    return jsonify({"deleted": True, "workOrderId": work_order_id}), 200
@app.route("/pp/work-orders", methods=["POST"])
def pp_wo_create():
    tid, rid = _tenant(), _req_id()
    s = get_store()
    if s.idem_get(rid):
        return _err("IDEMPOTENT_CONFLICT", "幂等冲突", 409)
    b = request.get_json() or {}
    err_msg = validators.validate_required(b, "pp_wo_create")
    if err_msg:
        return _err("VALIDATION_ERROR", "请求参数校验失败", 400, err_msg)
    wo = s.work_order_create(tid, b.get("bomId", ""), b.get("productMaterialId", ""), float(b.get("plannedQuantity", 1)))
    s.idem_set(rid, wo["workOrderId"])
    _human_audit(tid, f"创建了工单 (workOrderId={wo['workOrderId']})，BOM {b.get('bomId', '')}", _trace_id())
    _audit(tid, "work_order.create", 1, "work_order", wo["workOrderId"])
    return jsonify(wo), 201

@app.route("/gl/balance", methods=["GET"])
def gl_balance():
    data = get_store().gl_balance(_tenant())
    return jsonify({"data": data}), 200

@app.route("/gl/trial-balance", methods=["GET"])
def gl_trial_balance():
    data = get_store().gl_balance(_tenant())
    return jsonify({"data": data}), 200

@app.route("/ar/invoices/<invoice_id>/receipts", methods=["POST"])
def ar_register_receipt(invoice_id: str):
    tid, rid = _tenant(), _req_id()
    b = request.get_json() or {}
    err_msg = validators.validate_required(b, "ar_receipt")
    if err_msg:
        return _err("VALIDATION_ERROR", "请求参数校验失败", 400, err_msg)
    amt = int(b.get("amountCents", 0))
    inv = get_store().ar_get(tid, invoice_id)
    if not inv:
        return _err("NOT_FOUND", "应收发票不存在", 404)
    err_msg = validators.validate_receipt_amount(
        amt, inv.get("amountCents", 0), inv.get("paidAmountCents", 0)
    )
    if err_msg:
        return _err("BUSINESS_RULE_VIOLATION", "业务规则校验失败", 400, err_msg)
    inv = get_store().ar_register_receipt(tid, invoice_id, amt, idem_key=rid)
    if not inv:
        return _err("NOT_FOUND", "应收发票不存在", 404)
    _human_audit(tid, f"登记应收发票 {invoice_id} 收款，金额 {amt} 分", _trace_id())
    _audit(tid, "ar_invoice.receipt", 1, "ar_invoice", invoice_id)
    return jsonify(inv), 200

@app.route("/ap/invoices/<invoice_id>/payments", methods=["POST"])
def ap_register_payment(invoice_id: str):
    tid, rid = _tenant(), _req_id()
    b = request.get_json() or {}
    err_msg = validators.validate_required(b, "ap_payment")
    if err_msg:
        return _err("VALIDATION_ERROR", "请求参数校验失败", 400, err_msg)
    amt = int(b.get("amountCents", 0))
    inv = get_store().ap_get(tid, invoice_id)
    if not inv:
        return _err("NOT_FOUND", "应付发票不存在", 404)
    err_msg = validators.validate_payment_amount(
        amt, inv.get("amountCents", 0), inv.get("paidAmountCents", 0)
    )
    if err_msg:
        return _err("BUSINESS_RULE_VIOLATION", "业务规则校验失败", 400, err_msg)
    inv = get_store().ap_register_payment(tid, invoice_id, amt, idem_key=rid)
    if not inv:
        return _err("NOT_FOUND", "应付发票不存在", 404)
    _human_audit(tid, f"登记应付发票 {invoice_id} 付款，金额 {amt} 分", _trace_id())
    _audit(tid, "ap_invoice.payment", 1, "ap_invoice", invoice_id)
    return jsonify(inv), 200

@app.route("/ar/ageing", methods=["GET"])
def ar_ageing():
    data = get_store().ar_ageing(_tenant())
    return jsonify({"data": data}), 200

@app.route("/ap/ageing", methods=["GET"])
def ap_ageing():
    data = get_store().ap_ageing(_tenant())
    return jsonify({"data": data}), 200

@app.route("/pp/work-orders/<work_order_id>/report", methods=["POST"])
def pp_wo_report(work_order_id: str):
    tid = _tenant()
    b = request.get_json() or {}
    err_msg = validators.validate_required(b, "pp_wo_report")
    if err_msg:
        return _err("BAD_REQUEST", "请填写完成数量", 400, err_msg)
    qty = float(b.get("completedQuantity", 0))
    unit_mat = float(b.get("unitMaterialCostCents", 0))
    unit_labor = float(b.get("unitLaborCostCents", 0))
    wo = get_store().work_order_report(tid, work_order_id, qty, unit_material_cost_cents=unit_mat, unit_labor_cost_cents=unit_labor)
    if not wo:
        return _err("NOT_FOUND", "工单不存在或无权查看", 404, "请检查工单编号")
    _human_audit(tid, f"工单 {work_order_id} 报工，完成数量 {qty}", _trace_id())
    _audit(tid, "work_order.report", 1, "work_order", work_order_id)
    return jsonify(wo), 200


@app.route("/pp/cost-summary", methods=["GET"])
def pp_cost_summary():
    """生产成本核算汇总：按工单列出材料费、人工费、总成本。"""
    tid = _tenant()
    page = max(1, int(request.args.get("page", 1)))
    page_size = max(1, min(100, int(request.args.get("pageSize", 20))))
    data, total = get_store().pp_cost_summary(tid, page=page, page_size=page_size)
    _human_audit(tid, "查询生产成本核算汇总")
    return jsonify({"data": data, "total": total, "page": page, "pageSize": page_size}), 200


@app.route("/pp/work-orders/<work_order_id>/cost", methods=["GET"])
def pp_work_order_cost(work_order_id: str):
    """单工单生产成本明细。"""
    tid = _tenant()
    cost = get_store().pp_work_order_cost(tid, work_order_id)
    if not cost:
        return _err("NOT_FOUND", "工单不存在或尚未报工", 404, "请检查工单编号后重试")
    _human_audit(tid, f"查询工单 {work_order_id} 成本")
    return jsonify(cost), 200


# ---------- 操作审计查询（商用：可追溯） ----------
@app.route("/audit-logs", methods=["GET"])
def audit_logs():
    tid = _tenant()
    page = max(1, int(request.args.get("page", 1)))
    page_size = max(1, min(200, int(request.args.get("pageSize", 50))))
    resource_type = (request.args.get("resourceType") or "").strip() or None
    data, total = get_store().audit_list(tid, page=page, page_size=page_size, resource_type=resource_type)
    return jsonify({"data": data, "total": total, "page": page, "pageSize": page_size}), 200


# ---------- 订单批量导入 ----------
@app.route("/orders/import", methods=["POST"])
def orders_import():
    tid, rid = _tenant(), _req_id()
    s = get_store()
    body = request.get_json() or {}
    items = body.get("items") or body.get("data") or []
    if not items or not isinstance(items, list):
        return _err("BAD_REQUEST", "请提供 items 数组", 400, "请求体需包含 items 或 data 字段")
    if len(items) > 2000:
        return _err("BAD_REQUEST", "单次导入不超过 2000 条", 400, "请分批导入以保证系统稳定")
    created, errors = [], []
    for i, row in enumerate(items):
        customer_id = (row.get("customerId") or "").strip()
        amt = int(row.get("totalAmountCents", 0))
        currency = (row.get("currency") or "CNY").strip()
        if not customer_id:
            errors.append({"index": i, "reason": "客户ID不能为空"})
            continue
        try:
            o = s.order_create(tid, customer_id, amt, currency)
            created.append({"index": i, "orderId": o["orderId"], "customerId": customer_id})
        except Exception as e:
            errors.append({"index": i, "reason": str(e), "customerId": customer_id})
    _human_audit(tid, f"批量导入订单，成功 {len(created)} 条，失败 {len(errors)} 条", _trace_id())
    return jsonify({"accepted": True, "created": len(created), "errors": len(errors), "details": created, "errorsDetail": errors}), 202


# ---------- 核心单据标准化导出 ----------
@app.route("/export/orders", methods=["GET"])
def export_orders():
    """销售订单导出：format=csv 返回 CSV（Excel 可打开）。"""
    import csv
    import io
    from flask import Response
    tid = _tenant()
    page_size = max(1, min(5000, int(request.args.get("pageSize", 500))))
    data, total = get_store().order_list(tid, page=1, page_size=page_size)
    _human_audit(tid, "导出销售订单")
    fmt = (request.args.get("format") or "csv").lower()
    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["订单ID", "客户ID", "状态", "金额(分)", "币种", "创建时间"])
        for o in data:
            writer.writerow([o.get("orderId"), o.get("customerId"), o.get("orderStatus"), o.get("totalAmountCents"), o.get("currency"), o.get("createdAt")])
        return Response(buf.getvalue(), mimetype="text/csv; charset=utf-8-sig", headers={"Content-Disposition": "attachment; filename=orders.csv"})
    return jsonify({"data": data, "total": total}), 200


@app.route("/export/ar/invoices", methods=["GET"])
def export_ar():
    """应收发票导出：format=csv 返回 CSV。"""
    import csv
    import io
    from flask import Response
    tid = _tenant()
    page_size = max(1, min(5000, int(request.args.get("pageSize", 500))))
    data, total = get_store().ar_list(tid, page=1, page_size=page_size)
    _human_audit(tid, "导出应收发票")
    fmt = (request.args.get("format") or "csv").lower()
    if fmt == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["发票ID", "客户ID", "凭证号", "金额(分)", "已付(分)", "币种", "到期日", "状态", "创建时间"])
        for inv in data:
            w.writerow([inv.get("invoiceId"), inv.get("customerId"), inv.get("documentNo"), inv.get("amountCents"), inv.get("paidAmountCents"), inv.get("currency"), inv.get("dueDate"), inv.get("status"), inv.get("createdAt")])
        return Response(buf.getvalue(), mimetype="text/csv; charset=utf-8-sig", headers={"Content-Disposition": "attachment; filename=ar_invoices.csv"})
    return jsonify({"data": data, "total": total}), 200


@app.route("/export/ap/invoices", methods=["GET"])
def export_ap():
    """应付发票导出：format=csv 返回 CSV。"""
    import csv
    import io
    from flask import Response
    tid = _tenant()
    page_size = max(1, min(5000, int(request.args.get("pageSize", 500))))
    data, total = get_store().ap_list(tid, page=1, page_size=page_size)
    _human_audit(tid, "导出应付发票")
    fmt = (request.args.get("format") or "csv").lower()
    if fmt == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["发票ID", "供应商ID", "凭证号", "金额(分)", "已付(分)", "币种", "到期日", "状态", "创建时间"])
        for inv in data:
            w.writerow([inv.get("invoiceId"), inv.get("supplierId"), inv.get("documentNo"), inv.get("amountCents"), inv.get("paidAmountCents"), inv.get("currency"), inv.get("dueDate"), inv.get("status"), inv.get("createdAt")])
        return Response(buf.getvalue(), mimetype="text/csv; charset=utf-8-sig", headers={"Content-Disposition": "attachment; filename=ap_invoices.csv"})
    return jsonify({"data": data, "total": total}), 200


@app.route("/export/mm/materials", methods=["GET"])
def export_materials():
    """物料主数据导出：format=csv 返回 CSV。"""
    import csv
    import io
    from flask import Response
    tid = _tenant()
    page_size = max(1, min(5000, int(request.args.get("pageSize", 500))))
    data, total = get_store().material_list(tid, page=1, page_size=page_size)
    _human_audit(tid, "导出物料")
    fmt = (request.args.get("format") or "csv").lower()
    if fmt == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["物料ID", "物料编码", "名称", "单位", "创建时间"])
        for m in data:
            w.writerow([m.get("materialId"), m.get("materialCode"), m.get("name"), m.get("unit"), m.get("createdAt")])
        return Response(buf.getvalue(), mimetype="text/csv; charset=utf-8-sig", headers={"Content-Disposition": "attachment; filename=materials.csv"})
    return jsonify({"data": data, "total": total}), 200


if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8002")))
