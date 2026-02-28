"""
LIMS 细胞 Flask 应用 - 样品→实验任务→实验数据→实验报告→数据溯源。行业合规：数据留存≥5年，溯源可审计。
"""
from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from .store import get_store

# 行业合规：实验数据留存≥5年（模拟）
LAB_DATA_RETENTION_DAYS = int(os.environ.get("LIMS_LAB_DATA_RETENTION_DAYS", "1825"))

def _human_audit(tenant_id: str, operation_desc: str, trace_id: str = "") -> None:
    user_id = request.headers.get("X-User-Id") or request.headers.get("X-Tenant-Id") or "system"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    trace_id = trace_id or request.headers.get("X-Trace-Id") or request.headers.get("X-Request-ID") or ""
    import logging
    logging.getLogger("lims.audit").info(f"【人性化审计】租户 {tenant_id} 用户 {user_id} 在 {ts} {operation_desc}，trace_id={trace_id}")

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

def _tenant() -> str:
    return (request.headers.get("X-Tenant-Id") or "").strip() or "default"

def _request_id() -> str:
    return (request.headers.get("X-Request-ID") or "").strip() or str(uuid.uuid4())

def _operator_id() -> str:
    return (request.headers.get("X-User-Id") or "").strip()

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
        return jsonify({"code": "SIGNATURE_INVALID", "message": "验签失败", "requestId": headers.get("X-Request-ID", "")}), 403

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
    return jsonify({"status": "up", "cell": "lims"}), 200

@app.route("/config/retention")
def config_retention():
    """行业合规：实验数据留存天数（≥5年模拟）"""
    return jsonify({"labDataRetentionDays": LAB_DATA_RETENTION_DAYS}), 200

@app.route("/samples", methods=["GET"])
def list_samples():
    tenant_id = _tenant()
    operator_id = _operator_id() or request.args.get("operatorId")
    data = get_store().sample_list(tenant_id, operator_id=operator_id or None)
    _human_audit(tenant_id, "查询样品列表")
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/samples", methods=["POST"])
def create_sample():
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    if store.idem_get(req_id):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "details": "", "requestId": req_id}), 409
    body = request.get_json() or {}
    op_id = _operator_id() or body.get("operatorId", "")
    s = store.sample_create(tenant_id, body.get("sampleNo", ""), body.get("batchId", ""), body.get("testType", ""), op_id)
    store.idem_set(req_id, s["sampleId"])
    _human_audit(tenant_id, f"创建样品 {s['sampleId']}", req_id)
    return jsonify(s), 201

@app.route("/samples/<sample_id>", methods=["GET"])
def get_sample(sample_id: str):
    s = get_store().sample_get(_tenant(), sample_id)
    if not s:
        return jsonify({"code": "NOT_FOUND", "message": "样品不存在", "requestId": _request_id()}), 404
    _human_audit(_tenant(), f"查询样品 {sample_id}")
    return jsonify(s), 200

@app.route("/samples/<sample_id>/receive", methods=["POST"])
def receive_sample(sample_id: str):
    """样品接收：实验室合规要求记录接收时间。"""
    tenant_id = _tenant()
    store = get_store()
    s = store.sample_receive(tenant_id, sample_id)
    if not s:
        return jsonify({"code": "NOT_FOUND", "message": "样品不存在或已接收", "requestId": _request_id()}), 404
    store.trace_add(tenant_id, "sample", sample_id, "receive", _operator_id())
    _human_audit(tenant_id, f"样品接收 {sample_id}")
    return jsonify(s), 200

@app.route("/results", methods=["GET"])
def list_results():
    tenant_id = _tenant()
    sample_id = request.args.get("sampleId")
    data = get_store().result_list(tenant_id, sample_id=sample_id)
    _human_audit(tenant_id, "查询结果列表")
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/results", methods=["POST"])
def create_result():
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    if store.idem_get(req_id):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "details": "", "requestId": req_id}), 409
    body = request.get_json() or {}
    r = store.result_create(tenant_id, body.get("sampleId", ""), body.get("testItem", ""), body.get("value", ""), body.get("unit", ""))
    store.idem_set(req_id, r["resultId"])
    _human_audit(tenant_id, f"创建结果 {r['resultId']}", req_id)
    return jsonify(r), 201

@app.route("/results/<result_id>", methods=["GET"])
def get_result(result_id: str):
    r = get_store().result_get(_tenant(), result_id)
    if not r:
        return jsonify({"code": "NOT_FOUND", "message": "结果不存在", "requestId": _request_id()}), 404
    _human_audit(_tenant(), f"查询结果 {result_id}")
    return jsonify(r), 200

@app.route("/tasks", methods=["GET"])
def list_tasks():
    tenant_id = _tenant()
    sample_id = request.args.get("sampleId")
    operator_id = _operator_id() or request.args.get("operatorId")
    data = get_store().task_list(tenant_id, sample_id=sample_id, operator_id=operator_id or None)
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/tasks", methods=["POST"])
def create_task():
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    if store.idem_get(req_id):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "details": "", "requestId": req_id}), 409
    body = request.get_json() or {}
    sample_id = (body.get("sampleId") or "").strip()
    if not sample_id:
        return jsonify({"code": "BAD_REQUEST", "message": "sampleId 必填", "details": "", "requestId": req_id}), 400
    t = store.task_create(tenant_id, sample_id, body.get("taskType", ""), _operator_id() or body.get("operatorId", ""))
    store.idem_set(req_id, t["taskId"])
    store.trace_add(tenant_id, "task", t["taskId"], "create", _operator_id())
    _human_audit(tenant_id, f"创建实验任务 {t['taskId']}", req_id)
    return jsonify(t), 201

@app.route("/tasks/<task_id>", methods=["GET"])
def get_task(task_id: str):
    t = get_store().task_get(_tenant(), task_id)
    if not t:
        return jsonify({"code": "NOT_FOUND", "message": "任务不存在", "requestId": _request_id()}), 404
    return jsonify(t), 200

@app.route("/experiment-data", methods=["GET"])
def list_experiment_data():
    tenant_id = _tenant()
    task_id = request.args.get("taskId")
    sample_id = request.args.get("sampleId")
    data = get_store().experiment_data_list(tenant_id, task_id=task_id, sample_id=sample_id)
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/experiment-data", methods=["POST"])
def create_experiment_data():
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    if store.idem_get(req_id):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "details": "", "requestId": req_id}), 409
    body = request.get_json() or {}
    task_id = (body.get("taskId") or "").strip()
    sample_id = (body.get("sampleId") or "").strip()
    if not task_id or not sample_id:
        return jsonify({"code": "BAD_REQUEST", "message": "taskId、sampleId 必填", "details": "", "requestId": req_id}), 400
    d = store.experiment_data_add(tenant_id, task_id, sample_id, body.get("dataValue", ""))
    store.idem_set(req_id, d["dataId"])
    store.trace_add(tenant_id, "experiment_data", d["dataId"], "create", _operator_id())
    _human_audit(tenant_id, f"记录实验数据 {d['dataId']}", req_id)
    return jsonify(d), 201

@app.route("/reports", methods=["GET"])
def list_reports():
    tenant_id = _tenant()
    sample_id = request.args.get("sampleId")
    data = get_store().report_list(tenant_id, sample_id=sample_id)
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/reports", methods=["POST"])
def create_report():
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    if store.idem_get(req_id):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "details": "", "requestId": req_id}), 409
    body = request.get_json() or {}
    sample_id = (body.get("sampleId") or "").strip()
    if not sample_id:
        return jsonify({"code": "BAD_REQUEST", "message": "sampleId 必填", "details": "", "requestId": req_id}), 400
    r = store.report_create(tenant_id, sample_id, body.get("taskId", ""), body.get("content", ""))
    store.idem_set(req_id, r["reportId"])
    store.trace_add(tenant_id, "report", r["reportId"], "create", _operator_id())
    _human_audit(tenant_id, f"创建实验报告 {r['reportId']}", req_id)
    return jsonify(r), 201

@app.route("/reports/<report_id>", methods=["GET"])
def get_report(report_id: str):
    r = get_store().report_get(_tenant(), report_id)
    if not r:
        return jsonify({"code": "NOT_FOUND", "message": "报告不存在", "requestId": _request_id()}), 404
    return jsonify(r), 200

@app.route("/reports/<report_id>/review", methods=["POST"])
def review_report(report_id: str):
    """报告审核：实验室合规要求审核后可归档。"""
    tenant_id = _tenant()
    store = get_store()
    reviewer_id = _operator_id() or request.headers.get("X-User-Id") or "system"
    r = store.report_review(tenant_id, report_id, reviewer_id)
    if not r:
        return jsonify({"code": "NOT_FOUND", "message": "报告不存在", "requestId": _request_id()}), 404
    store.trace_add(tenant_id, "report", report_id, "review", reviewer_id)
    _human_audit(tenant_id, f"审核报告 {report_id}")
    return jsonify(r), 200

@app.route("/reports/<report_id>/archive", methods=["POST"])
def archive_report(report_id: str):
    """报告归档：实验室合规要求审核通过后可归档。"""
    tenant_id = _tenant()
    store = get_store()
    r = store.report_archive(tenant_id, report_id)
    if not r:
        return jsonify({"code": "NOT_FOUND", "message": "报告不存在或未审核，无法归档", "requestId": _request_id()}), 404
    store.trace_add(tenant_id, "report", report_id, "archive", _operator_id())
    _human_audit(tenant_id, f"归档报告 {report_id}")
    return jsonify(r), 200

@app.route("/trace", methods=["GET"])
def list_trace():
    """数据溯源：按实体类型、实体ID查询操作记录，可审计。"""
    tenant_id = _tenant()
    entity_type = request.args.get("entityType")
    entity_id = request.args.get("entityId")
    data = get_store().trace_list(tenant_id, entity_type=entity_type, entity_id=entity_id)
    return jsonify({"data": data, "total": len(data)}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8013))
    app.run(host="0.0.0.0", port=port, debug=False)
