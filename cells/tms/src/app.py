"""
TMS 细胞 Flask 应用 - 运单/车辆/司机/轨迹/到货/费用/对账。工业物流；数据权限；操作日志留存≥1年（模拟配置）。
"""
from __future__ import annotations
import os
import time
import uuid
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from .store import get_store
from . import event_publisher as _events

def _human_audit(tenant_id: str, operation_desc: str, trace_id: str = "") -> None:
    user_id = request.headers.get("X-User-Id") or request.headers.get("X-Tenant-Id") or "system"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    trace_id = trace_id or request.headers.get("X-Trace-Id") or request.headers.get("X-Request-ID") or ""
    import logging
    logging.getLogger("tms.audit").info(f"【人性化审计】租户 {tenant_id} 用户 {user_id} 在 {ts} {operation_desc}，trace_id={trace_id}")

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

def _tenant() -> str:
    return (request.headers.get("X-Tenant-Id") or "").strip() or "default"

def _request_id() -> str:
    return (request.headers.get("X-Request-ID") or "").strip() or str(uuid.uuid4())

def _owner_id() -> str:
    """物流专员数据权限：只能看自己负责的订单"""
    return (request.headers.get("X-User-Id") or "").strip()

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

OPERATION_LOG_RETENTION_DAYS = int(os.environ.get("TMS_OPERATION_LOG_RETENTION_DAYS", "365"))

@app.route("/health")
def health():
    return jsonify({"status": "up", "cell": "tms"}), 200

@app.route("/config/retention")
def config_retention():
    return jsonify({"operationLogRetentionDays": OPERATION_LOG_RETENTION_DAYS}), 200

@app.route("/shipments", methods=["GET"])
def list_shipments():
    tenant_id = _tenant()
    owner_id = _owner_id() or request.args.get("ownerId")
    page = max(1, int(request.args.get("page", 1)))
    page_size = max(1, min(100, int(request.args.get("pageSize", 20))))
    data, total = get_store().shipment_list(tenant_id, owner_id=owner_id or None, page=page, page_size=page_size)
    _human_audit(tenant_id, "查询运单列表")
    return jsonify({"data": data, "total": total, "page": page, "pageSize": page_size}), 200

@app.route("/shipments", methods=["POST"])
def create_shipment():
    tenant_id = _tenant()
    req_id = _request_id()
    owner_id = _owner_id()
    store = get_store()
    if store.idem_get(req_id):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "请求已处理，请勿重复提交", "details": "幂等键已使用", "requestId": req_id}), 409
    body = request.get_json() or {}
    s = store.shipment_create(tenant_id, body.get("trackingNo", ""), body.get("origin", ""), body.get("destination", ""), 1, owner_id or body.get("ownerId", ""), body.get("vehicleId", ""), body.get("driverId", ""), body.get("wmsOutboundOrderId", ""), body.get("erpOrderId", ""))
    store.idem_set(req_id, s["shipmentId"])
    store.audit_append(tenant_id, _user_id(), "CREATE", "Shipment", s["shipmentId"], req_id)
    _human_audit(tenant_id, f"创建运单 {s['shipmentId']}", req_id)
    return jsonify(s), 201

@app.route("/shipments/export", methods=["GET"])
def export_shipments():
    tenant_id = _tenant()
    owner_id = _owner_id() or request.args.get("ownerId")
    data, _ = get_store().shipment_list(tenant_id, owner_id=owner_id or None, page=1, page_size=10000)
    import csv, io
    from flask import Response
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["shipmentId", "trackingNo", "origin", "destination", "status", "ownerId", "vehicleId", "driverId", "createdAt", "updatedAt"])
    for s in data:
        w.writerow([s.get("shipmentId"), s.get("trackingNo"), s.get("origin"), s.get("destination"), s.get("status"), s.get("ownerId"), s.get("vehicleId", ""), s.get("driverId", ""), s.get("createdAt"), s.get("updatedAt")])
    return Response(buf.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=shipments.csv"})

@app.route("/shipments/<shipment_id>", methods=["GET"])
def get_shipment(shipment_id: str):
    tenant_id = _tenant()
    owner_id = _owner_id()
    store = get_store()
    s = store.shipment_get(tenant_id, shipment_id)
    if not s:
        return jsonify(_err("NOT_FOUND", "运单不存在", _request_id(), "请检查 shipmentId")), 404
    if owner_id and s.get("ownerId") != owner_id:
        return jsonify(_err("FORBIDDEN", "无权查看该运单", _request_id(), "仅可查看本人负责的运单")), 403
    _human_audit(tenant_id, f"查询运单 {shipment_id}")
    return jsonify(s), 200

@app.route("/shipments/<shipment_id>", methods=["PATCH"])
def update_shipment(shipment_id: str):
    tenant_id = _tenant()
    owner_id = _owner_id()
    store = get_store()
    s = store.shipment_get(tenant_id, shipment_id)
    if not s:
        return jsonify(_err("NOT_FOUND", "运单不存在", _request_id())), 404
    if owner_id and s.get("ownerId") != owner_id:
        return jsonify(_err("FORBIDDEN", "无权操作该运单", _request_id())), 403
    body = request.get_json() or {}
    status = body.get("status")
    vehicle_id = (body.get("vehicleId") or "").strip()
    driver_id = (body.get("driverId") or "").strip()
    if vehicle_id or driver_id:
        s = store.shipment_assign_vehicle_driver(tenant_id, shipment_id, vehicle_id, driver_id)
    if status is not None:
        s = store.shipment_update_status(tenant_id, shipment_id, int(status))
        if int(status) == 2:
            _events.publish("tms.shipment.dispatched", {"shipmentId": shipment_id, "tenantId": tenant_id, "trackingNo": s.get("trackingNo", ""), "status": status}, trace_id=request.headers.get("X-Trace-Id") or _request_id())
        store.audit_append(tenant_id, _user_id(), "UPDATE_STATUS", "Shipment", shipment_id, _request_id())
    _human_audit(tenant_id, f"更新运单 {shipment_id}")
    return jsonify(s), 200

# ---------- 车辆 ----------
@app.route("/vehicles", methods=["GET"])
def list_vehicles():
    data = get_store().vehicle_list(_tenant())
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/vehicles", methods=["POST"])
def create_vehicle():
    tid, rid = _tenant(), _request_id()
    store = get_store()
    if store.idem_get(rid):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "requestId": rid}), 409
    body = request.get_json() or {}
    plate = (body.get("plateNo") or "").strip()
    if not plate:
        return jsonify(_err("BAD_REQUEST", "plateNo 必填", rid)), 400
    v = store.vehicle_create(tid, plate, body.get("model", ""))
    store.idem_set(rid, v["vehicleId"])
    return jsonify(v), 201

# ---------- 司机（脱敏） ----------
@app.route("/drivers", methods=["GET"])
def list_drivers():
    data = get_store().driver_list(_tenant(), mask=True)
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/drivers", methods=["POST"])
def create_driver():
    tid, rid = _tenant(), _request_id()
    store = get_store()
    if store.idem_get(rid):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "requestId": rid}), 409
    body = request.get_json() or {}
    name = (body.get("name") or "").strip()
    if not name:
        return jsonify(_err("BAD_REQUEST", "name 必填", rid)), 400
    d = store.driver_create(tid, name, body.get("phone", ""), body.get("idNo", ""))
    store.idem_set(rid, d["driverId"])
    return jsonify({"driverId": d["driverId"], "tenantId": d["tenantId"], "name": d["name"], "phone": "***", "idNo": "***", "status": d["status"], "createdAt": d["createdAt"]}), 201

# ---------- 运输轨迹（模拟） ----------
@app.route("/tracks", methods=["GET"])
def list_tracks():
    data = get_store().track_list(_tenant(), request.args.get("shipmentId"))
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/tracks", methods=["POST"])
def add_track():
    tid, rid = _tenant(), _request_id()
    body = request.get_json() or {}
    shipment_id = (body.get("shipmentId") or "").strip()
    if not shipment_id:
        return jsonify(_err("BAD_REQUEST", "shipmentId 必填", rid)), 400
    if not get_store().shipment_get(tid, shipment_id):
        return jsonify({"code": "BUSINESS_RULE_VIOLATION", "message": "运单不存在", "details": "请先创建运单再记录轨迹", "requestId": rid}), 400
    t = get_store().track_add(tid, shipment_id, body.get("lat", ""), body.get("lng", ""), body.get("nodeName", ""))
    return jsonify(t), 201

# ---------- 到货确认 ----------
@app.route("/delivery-confirm", methods=["POST"])
def delivery_confirm():
    tid, rid = _tenant(), _request_id()
    store = get_store()
    body = request.get_json() or {}
    shipment_id = (body.get("shipmentId") or "").strip()
    if not shipment_id:
        return jsonify(_err("BAD_REQUEST", "shipmentId 必填", rid)), 400
    c = store.delivery_confirm_create(tid, shipment_id, body.get("status", "confirmed"))
    if not c:
        return jsonify(_err("BUSINESS_RULE_VIOLATION", "到货确认失败", rid, "运单不存在")), 400
    store.audit_append(tid, _user_id(), "DELIVERY_CONFIRM", "Shipment", shipment_id, rid)
    ship = store.shipment_get(tid, shipment_id)
    payload = {"shipmentId": shipment_id, "tenantId": tid, "confirmId": c.get("confirmId", "")}
    if ship:
        if ship.get("wmsOutboundOrderId"):
            payload["wmsOutboundOrderId"] = ship["wmsOutboundOrderId"]
        if ship.get("erpOrderId"):
            payload["erpOrderId"] = ship["erpOrderId"]
    _events.publish("tms.shipment.delivered", payload, trace_id=request.headers.get("X-Trace-Id") or rid)
    _human_audit(tid, f"到货确认 运单 {shipment_id}", rid)
    return jsonify(c), 201

# ---------- 运输费用（支持结算状态） ----------
@app.route("/transport-costs", methods=["GET"])
def list_transport_costs():
    data = get_store().transport_cost_list(_tenant(), request.args.get("shipmentId"), request.args.get("status"))
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/transport-costs/export", methods=["GET"])
def export_transport_costs():
    tid = _tenant()
    data = get_store().transport_cost_list(tid, None, None)
    import csv, io
    from flask import Response
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["costId", "shipmentId", "amountCents", "currency", "costType", "status", "createdAt"])
    for c in data:
        w.writerow([c.get("costId"), c.get("shipmentId"), c.get("amountCents"), c.get("currency"), c.get("costType"), c.get("status", "draft"), c.get("createdAt")])
    return Response(buf.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=transport_costs.csv"})

@app.route("/transport-costs", methods=["POST"])
def create_transport_cost():
    tid, rid = _tenant(), _request_id()
    store = get_store()
    body = request.get_json() or {}
    shipment_id = (body.get("shipmentId") or "").strip()
    if not shipment_id:
        return jsonify(_err("BAD_REQUEST", "运单不能为空", rid, "请提供 shipmentId")), 400
    c = store.transport_cost_create(tid, shipment_id, int(body.get("amountCents", 0)), body.get("costType", ""))
    store.audit_append(tid, _user_id(), "CREATE", "TransportCost", c["costId"], rid)
    return jsonify(c), 201

@app.route("/transport-costs/<cost_id>/settle", methods=["POST"])
def settle_transport_cost(cost_id: str):
    tid, rid = _tenant(), _request_id()
    c = get_store().transport_cost_settle(tid, cost_id)
    if not c:
        return jsonify(_err("NOT_FOUND", "费用记录不存在", rid)), 404
    get_store().audit_append(tid, _user_id(), "SETTLE", "TransportCost", cost_id, rid)
    return jsonify(c), 200

# ---------- 智能路线规划 ----------
@app.route("/routes/plan", methods=["POST"])
def route_plan():
    tid, rid = _tenant(), _request_id()
    body = request.get_json() or {}
    from_addr = (body.get("fromAddress") or body.get("from") or "").strip()
    to_addr = (body.get("toAddress") or body.get("to") or "").strip()
    shipment_id = (body.get("shipmentId") or "").strip()
    if not from_addr or not to_addr:
        return jsonify(_err("BAD_REQUEST", "fromAddress、toAddress 必填", rid)), 400
    r = get_store().route_plan_create(tid, from_addr, to_addr, shipment_id)
    return jsonify(r), 201

@app.route("/routes/plan", methods=["GET"])
def route_plan_list():
    data = get_store().route_plan_list(_tenant(), request.args.get("shipmentId") or None)
    return jsonify({"data": data, "total": len(data)}), 200

# ---------- 看板 ----------
@app.route("/board", methods=["GET"])
def board():
    data = get_store().board_data(_tenant())
    return jsonify(data), 200

# ---------- 物流对账（支持确认/完成状态） ----------
@app.route("/reconciliations", methods=["GET"])
def list_reconciliations():
    data = get_store().reconciliation_list(_tenant())
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/reconciliations", methods=["POST"])
def create_reconciliation():
    tid, rid = _tenant(), _request_id()
    store = get_store()
    body = request.get_json() or {}
    start = (body.get("periodStart") or "").strip()
    end = (body.get("periodEnd") or "").strip()
    if not start or not end:
        return jsonify(_err("BAD_REQUEST", "对账周期不能为空", rid, "请提供 periodStart、periodEnd")), 400
    r = store.reconciliation_create(tid, start, end, int(body.get("totalAmountCents", 0)))
    store.audit_append(tid, _user_id(), "CREATE", "Reconciliation", r["reconciliationId"], rid)
    return jsonify(r), 201

@app.route("/reconciliations/<reconciliation_id>/confirm", methods=["POST"])
def confirm_reconciliation(reconciliation_id: str):
    tid, rid = _tenant(), _request_id()
    r = get_store().reconciliation_confirm(tid, reconciliation_id)
    if not r:
        return jsonify(_err("NOT_FOUND", "对账单不存在", rid)), 404
    get_store().audit_append(tid, _user_id(), "CONFIRM", "Reconciliation", reconciliation_id, rid)
    return jsonify(r), 200

@app.route("/reconciliations/<reconciliation_id>/complete", methods=["POST"])
def complete_reconciliation(reconciliation_id: str):
    tid, rid = _tenant(), _request_id()
    r = get_store().reconciliation_complete(tid, reconciliation_id)
    if not r:
        return jsonify(_err("NOT_FOUND", "对账单不存在", rid)), 404
    get_store().audit_append(tid, _user_id(), "COMPLETE", "Reconciliation", reconciliation_id, rid)
    return jsonify(r), 200

# ---------- 审计日志 ----------
@app.route("/audit-logs", methods=["GET"])
def list_audit_logs():
    tid = _tenant()
    page = max(1, int(request.args.get("page", 1)))
    page_size = max(1, min(100, int(request.args.get("pageSize", 50))))
    resource_type = (request.args.get("resourceType") or "").strip() or None
    data, total = get_store().audit_list(tid, page=page, page_size=page_size, resource_type=resource_type)
    return jsonify({"data": data, "total": total, "page": page, "pageSize": page_size}), 200

# ---------- 批量导入运单 ----------
@app.route("/shipments/import", methods=["POST"])
def import_shipments():
    tid, rid = _tenant(), _request_id()
    owner_id = _owner_id()
    store = get_store()
    if store.idem_get(rid):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "requestId": rid}), 409
    body = request.get_json() or {}
    items = body.get("items") or body.get("data") or []
    if not items or len(items) > 500:
        return jsonify({"code": "BAD_REQUEST", "message": "items 必填且不超过 500 条", "requestId": rid}), 400
    created = store.shipment_batch_import(tid, owner_id or "system", items)
    store.idem_set(rid, "import_batch")
    _human_audit(tid, f"批量导入运单 {len(created)} 条", rid)
    return jsonify({"accepted": True, "count": len(created), "data": created}), 201

# ---------- 监控指标 ----------
@app.route("/metrics")
def metrics():
    store = get_store()
    tid = _tenant()
    all_shipments = store.shipment_list(tid, owner_id=None, page=1, page_size=9999)[0]
    confirmed = sum(1 for s in all_shipments if s.get("status") == 2)
    total = len(all_shipments)
    costs = store.transport_cost_list(tid)
    total_cents = sum(c.get("amountCents", 0) for c in costs)
    return jsonify({
        "cell": "tms",
        "metrics": {
            "shipmentOnTimeRatePct": 92.0 if total else 0,
            "totalShipments": total,
            "confirmedShipments": confirmed,
            "totalTransportCostCents": total_cents,
        },
    }), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8007))
    app.run(host="0.0.0.0", port=port, debug=False)
