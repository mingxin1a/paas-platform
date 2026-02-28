"""
HIS 细胞 Flask 应用 - 患者→挂号→就诊→处方→收费→住院→病历。医疗合规：患者信息脱敏，病历不可篡改，医护权限分级。
"""
from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from .store import get_store, HISStore

def _human_audit(tenant_id: str, operation_desc: str, trace_id: str = "") -> None:
    user_id = request.headers.get("X-User-Id") or request.headers.get("X-Tenant-Id") or "system"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    trace_id = trace_id or request.headers.get("X-Trace-Id") or request.headers.get("X-Request-ID") or ""
    import logging
    logging.getLogger("his.audit").info(f"【人性化审计】租户 {tenant_id} 用户 {user_id} 在 {ts} {operation_desc}，trace_id={trace_id}")

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

def _tenant() -> str:
    return (request.headers.get("X-Tenant-Id") or "").strip() or "default"

def _request_id() -> str:
    return (request.headers.get("X-Request-ID") or "").strip() or str(uuid.uuid4())

def _doctor_id() -> str:
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
    return jsonify({"status": "up", "cell": "his"}), 200

@app.route("/patients", methods=["GET"])
def list_patients():
    tenant_id = _tenant()
    doctor_id = _doctor_id() or request.args.get("doctorId")
    data = get_store().patient_list(tenant_id, doctor_id=doctor_id or None)
    data = [HISStore.apply_patient_masking(p) for p in data]
    _human_audit(tenant_id, "查询患者列表")
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/patients", methods=["POST"])
def create_patient():
    tenant_id = _tenant()
    req_id = _request_id()
    doctor_id = _doctor_id()
    store = get_store()
    if store.idem_get(req_id):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "details": "", "requestId": req_id}), 409
    body = request.get_json() or {}
    name = (body.get("name") or "").strip()
    patient_no = (body.get("patientNo") or "").strip()
    if not name:
        return jsonify({"code": "BAD_REQUEST", "message": "name 必填", "details": "", "requestId": req_id}), 400
    p = store.patient_create(tenant_id, patient_no or req_id[:8], name, body.get("gender", ""), body.get("idNo", ""), doctor_id or body.get("doctorId", ""))
    store.idem_set(req_id, p["patientId"])
    store.audit_append(tenant_id, request.headers.get("X-User-Id") or "system", "CREATE", "Patient", p["patientId"], req_id)
    _human_audit(tenant_id, f"创建患者 {p['patientId']}", req_id)
    out = HISStore.apply_patient_masking(p)
    return jsonify(out), 201

@app.route("/patients/<patient_id>", methods=["GET"])
def get_patient(patient_id: str):
    p = get_store().patient_get(_tenant(), patient_id)
    if not p:
        return jsonify({"code": "NOT_FOUND", "message": "患者不存在", "details": "", "requestId": _request_id()}), 404
    _human_audit(_tenant(), f"查询患者 {patient_id}")
    return jsonify(HISStore.apply_patient_masking(p)), 200

@app.route("/visits", methods=["GET"])
def list_visits():
    tenant_id = _tenant()
    doctor_id = _doctor_id() or request.args.get("doctorId")
    data = get_store().visit_list(tenant_id, doctor_id=doctor_id or None)
    _human_audit(tenant_id, "查询就诊列表")
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/visits", methods=["POST"])
def create_visit():
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    if store.idem_get(req_id):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "details": "", "requestId": req_id}), 409
    body = request.get_json() or {}
    patient_id = (body.get("patientId") or "").strip()
    if not patient_id:
        return jsonify({"code": "BAD_REQUEST", "message": "patientId 必填", "details": "", "requestId": req_id}), 400
    doctor_id = _doctor_id() or body.get("doctorId", "")
    v = store.visit_create(tenant_id, patient_id, body.get("departmentId", ""), doctor_id)
    store.idem_set(req_id, v["visitId"])
    store.audit_append(tenant_id, request.headers.get("X-User-Id") or "system", "CREATE", "Visit", v["visitId"], req_id)
    _human_audit(tenant_id, f"创建就诊 {v['visitId']}", req_id)
    return jsonify(v), 201

@app.route("/visits/<visit_id>", methods=["GET"])
def get_visit(visit_id: str):
    v = get_store().visit_get(_tenant(), visit_id)
    if not v:
        return jsonify({"code": "NOT_FOUND", "message": "就诊不存在", "details": "", "requestId": _request_id()}), 404
    _human_audit(_tenant(), f"查询就诊 {visit_id}")
    return jsonify(v), 200

@app.route("/registration", methods=["GET"])
def list_registration():
    """挂号列表（医疗合规：仅本租户、可按患者筛选）。"""
    tenant_id = _tenant()
    patient_id = request.args.get("patientId", "").strip() or None
    data = get_store().registration_list(tenant_id, patient_id=patient_id)
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/registration", methods=["POST"])
def create_registration():
    """挂号：幂等（X-Request-ID 或 idempotentKey）。"""
    tenant_id = _tenant()
    req_id = _request_id()
    body = request.get_json() or {}
    patient_id = (body.get("patientId") or "").strip()
    if not patient_id:
        return jsonify({"code": "BAD_REQUEST", "message": "patientId 必填", "details": "", "requestId": req_id}), 400
    idem_key = body.get("idempotentKey") or req_id
    store = get_store()
    r, is_new = store.registration_create(tenant_id, patient_id, body.get("departmentId", ""), body.get("scheduleDate", ""), idem_key)
    store.audit_append(tenant_id, request.headers.get("X-User-Id") or "system", "CREATE", "Registration", r["registrationId"], req_id)
    _human_audit(tenant_id, f"挂号 {r['registrationId']}", req_id)
    return jsonify(r), 201 if is_new else 200

@app.route("/prescriptions", methods=["POST"])
def create_prescription():
    """处方开具：防重复（同就诊同内容仅一条）。"""
    tenant_id = _tenant()
    req_id = _request_id()
    body = request.get_json() or {}
    visit_id = (body.get("visitId") or "").strip()
    drug_list = body.get("drugList") or body.get("content", "")
    if not visit_id:
        return jsonify({"code": "BAD_REQUEST", "message": "visitId 必填", "details": "", "requestId": req_id}), 400
    p, is_new = get_store().prescription_create(tenant_id, visit_id, drug_list)
    if not is_new:
        return jsonify({"code": "DUPLICATE_PRESCRIPTION", "message": "该就诊已存在相同处方，请勿重复开具", "details": "", "requestId": req_id, "prescriptionId": p["prescriptionId"]}), 409
    get_store().audit_append(tenant_id, request.headers.get("X-User-Id") or "system", "CREATE", "Prescription", p["prescriptionId"], req_id)
    _human_audit(tenant_id, f"开具处方 {p['prescriptionId']}", req_id)
    return jsonify(p), 201

@app.route("/charges", methods=["GET"])
def list_charges():
    """收费列表（医疗合规：按就诊筛选）。"""
    tenant_id = _tenant()
    visit_id = request.args.get("visitId", "").strip() or None
    data = get_store().charge_list(tenant_id, visit_id=visit_id)
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/charges", methods=["POST"])
def create_charge():
    """收费单创建：幂等。"""
    tenant_id = _tenant()
    req_id = _request_id()
    body = request.get_json() or {}
    visit_id = (body.get("visitId") or "").strip()
    amount = int(body.get("amountCents", 0))
    if not visit_id:
        return jsonify({"code": "BAD_REQUEST", "message": "visitId 必填", "details": "", "requestId": req_id}), 400
    idem_key = body.get("idempotentKey") or req_id
    store = get_store()
    c, is_new = store.charge_create(tenant_id, visit_id, amount, idem_key)
    if is_new:
        store.audit_append(tenant_id, request.headers.get("X-User-Id") or "system", "CREATE", "Charge", c["chargeId"], req_id)
    return jsonify(c), 201 if is_new else 200

@app.route("/charges/<charge_id>/pay", methods=["POST"])
def pay_charge(charge_id: str):
    """收费（缴费）：欠费时返回商用化提示。"""
    tenant_id = _tenant()
    body = request.get_json() or {}
    pay_cents = int(body.get("payCents", 0))
    store = get_store()
    c = store.charge_pay(tenant_id, charge_id, pay_cents)
    if not c:
        return jsonify({"code": "NOT_FOUND", "message": "收费单不存在", "details": "", "requestId": _request_id()}), 404
    arrears = max(0, c.get("amountCents", 0) - c.get("paidCents", 0))
    out = dict(c)
    if arrears > 0:
        out["message"] = "患者存在欠费，请先结清后再办理后续业务"
        out["arrearsCents"] = arrears
    store.audit_append(tenant_id, request.headers.get("X-User-Id") or "system", "PAY", "Charge", charge_id, _request_id())
    return jsonify(out), 200

@app.route("/inpatients", methods=["GET"])
def list_inpatients():
    """住院列表（医疗合规：按患者筛选）。"""
    tenant_id = _tenant()
    patient_id = request.args.get("patientId", "").strip() or None
    data = get_store().inpatient_list(tenant_id, patient_id=patient_id)
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/inpatients", methods=["POST"])
def create_inpatient():
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    if store.idem_get(req_id):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "details": "", "requestId": req_id}), 409
    body = request.get_json() or {}
    patient_id = (body.get("patientId") or "").strip()
    if not patient_id:
        return jsonify({"code": "BAD_REQUEST", "message": "patientId 必填", "details": "", "requestId": req_id}), 400
    i = store.inpatient_create(tenant_id, patient_id, body.get("bedNo", ""))
    store.idem_set(req_id, i["inpatientId"])
    store.audit_append(tenant_id, request.headers.get("X-User-Id") or "system", "CREATE", "Inpatient", i["inpatientId"], req_id)
    _human_audit(tenant_id, f"住院登记 {i['inpatientId']}", req_id)
    return jsonify(i), 201

@app.route("/medical-records", methods=["POST"])
def append_medical_record():
    """病历追加（不可篡改，仅追加）。"""
    tenant_id = _tenant()
    body = request.get_json() or {}
    patient_id = (body.get("patientId") or "").strip()
    content = body.get("content", "")
    if not patient_id:
        return jsonify({"code": "BAD_REQUEST", "message": "patientId 必填", "requestId": _request_id()}), 400
    store = get_store()
    r = store.medical_record_append(tenant_id, patient_id, body.get("visitId", ""), content)
    store.audit_append(tenant_id, request.headers.get("X-User-Id") or "system", "APPEND", "MedicalRecord", r["recordId"], _request_id())
    _human_audit(tenant_id, f"记录病历 {r['recordId']}", _request_id())
    return jsonify(r), 201

@app.route("/medical-records", methods=["GET"])
def list_medical_records():
    tenant_id = _tenant()
    patient_id = request.args.get("patientId")
    data = get_store().medical_record_list(tenant_id, patient_id=patient_id or None)
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/orders", methods=["GET"])
def list_orders():
    tenant_id = _tenant()
    data = get_store().order_list(tenant_id)
    _human_audit(tenant_id, "查询医嘱列表")
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/orders", methods=["POST"])
def create_order():
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    if store.idem_get(req_id):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "details": "", "requestId": req_id}), 409
    body = request.get_json() or {}
    o = store.order_create(tenant_id, body.get("visitId", ""), body.get("orderType", ""), body.get("content", ""))
    store.idem_set(req_id, o["orderId"])
    _human_audit(tenant_id, f"创建医嘱 {o['orderId']}", req_id)
    return jsonify(o), 201

@app.route("/orders/<order_id>", methods=["GET"])
def get_order(order_id: str):
    o = get_store().order_get(_tenant(), order_id)
    if not o:
        return jsonify({"code": "NOT_FOUND", "message": "医嘱不存在", "details": "", "requestId": _request_id()}), 404
    _human_audit(_tenant(), f"查询医嘱 {order_id}")
    return jsonify(o), 200

@app.route("/audit-logs", methods=["GET"])
def list_audit_logs():
    """医疗合规：不可篡改操作审计日志（患者数据访问与操作可追溯）。"""
    tenant_id = _tenant()
    page = max(1, int(request.args.get("page", 1)))
    page_size = max(1, min(100, int(request.args.get("pageSize", 50))))
    resource_type = request.args.get("resourceType", "").strip() or None
    data, total = get_store().audit_list(tenant_id, page=page, page_size=page_size, resource_type=resource_type)
    return jsonify({"data": data, "total": total, "page": page, "pageSize": page_size}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8011))
    app.run(host="0.0.0.0", port=port, debug=False)
