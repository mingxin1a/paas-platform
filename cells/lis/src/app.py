"""
LIS 细胞 Flask 应用 - 检验申请→样本→检验结果→报告生成→报告审核。医疗合规：报告可追溯，样本加密，检验师权限。
"""
from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from .store import get_store

def _human_audit(tenant_id: str, operation_desc: str, trace_id: str = "") -> None:
    user_id = request.headers.get("X-User-Id") or request.headers.get("X-Tenant-Id") or "system"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    trace_id = trace_id or request.headers.get("X-Trace-Id") or request.headers.get("X-Request-ID") or ""
    import logging
    logging.getLogger("lis.audit").info(f"【人性化审计】租户 {tenant_id} 用户 {user_id} 在 {ts} {operation_desc}，trace_id={trace_id}")

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

def _tenant() -> str:
    return (request.headers.get("X-Tenant-Id") or "").strip() or "default"

def _request_id() -> str:
    return (request.headers.get("X-Request-ID") or "").strip() or str(uuid.uuid4())

def _technician_id() -> str:
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
    return jsonify({"status": "up", "cell": "lis"}), 200

@app.route("/test-requests", methods=["GET"])
def list_test_requests():
    tenant_id = _tenant()
    patient_id = request.args.get("patientId")
    data = get_store().test_request_list(tenant_id, patient_id=patient_id)
    _human_audit(tenant_id, "查询检验申请列表")
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/test-requests", methods=["POST"])
def create_test_request():
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    if store.idem_get(req_id):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "details": "", "requestId": req_id}), 409
    body = request.get_json() or {}
    r = get_store().test_request_create(tenant_id, body.get("patientId", ""), body.get("visitId", ""), body.get("items", ""))
    store.idem_set(req_id, r["requestId"])
    _human_audit(tenant_id, f"创建检验申请 {r['requestId']}", req_id)
    return jsonify(r), 201

@app.route("/samples", methods=["GET"])
def list_samples():
    tenant_id = _tenant()
    technician_id = _technician_id() or request.args.get("technicianId")
    request_id = request.args.get("requestId")
    data = get_store().sample_list(tenant_id, technician_id=technician_id or None, request_id=request_id)
    _human_audit(tenant_id, "查询样本列表")
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/samples", methods=["POST"])
def create_sample():
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    if store.idem_get(req_id):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "details": "", "requestId": req_id}), 409
    body = request.get_json() or {}
    tech_id = _technician_id() or body.get("technicianId", "")
    s = store.sample_create(tenant_id, body.get("sampleNo", ""), body.get("patientId", ""), body.get("requestId", ""), body.get("specimenType", ""), tech_id)
    store.idem_set(req_id, s["sampleId"])
    store.audit_append(tenant_id, request.headers.get("X-User-Id") or "system", "CREATE", "Sample", s["sampleId"], req_id)
    _human_audit(tenant_id, f"创建样本 {s['sampleId']}", req_id)
    return jsonify(s), 201

@app.route("/samples/<sample_id>", methods=["GET"])
def get_sample(sample_id: str):
    s = get_store().sample_get(_tenant(), sample_id)
    if not s:
        return jsonify({"code": "NOT_FOUND", "message": "样本不存在", "details": "", "requestId": _request_id()}), 404
    _human_audit(_tenant(), f"查询样本 {sample_id}")
    return jsonify(s), 200

@app.route("/samples/<sample_id>/receive", methods=["POST"])
def receive_sample(sample_id: str):
    """样本接收：检验规范要求记录接收时间。"""
    tenant_id = _tenant()
    store = get_store()
    s = store.sample_receive(tenant_id, sample_id)
    if not s:
        return jsonify({"code": "NOT_FOUND", "message": "样本不存在或已接收", "details": "", "requestId": _request_id()}), 404
    store.audit_append(tenant_id, request.headers.get("X-User-Id") or "system", "RECEIVE", "Sample", sample_id, _request_id())
    _human_audit(tenant_id, f"样本接收 {sample_id}")
    return jsonify(s), 200

@app.route("/results", methods=["GET"])
def list_results():
    tenant_id = _tenant()
    technician_id = _technician_id() or request.args.get("technicianId")
    sample_id = request.args.get("sampleId")
    data = get_store().result_list(tenant_id, sample_id=sample_id, technician_id=technician_id or None)
    _human_audit(tenant_id, "查询检验结果列表")
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/results", methods=["POST"])
def create_result():
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    if store.idem_get(req_id):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "details": "", "requestId": req_id}), 409
    body = request.get_json() or {}
    r = store.result_create(tenant_id, body.get("sampleId", ""), body.get("itemCode", ""), body.get("value", ""), body.get("unit", ""))
    store.idem_set(req_id, r["resultId"])
    _human_audit(tenant_id, f"创建检验结果 {r['resultId']}", req_id)
    return jsonify(r), 201

@app.route("/results/<result_id>", methods=["GET"])
def get_result(result_id: str):
    r = get_store().result_get(_tenant(), result_id)
    if not r:
        return jsonify({"code": "NOT_FOUND", "message": "检验结果不存在", "details": "", "requestId": _request_id()}), 404
    _human_audit(_tenant(), f"查询检验结果 {result_id}")
    return jsonify(r), 200

@app.route("/reports", methods=["GET"])
def list_reports():
    tenant_id = _tenant()
    sample_id = request.args.get("sampleId")
    status = request.args.get("status")
    status_int = int(status) if status is not None and str(status).isdigit() else None
    data = get_store().report_list(tenant_id, sample_id=sample_id, status=status_int)
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
    r = store.report_create(tenant_id, sample_id, body.get("requestId", ""), body.get("content", ""))
    store.idem_set(req_id, r["reportId"])
    _human_audit(tenant_id, f"生成报告 {r['reportId']}", req_id)
    return jsonify(r), 201

@app.route("/reports/<report_id>", methods=["GET"])
def get_report(report_id: str):
    r = get_store().report_get(_tenant(), report_id)
    if not r:
        return jsonify({"code": "NOT_FOUND", "message": "报告不存在", "details": "", "requestId": _request_id()}), 404
    return jsonify(r), 200

@app.route("/reports/<report_id>/review", methods=["POST"])
def review_report(report_id: str):
    tenant_id = _tenant()
    store = get_store()
    reviewer_id = _technician_id() or "system"
    r = store.report_review(tenant_id, report_id, reviewer_id)
    if not r:
        return jsonify({"code": "NOT_FOUND", "message": "报告不存在", "details": "", "requestId": _request_id()}), 404
    store.audit_append(tenant_id, reviewer_id, "REVIEW", "Report", report_id, _request_id())
    _human_audit(tenant_id, f"审核报告 {report_id}")
    return jsonify(r), 200

@app.route("/reports/<report_id>/publish", methods=["POST"])
def publish_report(report_id: str):
    """报告发布：检验规范要求审核通过后可发布。"""
    tenant_id = _tenant()
    store = get_store()
    r = store.report_publish(tenant_id, report_id)
    if not r:
        return jsonify({"code": "NOT_FOUND", "message": "报告不存在或未审核，无法发布", "details": "", "requestId": _request_id()}), 404
    store.audit_append(tenant_id, request.headers.get("X-User-Id") or "system", "PUBLISH", "Report", report_id, _request_id())
    _human_audit(tenant_id, f"发布报告 {report_id}")
    return jsonify(r), 200

@app.route("/reports/<report_id>/audits", methods=["GET"])
def list_report_audits(report_id: str):
    tenant_id = _tenant()
    data = get_store().report_audit_list(tenant_id, report_id=report_id)
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/audit-logs", methods=["GET"])
def list_audit_logs():
    """检验规范：不可篡改操作审计日志。"""
    tenant_id = _tenant()
    page = max(1, int(request.args.get("page", 1)))
    page_size = max(1, min(100, int(request.args.get("pageSize", 50))))
    data, total = get_store().audit_list(tenant_id, page=page, page_size=page_size)
    return jsonify({"data": data, "total": total, "page": page, "pageSize": page_size}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8012))
    app.run(host="0.0.0.0", port=port, debug=False)
