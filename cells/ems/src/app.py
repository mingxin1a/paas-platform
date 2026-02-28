"""
EMS 细胞 Flask 应用 - 能耗采集→能耗统计→能耗分析→能耗预警→能耗报表→节能建议全流程。行业合规：数据留存≥3年，操作日志不可篡改。
"""
from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from .store import get_store

try:
    from . import event_publisher as _events
except ImportError:
    _events = None

# 行业合规：能耗数据留存≥3年（模拟配置）
ENERGY_DATA_RETENTION_DAYS = int(os.environ.get("EMS_ENERGY_DATA_RETENTION_DAYS", "1095"))

def _human_audit(tenant_id: str, operation_desc: str, trace_id: str = "") -> None:
    user_id = request.headers.get("X-User-Id") or request.headers.get("X-Tenant-Id") or "system"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    trace_id = trace_id or request.headers.get("X-Trace-Id") or request.headers.get("X-Request-ID") or ""
    import logging
    logging.getLogger("ems.audit").info(f"【人性化审计】租户 {tenant_id} 用户 {user_id} 在 {ts} {operation_desc}，trace_id={trace_id}")

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

def _tenant() -> str:
    return (request.headers.get("X-Tenant-Id") or "").strip() or "default"

def _request_id() -> str:
    return (request.headers.get("X-Request-ID") or "").strip() or str(uuid.uuid4())

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
    return jsonify({"status": "up", "cell": "ems"}), 200

@app.route("/config/retention")
def config_retention():
    """行业合规：能耗数据留存天数（≥3年模拟）"""
    return jsonify({"energyDataRetentionDays": ENERGY_DATA_RETENTION_DAYS}), 200

@app.route("/consumption-records", methods=["GET"])
def list_consumption():
    tenant_id = _tenant()
    meter_id = request.args.get("meterId")
    page = max(1, int(request.args.get("page", 1)))
    page_size = max(1, min(500, int(request.args.get("pageSize", 20))))
    data, total = get_store().consumption_list(tenant_id, meter_id=meter_id, page=page, page_size=page_size)
    _human_audit(tenant_id, "查询能耗记录列表")
    return jsonify({"data": data, "total": total, "page": page, "pageSize": page_size}), 200

@app.route("/consumption-records", methods=["POST"])
def create_consumption():
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    if store.idem_get(req_id):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "requestId": req_id}), 409
    body = request.get_json() or {}
    r = store.consumption_create(tenant_id, body.get("meterId", ""), float(body.get("value", 0)), body.get("unit", "kWh"), body.get("recordTime", ""))
    store.idem_set(req_id, r["recordId"])
    store.audit_append(tenant_id, request.headers.get("X-User-Id") or "system", "CREATE", "ConsumptionRecord", r["recordId"], req_id)
    _human_audit(tenant_id, f"创建能耗记录 {r['recordId']}", req_id)
    if _events:
        _events.publish("ems.consumption.recorded", {"recordId": r["recordId"], "tenantId": tenant_id, "meterId": r.get("meterId"), "value": r.get("value"), "unit": r.get("unit")}, trace_id=req_id)
    return jsonify(r), 201

@app.route("/consumption-records/<record_id>", methods=["GET"])
def get_consumption(record_id: str):
    r = get_store().consumption_get(_tenant(), record_id)
    if not r:
        return jsonify({"code": "NOT_FOUND", "message": "能耗记录不存在", "details": "", "requestId": _request_id()}), 404
    _human_audit(_tenant(), f"查询能耗记录 {record_id}")
    return jsonify(r), 200

@app.route("/stats", methods=["GET"])
def consumption_stats():
    """能耗统计：按日/周/月/年；符合工业能耗规范报表。"""
    tenant_id = _tenant()
    period = request.args.get("period", "day")
    if period not in ("day", "week", "month", "year"):
        period = "day"
    from_date = request.args.get("fromDate", "")
    to_date = request.args.get("toDate", "")
    data = get_store().consumption_stats(tenant_id, period, from_date=from_date, to_date=to_date)
    return jsonify({"data": data, "period": period}), 200

@app.route("/alerts", methods=["GET"])
def list_alerts():
    """能耗预警列表（可对接实时推送）。"""
    tenant_id = _tenant()
    ack = request.args.get("acknowledged")
    acknowledged = None if ack is None else ack == "1"
    data = get_store().alert_list(tenant_id, acknowledged=acknowledged)
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/alerts", methods=["POST"])
def create_alert():
    """能耗异常预警（阈值/异常等）；发布事件供下游消费。"""
    tenant_id = _tenant()
    body = request.get_json() or {}
    store = get_store()
    a = store.alert_add(tenant_id, body.get("meterId", ""), body.get("alertType", "anomaly"), body.get("thresholdValue"), body.get("actualValue"))
    store.audit_append(tenant_id, request.headers.get("X-User-Id") or "system", "CREATE", "Alert", a["alertId"], _request_id())
    if _events:
        _events.publish("ems.alert.raised", {"alertId": a["alertId"], "tenantId": tenant_id, "meterId": a.get("meterId"), "alertType": a.get("alertType")}, trace_id=_request_id())
    return jsonify(a), 201

@app.route("/analysis", methods=["GET"])
def consumption_analysis():
    """能耗分析：同比/环比、趋势、异常检测，适配工业能耗监管。"""
    tenant_id = _tenant()
    period = request.args.get("period", "month")
    if period not in ("day", "week", "month", "year"):
        period = "month"
    from_date = request.args.get("fromDate", "")
    to_date = request.args.get("toDate", "")
    data = get_store().consumption_analysis(tenant_id, period, from_date=from_date, to_date=to_date)
    _human_audit(tenant_id, "查询能耗分析")
    return jsonify(data), 200

@app.route("/reports", methods=["GET"])
def energy_reports():
    """能耗报表：按周期生成报表（工业监管报表）。"""
    tenant_id = _tenant()
    period = request.args.get("period", "month")
    period_key = request.args.get("periodKey", "")
    if not period_key:
        stats = get_store().consumption_stats(tenant_id, period)
        return jsonify({"data": [get_store().report_generate(tenant_id, period, s.get("period", "")) for s in stats], "period": period}), 200
    data = get_store().report_generate(tenant_id, period, period_key)
    return jsonify(data), 200

@app.route("/suggestions", methods=["GET"])
def energy_suggestions():
    """节能建议：基于预警与统计给出建议。"""
    tenant_id = _tenant()
    limit = max(1, min(50, int(request.args.get("limit", 10))))
    data = get_store().suggestions_list(tenant_id, limit=limit)
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/audit-logs", methods=["GET"])
def list_audit_logs():
    """工业合规：不可篡改操作审计日志。"""
    tenant_id = _tenant()
    page = max(1, int(request.args.get("page", 1)))
    page_size = max(1, min(100, int(request.args.get("pageSize", 50))))
    resource_type = request.args.get("resourceType", "").strip() or None
    data, total = get_store().audit_list(tenant_id, page=page, page_size=page_size, resource_type=resource_type)
    return jsonify({"data": data, "total": total, "page": page, "pageSize": page_size}), 200

@app.route("/export", methods=["GET"])
def export_records():
    """能耗数据导出，符合监管要求。"""
    tenant_id = _tenant()
    from_date = request.args.get("fromDate", "")
    to_date = request.args.get("toDate", "")
    limit = min(50000, max(1, int(request.args.get("limit", 10000))))
    data = get_store().export_records(tenant_id, from_date=from_date, to_date=to_date, limit=limit)
    get_store().audit_append(tenant_id, request.headers.get("X-User-Id") or "system", "EXPORT", "ConsumptionRecord", "", _request_id())
    _human_audit(tenant_id, f"导出能耗数据 {len(data)} 条")
    return jsonify({"data": data, "count": len(data), "retentionDays": ENERGY_DATA_RETENTION_DAYS}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8010))
    app.run(host="0.0.0.0", port=port, debug=False)
