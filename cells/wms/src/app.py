"""
WMS 细胞 Flask 应用 - 入库/出库/库位/批次/调拨/盘点/冻结/效期。工业场景；操作日志留存≥1年（模拟配置）。
"""
from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from .store import get_store
from . import event_publisher as _events

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

def _tenant() -> str:
    return (request.headers.get("X-Tenant-Id") or "").strip() or "default"
def _req_id() -> str:
    return (request.headers.get("X-Request-ID") or "").strip() or str(uuid.uuid4())
def _warehouse_id() -> str:
    return (request.headers.get("X-Warehouse-Id") or "").strip()
def _user_id() -> str:
    return (request.headers.get("X-User-Id") or request.headers.get("X-Tenant-Id") or "system").strip()

def _err(code: str, message: str, details: str = "", request_id: str = "") -> tuple:
    body = {"code": code, "message": message, "requestId": request_id or _req_id()}
    if details:
        body["details"] = details
    return (body, 404 if code == "NOT_FOUND" else 400)


def _human_audit(tenant_id: str, operation_desc: str, trace_id: str = "") -> None:
    import logging
    user_id = request.headers.get("X-User-Id") or request.headers.get("X-Tenant-Id") or "system"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    trace_id = trace_id or request.headers.get("X-Trace-Id") or request.headers.get("X-Request-ID") or ""
    logging.getLogger("wms.audit").info(f"【人性化审计】租户 {tenant_id} 用户 {user_id} 在 {ts} {operation_desc}，trace_id={trace_id}")


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
        return jsonify({"code": "SIGNATURE_INVALID", "message": "验签失败", "details": "黑客入侵/验签失败", "requestId": headers.get("X-Request-ID", "")}), 403


@app.before_request
def _start():
    request._start_time = time.time()
@app.after_request
def _resp_time(r):
    if "X-Response-Time" not in r.headers:
        r.headers["X-Response-Time"] = f"{time.time() - getattr(request, '_start_time', 0):.3f}"
    return r

# 工业场景：操作日志留存≥1年（模拟配置）
OPERATION_LOG_RETENTION_DAYS = int(os.environ.get("WMS_OPERATION_LOG_RETENTION_DAYS", "365"))

@app.route("/health")
def health():
    return jsonify({"status": "up", "cell": "wms"}), 200

@app.route("/config/retention")
def config_retention():
    return jsonify({"operationLogRetentionDays": OPERATION_LOG_RETENTION_DAYS}), 200

@app.route("/inventory", methods=["GET"])
def inventory():
    data = get_store().inventory_get(_tenant(), request.args.get("warehouseId"), request.args.get("skuId"))
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/inbound-orders", methods=["GET"])
def inbound_list():
    wh = _warehouse_id() or request.args.get("warehouseId")
    data = get_store().inbound_list(_tenant(), wh, int(request.args.get("status")) if request.args.get("status") else None)
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/inbound-orders/<order_id>", methods=["GET"])
def inbound_get(order_id: str):
    tid, wh = _tenant(), _warehouse_id()
    o = get_store().inbound_get(tid, order_id)
    if not o:
        return jsonify(_err("NOT_FOUND", "入库单不存在", "请检查 orderId", _req_id())), 404
    if wh and o.get("warehouseId") != wh:
        return jsonify(_err("FORBIDDEN", "无权查看该仓库数据", "", _req_id())), 403
    return jsonify(o), 200

@app.route("/inbound-orders", methods=["POST"])
def inbound_create():
    tid, rid = _tenant(), _req_id()
    s = get_store()
    if s.idem_get(rid):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "请求已处理，请勿重复提交", "details": "幂等键已使用", "requestId": rid}), 409
    b = request.get_json() or {}
    wh = (b.get("warehouseId") or "").strip()
    type_code = (b.get("typeCode") or "purchase").strip().lower()
    if type_code not in ("purchase", "production", "return"):
        type_code = "purchase"
    if not wh:
        return jsonify(_err("BAD_REQUEST", "仓库不能为空", "请提供 warehouseId", rid)), 400
    o = s.inbound_create(tid, wh, type_code=type_code, source_order_id=(b.get("sourceOrderId") or "").strip(), erp_order_id=(b.get("erpOrderId") or "").strip())
    s.idem_set(rid, o["orderId"])
    s.audit_append(tid, _user_id(), "CREATE", "InboundOrder", o["orderId"], rid)
    _human_audit(tid, f"创建了入库单 (orderId={o['orderId']})，仓库 {wh}", request.headers.get("X-Trace-Id") or rid)
    return jsonify(o), 201

@app.route("/inbound-orders/export", methods=["GET"])
def export_inbound():
    tid, wh = _tenant(), _warehouse_id() or request.args.get("warehouseId")
    data = get_store().inbound_list(tid, wh, None)
    import csv, io
    from flask import Response
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["orderId", "warehouseId", "typeCode", "status", "createdAt", "updatedAt"])
    for o in data:
        w.writerow([o.get("orderId"), o.get("warehouseId"), o.get("typeCode", "purchase"), o.get("status"), o.get("createdAt"), o.get("updatedAt")])
    return Response(buf.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=inbound_orders.csv"})

@app.route("/inbound-orders/<order_id>/lines", methods=["POST"])
def inbound_add_line(order_id: str):
    tid, rid = _tenant(), _req_id()
    s = get_store()
    if s.idem_get(rid):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "请求已处理，请勿重复提交", "details": "幂等键已使用", "requestId": rid}), 409
    b = request.get_json() or {}
    line = s.inbound_add_line(tid, order_id, b.get("skuId", ""), int(b.get("quantity", 0)), b.get("lotNumber"), b.get("serialNumbers"))
    if not line:
        return jsonify(_err("NOT_FOUND", "入库单不存在", "请检查 orderId", rid)), 404
    s.idem_set(rid, line["lineId"])
    _human_audit(tid, f"入库单 {order_id} 添加行 (lineId={line['lineId']})，SKU {b.get('skuId', '')}", request.headers.get("X-Trace-Id") or rid)
    return jsonify(line), 201

@app.route("/inbound-orders/<order_id>/receive", methods=["POST"])
def inbound_receive(order_id: str):
    tid, rid = _tenant(), _req_id()
    b = request.get_json() or {}
    line_id = b.get("lineId", "")
    qty = int(b.get("receivedQuantity", 0))
    wh = b.get("warehouseId") or (get_store().inbound_orders.get(order_id) or {}).get("warehouseId", "")
    line = get_store().inbound_receive(tid, order_id, line_id, qty, wh, b.get("lotNumber"), idempotent_key=rid)
    if not line:
        return jsonify(_err("NOT_FOUND", "入库单或行不存在", "请检查 orderId、lineId", rid)), 404
    get_store().audit_append(tid, _user_id(), "RECEIVE", "InboundOrder", order_id, rid)
    o = get_store().inbound_get(tid, order_id)
    payload = {"orderId": order_id, "tenantId": tid, "warehouseId": wh, "lineId": line_id, "receivedQuantity": qty, "status": o.get("status", 1), "typeCode": o.get("typeCode", "purchase")}
    if o.get("sourceOrderId"):
        payload["sourceOrderId"] = o["sourceOrderId"]
    if o.get("erpOrderId"):
        payload["erpOrderId"] = o["erpOrderId"]
    _events.publish("wms.inbound.completed", payload, trace_id=request.headers.get("X-Trace-Id") or rid)
    _human_audit(tid, f"入库单 {order_id} 收货，行 {line_id} 数量 {qty}", request.headers.get("X-Trace-Id") or rid)
    return jsonify(line), 200

@app.route("/outbound-orders", methods=["GET"])
def outbound_list():
    wh = _warehouse_id() or request.args.get("warehouseId")
    data = get_store().outbound_list(_tenant(), wh, int(request.args.get("status")) if request.args.get("status") else None)
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/outbound-orders/<order_id>", methods=["GET"])
def outbound_get(order_id: str):
    tid, wh = _tenant(), _warehouse_id()
    o = get_store().outbound_get(tid, order_id)
    if not o:
        return jsonify(_err("NOT_FOUND", "出库单不存在", "请检查 orderId", _req_id())), 404
    if wh and o.get("warehouseId") != wh:
        return jsonify(_err("FORBIDDEN", "无权查看该仓库数据", "", _req_id())), 403
    return jsonify(o), 200

@app.route("/outbound-orders/<order_id>", methods=["PATCH"])
def outbound_patch(order_id: str):
    """联动回写：TMS 签收完成后更新出库单状态。body { "status": 2|3 }，3=已签收。"""
    tid = _tenant()
    b = request.get_json() or {}
    status = b.get("status")
    if status is None:
        return jsonify(_err("BAD_REQUEST", "status 必填", "", "如 2=已发货 3=已签收", _req_id())), 400
    o = get_store().outbound_update_status(tid, order_id, int(status))
    if not o:
        return jsonify(_err("NOT_FOUND", "出库单不存在", "请检查 orderId", _req_id())), 404
    return jsonify(o), 200

@app.route("/outbound-orders", methods=["POST"])
def outbound_create():
    tid, rid = _tenant(), _req_id()
    s = get_store()
    if s.idem_get(rid):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "请求已处理，请勿重复提交", "details": "幂等键已使用", "requestId": rid}), 409
    b = request.get_json() or {}
    wh = (b.get("warehouseId") or "").strip()
    type_code = (b.get("typeCode") or "sales").strip().lower()
    if type_code not in ("sales", "picking", "transfer"):
        type_code = "sales"
    if not wh:
        return jsonify(_err("BAD_REQUEST", "仓库不能为空", "请提供 warehouseId", rid)), 400
    o = s.outbound_create(tid, wh, type_code=type_code, source_order_id=(b.get("sourceOrderId") or "").strip(), erp_order_id=(b.get("erpOrderId") or "").strip())
    s.idem_set(rid, o["orderId"])
    s.audit_append(tid, _user_id(), "CREATE", "OutboundOrder", o["orderId"], rid)
    _human_audit(tid, f"创建了出库单 (orderId={o['orderId']})，仓库 {wh}", request.headers.get("X-Trace-Id") or rid)
    return jsonify(o), 201

@app.route("/outbound-orders/export", methods=["GET"])
def export_outbound():
    tid, wh = _tenant(), _warehouse_id() or request.args.get("warehouseId")
    data = get_store().outbound_list(tid, wh, None)
    import csv, io
    from flask import Response
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["orderId", "warehouseId", "typeCode", "status", "createdAt", "updatedAt"])
    for o in data:
        w.writerow([o.get("orderId"), o.get("warehouseId"), o.get("typeCode", "sales"), o.get("status"), o.get("createdAt"), o.get("updatedAt")])
    return Response(buf.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=outbound_orders.csv"})

@app.route("/outbound-orders/<order_id>/lines", methods=["POST"])
def outbound_add_line(order_id: str):
    tid, rid = _tenant(), _req_id()
    s = get_store()
    if s.idem_get(rid):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "details": "", "requestId": rid}), 409
    b = request.get_json() or {}
    line = s.outbound_add_line(tid, order_id, b.get("skuId", ""), int(b.get("quantity", 0)))
    if not line:
        return jsonify({"code": "NOT_FOUND", "message": "出库单不存在", "details": "", "requestId": rid}), 404
    s.idem_set(rid, line["lineId"])
    _human_audit(tid, f"出库单 {order_id} 添加行 (lineId={line['lineId']})，SKU {b.get('skuId', '')}", request.headers.get("X-Trace-Id") or rid)
    return jsonify(line), 201

@app.route("/outbound-orders/<order_id>/ship", methods=["POST"])
def outbound_ship(order_id: str):
    tid, rid = _tenant(), _req_id()
    b = request.get_json() or {}
    line_id = b.get("lineId", "")
    qty = int(b.get("pickedQuantity", 0))
    wh = b.get("warehouseId") or (get_store().outbound_orders.get(order_id) or {}).get("warehouseId", "")
    line = get_store().outbound_ship(tid, order_id, line_id, qty, wh, idempotent_key=rid)
    if not line:
        return jsonify(_err("BUSINESS_RULE_VIOLATION", "出库失败", "出库数量超出可用库存或出库单/行不存在，请核对库存", rid)), 400
    get_store().audit_append(tid, _user_id(), "SHIP", "OutboundOrder", order_id, rid)
    o = get_store().outbound_get(tid, order_id)
    payload = {"orderId": order_id, "tenantId": tid, "warehouseId": wh, "lineId": line_id, "pickedQuantity": qty, "status": o.get("status", 1), "typeCode": o.get("typeCode", "sales")}
    if o.get("erpOrderId"):
        payload["erpOrderId"] = o["erpOrderId"]
    if o.get("sourceOrderId"):
        payload["sourceOrderId"] = o["sourceOrderId"]
    _events.publish("wms.outbound.completed", payload, trace_id=request.headers.get("X-Trace-Id") or rid)
    _human_audit(tid, f"出库单 {order_id} 发货，行 {line_id} 数量 {qty}", request.headers.get("X-Trace-Id") or rid)
    return jsonify(line), 200

@app.route("/locations", methods=["GET"])
def locations_list():
    data = get_store().location_list(_tenant(), request.args.get("warehouseId"))
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/locations/<location_id>", methods=["GET"])
def location_get(location_id: str):
    loc = get_store().location_get(_tenant(), location_id)
    if not loc:
        return jsonify({"code": "NOT_FOUND", "message": "库位不存在", "details": "", "requestId": _req_id()}), 404
    return jsonify(loc), 200

@app.route("/locations", methods=["POST"])
def location_create():
    tid, rid = _tenant(), _req_id()
    s = get_store()
    if s.idem_get(rid):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "details": "", "requestId": rid}), 409
    b = request.get_json() or {}
    loc_id = b.get("locationId", "")
    if not loc_id:
        return jsonify({"code": "BAD_REQUEST", "message": "locationId 必填", "details": "", "requestId": rid}), 400
    loc = s.location_create(tid, b.get("warehouseId", ""), loc_id, b.get("zoneCode", ""), b.get("aisle", ""), b.get("level", ""), b.get("position", ""))
    s.idem_set(rid, loc_id)
    _human_audit(tid, f"创建了库位 {loc_id}，仓库 {b.get('warehouseId', '')}", request.headers.get("X-Trace-Id") or rid)
    return jsonify(loc), 201

@app.route("/lots", methods=["GET"])
def lots_list():
    data = get_store().lot_list(_tenant(), request.args.get("skuId"), request.args.get("lotNumber"), request.args.get("warehouseId"))
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/lots/<lot_id>", methods=["GET"])
def lot_get(lot_id: str):
    lot = get_store().lot_get(_tenant(), lot_id)
    if not lot:
        return jsonify({"code": "NOT_FOUND", "message": "批次不存在", "details": "", "requestId": _req_id()}), 404
    return jsonify(lot), 200

@app.route("/lots/fifo", methods=["GET"])
def lots_fifo():
    wh = request.args.get("warehouseId", "")
    sku = request.args.get("skuId", "")
    qty = int(request.args.get("quantity", 1))
    data = get_store().lot_fifo(_tenant(), wh, sku, qty)
    return jsonify({"data": data}), 200

# ---------- 调拨（幂等） ----------
@app.route("/transfers", methods=["GET"])
def transfers_list():
    data = get_store().transfer_list(_tenant())
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/transfers", methods=["POST"])
def transfer_create():
    tid, rid = _tenant(), _req_id()
    s = get_store()
    if s.idem_get(rid):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "details": "", "requestId": rid}), 409
    b = request.get_json() or {}
    from_wh = (b.get("fromWarehouseId") or "").strip()
    to_wh = (b.get("toWarehouseId") or "").strip()
    sku = (b.get("skuId") or "").strip()
    qty = int(b.get("quantity", 0))
    if not from_wh or not to_wh or not sku or qty <= 0:
        return jsonify({"code": "BAD_REQUEST", "message": "fromWarehouseId、toWarehouseId、skuId、quantity 必填且 quantity>0", "details": "", "requestId": rid}), 400
    t = s.transfer_create(tid, from_wh, to_wh, sku, qty, idempotent_key=rid)
    if not t:
        return jsonify({"code": "BUSINESS_RULE_VIOLATION", "message": "源仓库可用库存不足", "details": "", "requestId": rid}), 400
    s.idem_set(rid, t["transferId"])
    _human_audit(tid, f"创建调拨 {t['transferId']}", rid)
    return jsonify(t), 201

# ---------- 盘点（支持批量 1000+ 物料） ----------
@app.route("/cycle-counts", methods=["GET"])
def cycle_counts_list():
    data = get_store().cycle_count_list(_tenant(), request.args.get("warehouseId"))
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/cycle-counts/batch", methods=["POST"])
def cycle_count_batch():
    tid, rid = _tenant(), _req_id()
    s = get_store()
    if s.idem_get(rid):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "details": "", "requestId": rid}), 409
    b = request.get_json() or {}
    wh = (b.get("warehouseId") or "").strip()
    items = b.get("items") or b.get("data") or []
    if not wh or not items:
        return jsonify({"code": "BAD_REQUEST", "message": "warehouseId、items 必填", "details": "", "requestId": rid}), 400
    if len(items) > 2000:
        return jsonify({"code": "BAD_REQUEST", "message": "单次盘点不超过 2000 条", "details": "", "requestId": rid}), 400
    created = s.cycle_count_batch(tid, wh, items)
    s.idem_set(rid, "cycle_count_batch")
    _human_audit(tid, f"批量盘点 {len(created)} 条", rid)
    return jsonify({"accepted": True, "count": len(created), "data": created}), 201

# ---------- 库存冻结/解冻 ----------
@app.route("/inventory/freeze", methods=["POST"])
def inventory_freeze():
    tid, rid = _tenant(), _req_id()
    b = request.get_json() or {}
    wh = (b.get("warehouseId") or "").strip()
    sku = (b.get("skuId") or "").strip()
    qty = int(b.get("quantity", 0))
    if not wh or not sku or qty <= 0:
        return jsonify({"code": "BAD_REQUEST", "message": "warehouseId、skuId、quantity 必填且 quantity>0", "details": "", "requestId": rid}), 400
    f = get_store().freeze_add(tid, wh, sku, qty, b.get("reason", ""))
    if not f:
        return jsonify({"code": "BUSINESS_RULE_VIOLATION", "message": "可用库存不足", "details": "", "requestId": rid}), 400
    _human_audit(tid, f"冻结库存 {sku} 数量 {qty}", rid)
    return jsonify(f), 201

@app.route("/inventory/freeze/<freeze_id>/release", methods=["POST"])
def inventory_freeze_release(freeze_id: str):
    f = get_store().freeze_release(_tenant(), freeze_id)
    if not f:
        return jsonify({"code": "NOT_FOUND", "message": "冻结记录不存在", "details": "", "requestId": _req_id()}), 404
    _human_audit(_tenant(), f"解冻 {freeze_id}")
    return jsonify({"released": True, "freezeId": freeze_id}), 200

# ---------- 效期预警 ----------
@app.route("/alerts/expiry", methods=["GET"])
def alerts_expiry():
    days = int(request.args.get("daysAhead", 30))
    data = get_store().expiry_alert_list(_tenant(), days_ahead=days)
    return jsonify({"data": data, "total": len(data), "daysAhead": days}), 200

# ---------- 库存预警（低于安全库存） ----------
@app.route("/alerts/stock", methods=["GET"])
def alerts_stock():
    wh = _warehouse_id() or request.args.get("warehouseId")
    data = get_store().stock_alert_list(_tenant(), warehouse_id=wh)
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/safety-stock", methods=["POST"])
def set_safety_stock():
    tid, rid = _tenant(), _req_id()
    b = request.get_json() or {}
    wh = (b.get("warehouseId") or "").strip()
    sku = (b.get("skuId") or "").strip()
    min_qty = int(b.get("minQuantity", 0))
    if not wh or not sku:
        return jsonify(_err("BAD_REQUEST", "warehouseId、skuId 必填", "", rid)), 400
    get_store().set_safety_stock(tid, wh, sku, min_qty)
    return jsonify({"warehouseId": wh, "skuId": sku, "minQuantity": min_qty}), 200

# ---------- 批次/序列号追溯 ----------
@app.route("/trace/serial/<serial_number>", methods=["GET"])
def trace_serial(serial_number: str):
    data = get_store().trace_by_serial(_tenant(), serial_number)
    return jsonify({"data": data, "serialNumber": serial_number}), 200

# ---------- 审计日志 ----------
@app.route("/audit-logs", methods=["GET"])
def list_audit_logs():
    tid = _tenant()
    page = max(1, int(request.args.get("page", 1)))
    page_size = max(1, min(100, int(request.args.get("pageSize", 50))))
    resource_type = (request.args.get("resourceType") or "").strip() or None
    data, total = get_store().audit_list(tid, page=page, page_size=page_size, resource_type=resource_type)
    return jsonify({"data": data, "total": total, "page": page, "pageSize": page_size}), 200


# ---------- 波次拣货 ----------
@app.route("/waves", methods=["GET"])
def waves_list():
    data = get_store().wave_list(_tenant(), request.args.get("warehouseId"), int(request.args.get("status")) if request.args.get("status") else None)
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/waves", methods=["POST"])
def waves_create():
    tid, rid = _tenant(), _req_id()
    s = get_store()
    if s.idem_get(rid):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "details": "", "requestId": rid}), 409
    b = request.get_json() or {}
    wh = (b.get("warehouseId") or "").strip()
    order_ids = b.get("outboundOrderIds") or b.get("orderIds") or []
    if not wh or not order_ids:
        return jsonify({"code": "BAD_REQUEST", "message": "warehouseId、outboundOrderIds 必填", "details": "", "requestId": rid}), 400
    w = s.wave_create(tid, wh, order_ids)
    s.idem_set(rid, w["waveId"])
    _human_audit(tid, f"创建波次 {w['waveId']}", rid)
    return jsonify(w), 201

@app.route("/waves/<wave_id>/picks", methods=["GET"])
def wave_picks(wave_id: str):
    data = get_store().wave_get_picks(_tenant(), wave_id)
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/waves/<wave_id>/confirm-pick", methods=["POST"])
def wave_confirm_pick(wave_id: str):
    tid, rid = _tenant(), _req_id()
    b = request.get_json() or {}
    pick_line_id = (b.get("pickLineId") or "").strip()
    picked_qty = int(b.get("pickedQuantity", 0))
    if not pick_line_id:
        return jsonify({"code": "BAD_REQUEST", "message": "pickLineId 必填", "details": "", "requestId": rid}), 400
    line = get_store().wave_confirm_pick(tid, wave_id, pick_line_id, picked_qty)
    if not line:
        return jsonify({"code": "NOT_FOUND", "message": "波次或拣货行不存在", "details": "", "requestId": rid}), 404
    return jsonify(line), 200

# ---------- 看板 ----------
@app.route("/board", methods=["GET"])
def board():
    data = get_store().board_data(_tenant())
    return jsonify(data), 200

# ---------- 扫码出入库（模拟接口） ----------
@app.route("/scan/inbound", methods=["POST"])
def scan_inbound():
    body = request.get_json() or {}
    order_id = body.get("orderId")
    barcode = body.get("barcode")
    qty = int(body.get("quantity", 1))
    if not order_id or not barcode:
        return jsonify({"code": "BAD_REQUEST", "message": "orderId、barcode 必填", "details": "", "requestId": _req_id()}), 400
    o = get_store().inbound_get(_tenant(), order_id)
    if not o:
        return jsonify({"code": "NOT_FOUND", "message": "入库单不存在", "details": "", "requestId": _req_id()}), 404
    lines = o.get("lines") or []
    line_id = next((l.get("lineId") for l in lines if l.get("skuId") == barcode or l.get("lotNumber") == barcode), None)
    if not line_id and lines:
        line_id = lines[0].get("lineId")
    if not line_id:
        return jsonify({"code": "BAD_REQUEST", "message": "未匹配到入库行或入库单无明细", "details": "", "requestId": _req_id()}), 400
    wh = o.get("warehouseId", "")
    line = get_store().inbound_receive(_tenant(), order_id, line_id, qty, wh, None, _req_id())
    if not line:
        return jsonify({"code": "NOT_FOUND", "message": "入库单或行不存在", "details": "", "requestId": _req_id()}), 404
    return jsonify({"accepted": True, "orderId": order_id, "lineId": line_id, "receivedQuantity": qty}), 200

@app.route("/scan/outbound", methods=["POST"])
def scan_outbound():
    body = request.get_json() or {}
    order_id = body.get("orderId")
    barcode = body.get("barcode")
    qty = int(body.get("quantity", 1))
    if not order_id or not barcode:
        return jsonify({"code": "BAD_REQUEST", "message": "orderId、barcode 必填", "details": "", "requestId": _req_id()}), 400
    o = get_store().outbound_get(_tenant(), order_id)
    if not o:
        return jsonify({"code": "NOT_FOUND", "message": "出库单不存在", "details": "", "requestId": _req_id()}), 404
    lines = o.get("lines") or []
    line_id = next((l.get("lineId") for l in lines if l.get("skuId") == barcode), None)
    if not line_id and lines:
        line_id = lines[0].get("lineId")
    if not line_id:
        return jsonify({"code": "BAD_REQUEST", "message": "未匹配到出库行或出库单无明细", "details": "", "requestId": _req_id()}), 400
    wh = o.get("warehouseId", "")
    line = get_store().outbound_ship(_tenant(), order_id, line_id, qty, wh, _req_id())
    if not line:
        return jsonify({"code": "BUSINESS_RULE_VIOLATION", "message": "出库数量超出可用库存", "details": "", "requestId": _req_id()}), 400
    return jsonify({"accepted": True, "orderId": order_id, "lineId": line_id, "pickedQuantity": qty}), 200

# ---------- 监控指标（仓储版） ----------
@app.route("/metrics")
def metrics():
    store = get_store()
    tid = _tenant()
    expiry = store.expiry_alert_list(tid, 30)
    counts = store.cycle_count_list(tid)
    transfers = store.transfer_list(tid)
    return jsonify({
        "cell": "wms",
        "metrics": {
            "transferCount": len(transfers),
            "cycleCountTotal": len(counts),
            "expiryAlertCount": len(expiry),
        },
    }), 200

if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8003")))
