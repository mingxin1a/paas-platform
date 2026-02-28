"""
MES 细胞 Flask 应用 - 工业场景：BOM→计划→生产订单→领料→报工→生产入库→追溯。
01 合规（验签、人性化审计）；操作日志留存≥1年（配置）；车间数据权限；生产入库幂等；领料防超领。
"""
from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from .store import get_store
from . import event_publisher as _events

# 工业数据留存：操作日志保留≥1年（模拟配置，实际由持久化与清理策略实现）
OPERATION_LOG_RETENTION_DAYS = int(os.environ.get("MES_OPERATION_LOG_RETENTION_DAYS", "365"))

def _human_audit(tenant_id: str, operation_desc: str, trace_id: str = "") -> None:
    user_id = request.headers.get("X-User-Id") or request.headers.get("X-Tenant-Id") or "system"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    trace_id = trace_id or request.headers.get("X-Trace-Id") or request.headers.get("X-Request-ID") or ""
    import logging
    logging.getLogger("mes.audit").info(f"【人性化审计】租户 {tenant_id} 用户 {user_id} 在 {ts} {operation_desc}，trace_id={trace_id}")

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

def _tenant() -> str:
    return (request.headers.get("X-Tenant-Id") or "").strip() or "default"

def _request_id() -> str:
    return (request.headers.get("X-Request-ID") or "").strip() or str(uuid.uuid4())

def _workshop_id() -> str:
    """车间数据权限：车间主任只能看本车间订单"""
    return (request.headers.get("X-Workshop-Id") or "").strip()

def _err(code: str, message: str, request_id: str = "", details: str = "", status: int = 400) -> tuple:
    body = {"code": code, "message": message, "requestId": request_id or _request_id()}
    if details:
        body["details"] = details
    return (body, status if code != "NOT_FOUND" else 404)

def _user_id() -> str:
    return (request.headers.get("X-User-Id") or request.headers.get("X-Tenant-Id") or "system").strip()

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
    return jsonify({"status": "up", "cell": "mes"}), 200

@app.route("/config/retention")
def config_retention():
    """工业数据留存配置：操作日志保留天数（≥1年模拟）"""
    return jsonify({"operationLogRetentionDays": OPERATION_LOG_RETENTION_DAYS}), 200

# ---------- 工单（支持车间过滤） ----------
@app.route("/work-orders", methods=["GET"])
def list_work_orders():
    tenant_id = _tenant()
    workshop_id = _workshop_id() or request.args.get("workshopId")
    page = max(1, int(request.args.get("page", 1)))
    page_size = max(1, min(100, int(request.args.get("pageSize", 20))))
    data, total = get_store().work_order_list(tenant_id, workshop_id=workshop_id or None, page=page, page_size=page_size)
    _human_audit(tenant_id, "查询工单列表")
    return jsonify({"data": data, "total": total, "page": page, "pageSize": page_size}), 200

@app.route("/work-orders", methods=["POST"])
def create_work_order():
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    if store.idem_get(req_id):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "details": "", "requestId": req_id}), 409
    body = request.get_json() or {}
    order_no = (body.get("orderNo") or "").strip()
    if not order_no:
        return jsonify(_err("BAD_REQUEST", "orderNo 必填", req_id)), 400
    w = store.work_order_create(tenant_id, order_no, body.get("productCode", ""), int(body.get("qty", 1)), body.get("workshopId", ""))
    store.idem_set(req_id, w["workOrderId"])
    _human_audit(tenant_id, f"创建工单 {w['workOrderId']}", req_id)
    return jsonify(w), 201

@app.route("/work-orders/<work_order_id>", methods=["GET"])
def get_work_order(work_order_id: str):
    tenant_id = _tenant()
    w = get_store().work_order_get(tenant_id, work_order_id)
    if not w:
        return jsonify(_err("NOT_FOUND", "工单不存在", _request_id())), 404
    _human_audit(tenant_id, f"查询工单 {work_order_id}")
    return jsonify(w), 200

@app.route("/work-orders/<work_order_id>", methods=["PATCH"])
def update_work_order(work_order_id: str):
    tenant_id = _tenant()
    store = get_store()
    body = request.get_json() or {}
    status = body.get("status")
    if status is None:
        return jsonify(_err("BAD_REQUEST", "status 必填", _request_id())), 400
    w = store.work_order_update_status(tenant_id, work_order_id, int(status))
    if not w:
        return jsonify(_err("NOT_FOUND", "工单不存在", _request_id())), 404
    if int(status) == 2:
        _events.publish("mes.work_order.completed", {"workOrderId": work_order_id, "tenantId": tenant_id, "orderNo": w.get("orderNo", "")}, trace_id=request.headers.get("X-Trace-Id") or _request_id())
    _human_audit(tenant_id, f"更新工单 {work_order_id} 状态为 {status}")
    return jsonify(w), 200

# ---------- BOM ----------
@app.route("/boms", methods=["GET"])
def list_boms():
    tenant_id = _tenant()
    data = get_store().bom_list(tenant_id, request.args.get("productSku"))
    _human_audit(tenant_id, "查询BOM列表")
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/boms", methods=["POST"])
def create_bom():
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    if store.idem_get(req_id):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "请求已处理，请勿重复提交", "details": "幂等键已使用", "requestId": req_id}), 409
    body = request.get_json() or {}
    product_sku = (body.get("productSku") or "").strip()
    if not product_sku:
        return jsonify(_err("BAD_REQUEST", "产品编码不能为空", req_id, "请提供 productSku")), 400
    lines = body.get("lines") or []
    b = store.bom_create(tenant_id, product_sku, int(body.get("version", 1)), lines=lines if isinstance(lines, list) else None)
    store.idem_set(req_id, b["bomId"])
    store.audit_append(tenant_id, _user_id(), "CREATE", "BOM", b["bomId"], req_id)
    _human_audit(tenant_id, f"创建BOM {b['bomId']}", req_id)
    return jsonify(b), 201

@app.route("/boms/<bom_id>", methods=["GET"])
def get_bom(bom_id: str):
    tenant_id = _tenant()
    b = get_store().bom_get(tenant_id, bom_id)
    if not b:
        return jsonify(_err("NOT_FOUND", "BOM不存在", _request_id(), "请检查 bomId")), 404
    return jsonify(b), 200

@app.route("/boms/<bom_id>/lines", methods=["GET"])
def list_bom_lines(bom_id: str):
    tenant_id = _tenant()
    if not get_store().bom_get(tenant_id, bom_id):
        return jsonify(_err("NOT_FOUND", "BOM不存在", _request_id())), 404
    data = get_store().bom_lines_by_bom(tenant_id, bom_id)
    return jsonify({"data": data, "bomId": bom_id, "total": len(data)}), 200

# ---------- 生产计划 ----------
@app.route("/production-plans", methods=["GET"])
def list_production_plans():
    tenant_id = _tenant()
    page = max(1, int(request.args.get("page", 1)))
    page_size = max(1, min(100, int(request.args.get("pageSize", 20))))
    data, total = get_store().production_plan_list(tenant_id, page=page, page_size=page_size)
    return jsonify({"data": data, "total": total, "page": page, "pageSize": page_size}), 200

@app.route("/production-plans", methods=["POST"])
def create_production_plan():
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    if store.idem_get(req_id):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "details": "", "requestId": req_id}), 409
    body = request.get_json() or {}
    plan_no = (body.get("planNo") or "").strip()
    product_sku = (body.get("productSku") or "").strip()
    if not plan_no or not product_sku:
        return jsonify(_err("BAD_REQUEST", "planNo、productSku 必填", req_id)), 400
    p = store.production_plan_create(tenant_id, plan_no, product_sku, float(body.get("plannedQty", 0)), body.get("planDate", ""))
    store.idem_set(req_id, p["planId"])
    _human_audit(tenant_id, f"创建生产计划 {p['planId']}", req_id)
    return jsonify(p), 201

# ---------- 生产订单（车间数据权限） ----------
@app.route("/production-orders", methods=["GET"])
def list_production_orders():
    tenant_id = _tenant()
    workshop_id = _workshop_id() or request.args.get("workshopId")
    page = max(1, int(request.args.get("page", 1)))
    page_size = max(1, min(100, int(request.args.get("pageSize", 20))))
    data, total = get_store().production_order_list(tenant_id, workshop_id=workshop_id or None, page=page, page_size=page_size)
    _human_audit(tenant_id, "查询生产订单列表")
    return jsonify({"data": data, "total": total, "page": page, "pageSize": page_size}), 200

@app.route("/production-orders", methods=["POST"])
def create_production_order():
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    if store.idem_get(req_id):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "details": "", "requestId": req_id}), 409
    body = request.get_json() or {}
    workshop_id = (body.get("workshopId") or "").strip()
    order_no = (body.get("orderNo") or "").strip()
    product_sku = (body.get("productSku") or "").strip()
    if not workshop_id or not order_no or not product_sku:
        return jsonify(_err("BAD_REQUEST", "workshopId、orderNo、productSku 必填", req_id)), 400
    o = store.production_order_create(tenant_id, workshop_id, order_no, product_sku, float(body.get("quantity", 1)), body.get("planId", ""))
    store.idem_set(req_id, o["orderId"])
    store.audit_append(tenant_id, _user_id(), "CREATE", "ProductionOrder", o["orderId"], req_id)
    _events.publish("mes.production_order.created", {"orderId": o["orderId"], "tenantId": tenant_id, "orderNo": order_no, "productSku": product_sku, "quantity": o.get("quantity", 1), "planId": o.get("planId", ""), "workshopId": workshop_id}, trace_id=request.headers.get("X-Trace-Id") or req_id)
    _human_audit(tenant_id, f"创建生产订单 {o['orderId']}", req_id)
    return jsonify(o), 201

@app.route("/production-orders/export", methods=["GET"])
def export_production_orders():
    tenant_id = _tenant()
    workshop_id = _workshop_id() or request.args.get("workshopId")
    store = get_store()
    data, _ = store.production_order_list(tenant_id, workshop_id=workshop_id or None, page=1, page_size=10000)
    import csv, io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["orderId", "orderNo", "workshopId", "planId", "productSku", "quantity", "status", "createdAt", "updatedAt"])
    for o in data:
        w.writerow([o.get("orderId"), o.get("orderNo"), o.get("workshopId"), o.get("planId"), o.get("productSku"), o.get("quantity"), o.get("status"), o.get("createdAt"), o.get("updatedAt")])
    from flask import Response
    return Response(buf.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=production_orders.csv"})

@app.route("/production-orders/<order_id>", methods=["GET"])
def get_production_order(order_id: str):
    tenant_id = _tenant()
    workshop_id = _workshop_id()
    o = get_store().production_order_get(tenant_id, order_id)
    if not o:
        return jsonify(_err("NOT_FOUND", "生产订单不存在", _request_id(), "请检查 orderId")), 404
    if workshop_id and o.get("workshopId") != workshop_id:
        return jsonify(_err("FORBIDDEN", "无权查看该车间订单", _request_id(), "请使用对应车间权限")), 403
    return jsonify(o), 200

@app.route("/production-orders/<order_id>", methods=["PATCH"])
def update_production_order(order_id: str):
    tenant_id = _tenant()
    workshop_id = _workshop_id()
    store = get_store()
    o = store.production_order_get(tenant_id, order_id)
    if not o:
        return jsonify(_err("NOT_FOUND", "生产订单不存在", _request_id())), 404
    if workshop_id and o.get("workshopId") != workshop_id:
        return jsonify(_err("FORBIDDEN", "无权操作该车间订单", _request_id())), 403
    body = request.get_json() or {}
    status = body.get("status")
    if status is None:
        return jsonify(_err("BAD_REQUEST", "请提供 status", _request_id(), "如 1=进行中 2=已完成")), 400
    updated = store.production_order_update_status(tenant_id, order_id, int(status))
    if not updated:
        return jsonify(_err("NOT_FOUND", "生产订单不存在", _request_id())), 404
    if int(status) == 2:
        _events.publish("mes.production_order.completed", {"orderId": order_id, "tenantId": tenant_id, "orderNo": updated.get("orderNo", ""), "productSku": updated.get("productSku", ""), "quantity": updated.get("quantity", 1)}, trace_id=request.headers.get("X-Trace-Id") or _request_id())
    store.audit_append(tenant_id, _user_id(), "UPDATE", "ProductionOrder", order_id, _request_id())
    return jsonify(updated), 200

@app.route("/production-orders/<order_id>/material-requirements", methods=["GET"])
def get_material_requirements(order_id: str):
    tenant_id = _tenant()
    store = get_store()
    o = store.production_order_get(tenant_id, order_id)
    if not o:
        return jsonify(_err("NOT_FOUND", "生产订单不存在", _request_id())), 404
    reqs = store.material_requirements(tenant_id, order_id)
    if reqs is None:
        return jsonify(_err("NOT_FOUND", "生产订单不存在", _request_id())), 404
    return jsonify({"orderId": order_id, "productSku": o.get("productSku"), "quantity": o.get("quantity"), "requirements": reqs}), 200

# ---------- 领料（防超领） ----------
@app.route("/material-issues", methods=["GET"])
def list_material_issues():
    tenant_id = _tenant()
    data = get_store().material_issue_list(tenant_id, request.args.get("orderId"))
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/material-issues", methods=["POST"])
def create_material_issue():
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    body = request.get_json() or {}
    order_id = (body.get("orderId") or "").strip()
    material_sku = (body.get("materialSku") or "").strip()
    if not order_id or not material_sku:
        return jsonify(_err("BAD_REQUEST", "生产订单与物料编码不能为空", req_id, "请提供 orderId、materialSku")), 400
    m = store.material_issue_create(tenant_id, order_id, material_sku, float(body.get("requiredQty", 0)))
    if not m:
        return jsonify(_err("BUSINESS_RULE_VIOLATION", "无法创建领料单", req_id, "生产订单不存在或已关闭")), 400
    store.audit_append(tenant_id, _user_id(), "CREATE", "MaterialIssue", m["issueId"], req_id)
    _human_audit(tenant_id, f"创建领料单 {m['issueId']}", req_id)
    return jsonify(m), 201

@app.route("/material-issues/<issue_id>/issue", methods=["POST"])
def issue_material(issue_id: str):
    tenant_id = _tenant()
    body = request.get_json() or {}
    qty = float(body.get("issueQty", 0))
    if qty <= 0:
        return jsonify(_err("BAD_REQUEST", "issueQty 须大于 0", _request_id())), 400
    m = get_store().material_issue_issue(tenant_id, issue_id, qty)
    if not m:
        return jsonify(_err("BUSINESS_RULE_VIOLATION", "领料失败", _request_id(), "领料数量不得超过应领数量，或领料单不存在")), 400
    get_store().audit_append(tenant_id, _user_id(), "ISSUE", "MaterialIssue", issue_id, _request_id())
    _human_audit(tenant_id, f"领料 {issue_id} 数量 {qty}")
    return jsonify(m), 200

# ---------- 报工（支持批量 100+ 工序） ----------
@app.route("/work-reports", methods=["GET"])
def list_work_reports():
    tenant_id = _tenant()
    page = max(1, int(request.args.get("page", 1)))
    page_size = max(1, min(200, int(request.args.get("pageSize", 20))))
    data, total = get_store().work_report_list(tenant_id, order_id=request.args.get("orderId"), page=page, page_size=page_size)
    return jsonify({"data": data, "total": total, "page": page, "pageSize": page_size}), 200

@app.route("/work-reports/batch", methods=["POST"])
def batch_work_report():
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    body = request.get_json() or {}
    order_id = (body.get("orderId") or "").strip()
    items = body.get("items") or body.get("operations") or []
    if not order_id or not items:
        return jsonify(_err("BAD_REQUEST", "orderId、items 必填", req_id)), 400
    if len(items) > 200:
        return jsonify(_err("BAD_REQUEST", "单次报工工序数不超过 200", req_id)), 400
    if not store.production_order_get(tenant_id, order_id):
        return jsonify(_err("NOT_FOUND", "生产订单不存在", req_id)), 404
    created = store.work_report_batch(tenant_id, order_id, items)
    store.audit_append(tenant_id, _user_id(), "BATCH_REPORT", "WorkReport", order_id, req_id)
    _human_audit(tenant_id, f"批量报工 生产订单 {order_id} 共 {len(created)} 条")
    return jsonify({"accepted": True, "count": len(created), "data": created}), 201

# ---------- 生产入库（幂等） ----------
@app.route("/production-inbounds", methods=["POST"])
def create_production_inbound():
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    body = request.get_json() or {}
    order_id = (body.get("orderId") or "").strip()
    warehouse_id = (body.get("warehouseId") or "").strip()
    quantity = float(body.get("quantity", 0))
    if not order_id or not warehouse_id or quantity <= 0:
        return jsonify(_err("BAD_REQUEST", "orderId、warehouseId、quantity 必填且 quantity>0", req_id)), 400
    record, is_new = store.production_inbound_create(tenant_id, order_id, warehouse_id, quantity, body.get("lotNumber", ""), body.get("serialNumbers"), idempotent_key=req_id)
    if not record:
        return jsonify(_err("NOT_FOUND", "生产订单不存在", req_id)), 404
    if not is_new:
        return jsonify(record), 200
    store.audit_append(tenant_id, _user_id(), "PRODUCTION_INBOUND", "ProductionInbound", record["inboundId"], req_id)
    _events.publish("mes.production_inbound.completed", {"inboundId": record["inboundId"], "orderId": order_id, "tenantId": tenant_id, "warehouseId": warehouse_id, "quantity": quantity, "lotNumber": record.get("lotNumber", "")}, trace_id=request.headers.get("X-Trace-Id") or req_id)
    _human_audit(tenant_id, f"生产入库 {record['inboundId']}", req_id)
    return jsonify(record), 201

# ---------- 质检 ----------
@app.route("/quality-inspections", methods=["GET"])
def list_quality_inspections():
    tenant_id = _tenant()
    page = max(1, int(request.args.get("page", 1)))
    page_size = max(1, min(100, int(request.args.get("pageSize", 20))))
    data, total = get_store().quality_inspection_list(tenant_id, order_id=request.args.get("orderId"), page=page, page_size=page_size)
    return jsonify({"data": data, "total": total, "page": page, "pageSize": page_size}), 200

@app.route("/quality-inspections", methods=["POST"])
def create_quality_inspection():
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    body = request.get_json() or {}
    order_id = (body.get("orderId") or "").strip()
    lot_number = (body.get("lotNumber") or "").strip()
    result = (body.get("result") or "pass").strip().upper() or "PASS"
    defect_code = (body.get("defectCode") or "").strip()
    if not order_id or not lot_number:
        return jsonify(_err("BAD_REQUEST", "生产订单与批次号不能为空", req_id, "请提供 orderId、lotNumber")), 400
    q = store.quality_inspection_create(tenant_id, order_id, lot_number, result, defect_code)
    if not q:
        return jsonify(_err("NOT_FOUND", "生产订单不存在", req_id)), 404
    store.audit_append(tenant_id, _user_id(), "CREATE", "QualityInspection", q["inspectionId"], req_id)
    _human_audit(tenant_id, f"创建质检记录 {q['inspectionId']}", req_id)
    return jsonify(q), 201

# ---------- 看板 ----------
@app.route("/board", methods=["GET"])
def board():
    tenant_id = _tenant()
    data = get_store().board_data(tenant_id)
    return jsonify(data), 200

# ---------- 工业设备遥测（标准化 HTTP 接入） ----------
@app.route("/devices/telemetry", methods=["POST"])
def device_telemetry_submit():
    tenant_id = _tenant()
    body = request.get_json() or {}
    device_id = (body.get("deviceId") or "").strip()
    metric = (body.get("metric") or "").strip()
    value = body.get("value")
    ts = body.get("timestamp") or body.get("ts")
    if not device_id or not metric:
        return jsonify(_err("BAD_REQUEST", "deviceId、metric 必填", _request_id())), 400
    try:
        val = float(value) if value is not None else 0.0
    except (TypeError, ValueError):
        val = 0.0
    get_store().device_telemetry_submit(tenant_id, device_id, metric, val, ts or "")
    return jsonify({"accepted": True}), 202

@app.route("/devices/telemetry", methods=["GET"])
def device_telemetry_list():
    tenant_id = _tenant()
    device_id = request.args.get("deviceId", "").strip() or None
    limit = max(1, min(500, int(request.args.get("limit", 100))))
    data = get_store().device_telemetry_list(tenant_id, device_id=device_id, limit=limit)
    return jsonify({"data": data, "total": len(data)}), 200

# ---------- 生产追溯 ----------
@app.route("/trace/lot/<lot_number>", methods=["GET"])
def trace_by_lot(lot_number: str):
    tenant_id = _tenant()
    data = get_store().trace_by_lot(tenant_id, lot_number)
    return jsonify({"data": data, "lotNumber": lot_number}), 200

@app.route("/trace/order/<order_id>", methods=["GET"])
def trace_by_order(order_id: str):
    tenant_id = _tenant()
    data = get_store().trace_by_order(tenant_id, order_id)
    return jsonify({"data": data, "orderId": order_id}), 200

@app.route("/trace/serial/<serial_number>", methods=["GET"])
def trace_by_serial(serial_number: str):
    tenant_id = _tenant()
    data = get_store().trace_by_serial(tenant_id, serial_number)
    return jsonify({"data": data, "serialNumber": serial_number}), 200

# ---------- 审计日志 ----------
@app.route("/audit-logs", methods=["GET"])
def list_audit_logs():
    tenant_id = _tenant()
    page = max(1, int(request.args.get("page", 1)))
    page_size = max(1, min(100, int(request.args.get("pageSize", 50))))
    resource_type = (request.args.get("resourceType") or "").strip() or None
    data, total = get_store().audit_list(tenant_id, page=page, page_size=page_size, resource_type=resource_type)
    return jsonify({"data": data, "total": total, "page": page, "pageSize": page_size}), 200

# ---------- 批量导出（CSV） ----------
@app.route("/work-reports/export", methods=["GET"])
def export_work_reports():
    tenant_id = _tenant()
    order_id = request.args.get("orderId")
    store = get_store()
    data, _ = store.work_report_list(tenant_id, order_id=order_id, page=1, page_size=10000)
    import csv, io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["reportId", "orderId", "operationCode", "completedQty", "reportAt", "createdAt"])
    for r in data:
        w.writerow([r.get("reportId"), r.get("orderId"), r.get("operationCode"), r.get("completedQty"), r.get("reportAt"), r.get("createdAt")])
    from flask import Response
    return Response(buf.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=work_reports.csv"})

# ---------- 监控指标（工业版） ----------
@app.route("/metrics")
def metrics():
    tenant_id = _tenant()
    store = get_store()
    cap = store.capacity_stats(tenant_id)
    issue_acc = store.issue_accuracy(tenant_id)
    return jsonify({
        "cell": "mes",
        "metrics": {
            "productionCompletionRatePct": cap.get("completionRatePct", 0),
            "issueAccuracyPct": issue_acc.get("accuracyPct", 100),
            "equipmentOeePct": 85.0,  # 模拟设备稼动率
            "totalProductionOrders": cap.get("totalOrders", 0),
            "completedProductionOrders": cap.get("completedOrders", 0),
        },
        "operationLogRetentionDays": OPERATION_LOG_RETENTION_DAYS,
    }), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8006))
    app.run(host="0.0.0.0", port=port, debug=False)
