"""HRM 细胞 Flask 应用 - 员工、部门、请假。遵循《接口设计说明书》。01 5.2/00 #5 验签；01 4.4 人性化审计。"""
from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from .store import get_store

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

def _tenant(): return (request.headers.get("X-Tenant-Id") or "").strip() or "default"
def _req_id(): return (request.headers.get("X-Request-ID") or "").strip() or str(uuid.uuid4())


def _human_audit(tenant_id: str, operation_desc: str, trace_id: str = "") -> None:
    import logging
    user_id = request.headers.get("X-User-Id") or request.headers.get("X-Tenant-Id") or "system"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    trace_id = trace_id or request.headers.get("X-Trace-Id") or request.headers.get("X-Request-ID") or ""
    logging.getLogger("hrm.audit").info(f"【人性化审计】租户 {tenant_id} 用户 {user_id} 在 {ts} {operation_desc}，trace_id={trace_id}")


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
def _start(): request._start_time = time.time()
@app.after_request
def _resp(r):
    if "X-Response-Time" not in r.headers:
        r.headers["X-Response-Time"] = f"{time.time() - getattr(request, '_start_time', 0):.3f}"
    return r

@app.route("/health")
def health():
    return jsonify({"status": "up", "cell": "hrm"}), 200

@app.route("/employees", methods=["GET"])
def employees_list():
    data = get_store().employee_list(_tenant())
    return jsonify({"data": data, "total": len(data)}), 200
@app.route("/employees", methods=["POST"])
def employees_create():
    tid, rid = _tenant(), _req_id()
    s = get_store()
    if s.idem_get(rid):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "details": "", "requestId": rid}), 409
    b = request.get_json() or {}
    e = s.employee_create(tid, b.get("name", ""), b.get("departmentId", ""), b.get("employeeNo", ""))
    s.idem_set(rid, e["employeeId"])
    _human_audit(tid, f"创建了员工 {b.get('name', '')} (employeeId={e['employeeId']})", request.headers.get("X-Trace-Id") or rid)
    return jsonify(e), 201

@app.route("/departments", methods=["GET"])
def departments_list():
    data = get_store().department_list(_tenant())
    return jsonify({"data": data, "total": len(data)}), 200
@app.route("/departments", methods=["POST"])
def departments_create():
    tid, rid = _tenant(), _req_id()
    s = get_store()
    if s.idem_get(rid):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "details": "", "requestId": rid}), 409
    b = request.get_json() or {}
    d = s.department_create(tid, b.get("name", ""), b.get("parentId", ""))
    s.idem_set(rid, d["departmentId"])
    _human_audit(tid, f"创建了部门 {b.get('name', '')} (departmentId={d['departmentId']})", request.headers.get("X-Trace-Id") or rid)
    return jsonify(d), 201

@app.route("/leave-requests", methods=["GET"])
def leave_list():
    data = get_store().leave_list(_tenant())
    return jsonify({"data": data, "total": len(data)}), 200
@app.route("/leave-requests", methods=["POST"])
def leave_create():
    tid, rid = _tenant(), _req_id()
    s = get_store()
    if s.idem_get(rid):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "details": "", "requestId": rid}), 409
    b = request.get_json() or {}
    r = s.leave_create(tid, b.get("employeeId", ""), b.get("leaveType", ""), b.get("startDate", ""), b.get("endDate", ""), float(b.get("days", 0)))
    s.idem_set(rid, r["requestId"])
    _human_audit(tid, f"创建了请假申请 (requestId={r['requestId']})，员工 {b.get('employeeId', '')}，类型 {b.get('leaveType', '')}，{b.get('days', 0)} 天", request.headers.get("X-Trace-Id") or rid)
    return jsonify(r), 201

@app.route("/employees/<employee_id>", methods=["GET"])
def employee_get(employee_id: str):
    s = get_store()
    e = s.employee_get(_tenant(), employee_id)
    if not e:
        return jsonify({"code": "NOT_FOUND", "message": "员工不存在", "details": "", "requestId": _req_id()}), 404
    _human_audit(_tenant(), f"查询员工 {employee_id}")
    return jsonify(e), 200

@app.route("/departments/<department_id>", methods=["GET"])
def department_get(department_id: str):
    s = get_store()
    d = s.department_get(_tenant(), department_id)
    if not d:
        return jsonify({"code": "NOT_FOUND", "message": "部门不存在", "details": "", "requestId": _req_id()}), 404
    _human_audit(_tenant(), f"查询部门 {department_id}")
    return jsonify(d), 200

@app.route("/leave-requests/<request_id>", methods=["GET"])
def leave_get(request_id: str):
    s = get_store()
    r = s.leave_get(_tenant(), request_id)
    if not r:
        return jsonify({"code": "NOT_FOUND", "message": "请假申请不存在", "details": "", "requestId": _req_id()}), 404
    _human_audit(_tenant(), f"查询请假申请 {request_id}")
    return jsonify(r), 200

@app.route("/leave-requests/<request_id>", methods=["PATCH"])
def leave_patch(request_id: str):
    tid = _tenant()
    s = get_store()
    body = request.get_json() or {}
    status = body.get("status")
    if status is None:
        return jsonify({"code": "BAD_REQUEST", "message": "status 必填", "details": "", "requestId": _req_id()}), 400
    r = s.leave_update_status(tid, request_id, int(status))
    if not r:
        return jsonify({"code": "NOT_FOUND", "message": "请假申请不存在", "details": "", "requestId": _req_id()}), 404
    _human_audit(tid, f"更新请假申请 {request_id} 状态为 {status}")
    return jsonify(r), 200

if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8004")))
