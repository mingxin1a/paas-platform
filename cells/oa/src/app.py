"""
OA 细胞 Flask 应用 - 任务管理，01 合规（验签、人性化审计）。
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
    logging.getLogger("oa.audit").info(f"【人性化审计】租户 {tenant_id} 用户 {user_id} 在 {ts} {operation_desc}，trace_id={trace_id}")

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

def _tenant() -> str:
    return (request.headers.get("X-Tenant-Id") or "").strip() or "default"

def _request_id() -> str:
    return (request.headers.get("X-Request-ID") or "").strip() or str(uuid.uuid4())

def _user_id() -> str:
    return (request.headers.get("X-User-Id") or request.headers.get("X-Tenant-Id") or "system").strip() or "system"

def _err(code: str, message: str, request_id: str = "", details: str = "") -> tuple[dict, int]:
    """《接口设计说明书》3.1.3：错误响应含 code、message、details、requestId；商用友好话术。"""
    return ({"code": code, "message": message, "details": details, "requestId": request_id or _request_id()}, 400 if code == "BAD_REQUEST" else 404)

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
    return jsonify({"status": "up", "cell": "oa"}), 200

@app.route("/tasks", methods=["GET"])
def list_tasks():
    tenant_id = _tenant()
    store = get_store()
    data = store.task_list(tenant_id)
    _human_audit(tenant_id, "查询任务列表")
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/tasks", methods=["POST"])
def create_task():
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    if store.idem_get(req_id):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "details": "", "requestId": req_id}), 409
    body = request.get_json() or {}
    title = (body.get("title") or "").strip()
    if not title:
        err_body, err_status = _err("BAD_REQUEST", "title 必填", req_id, "请填写任务标题")
        return jsonify(err_body), err_status
    t = store.task_create(tenant_id, title, body.get("assigneeId", ""), int(body.get("priority", 0)))
    store.idem_set(req_id, t["taskId"])
    store.audit_append(tenant_id, _user_id(), "task.create", "task", t["taskId"], req_id)
    _human_audit(tenant_id, f"创建任务 {t['taskId']}", req_id)
    return jsonify(t), 201

@app.route("/tasks/<task_id>", methods=["GET"])
def get_task(task_id: str):
    tenant_id = _tenant()
    store = get_store()
    t = store.task_get(tenant_id, task_id)
    if not t:
        err_body, err_status = _err("NOT_FOUND", "任务不存在", _request_id(), "任务不存在或已删除")
        return jsonify(err_body), err_status
    _human_audit(tenant_id, f"查询任务 {task_id}")
    return jsonify(t), 200

@app.route("/tasks/<task_id>", methods=["PATCH"])
def update_task(task_id: str):
    tenant_id = _tenant()
    store = get_store()
    body = request.get_json() or {}
    status = body.get("status")
    if status is None:
        err_body, err_status = _err("BAD_REQUEST", "status 必填", _request_id(), "请传递 status 字段")
        return jsonify(err_body), err_status
    t = store.task_update_status(tenant_id, task_id, int(status))
    if not t:
        err_body, err_status = _err("NOT_FOUND", "任务不存在", _request_id(), "请检查任务编号或刷新列表后重试")
        return jsonify(err_body), err_status
    store.audit_append(tenant_id, _user_id(), "task.update", "task", task_id, _request_id())
    _human_audit(tenant_id, f"更新任务 {task_id} 状态为 {status}")
    return jsonify(t), 200

# ---------- 审批流程（数据权限：仅本人发起/待审批） ----------
@app.route("/approvals", methods=["GET"])
def list_approvals():
    tenant_id = _tenant()
    user_id = request.headers.get("X-User-Id") or ""
    status = request.args.get("status")
    page = max(1, int(request.args.get("page", 1)))
    page_size = max(1, min(100, int(request.args.get("pageSize", 20))))
    data, total = get_store().approval_list(tenant_id, applicant_id=user_id or None, status=status, page=page, page_size=page_size)
    _human_audit(tenant_id, "查询审批列表")
    return jsonify({"data": data, "total": total, "page": page, "pageSize": page_size}), 200

@app.route("/approvals", methods=["POST"])
def create_approval():
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    if store.idem_get(req_id):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "details": "", "requestId": req_id}), 409
    body = request.get_json() or {}
    type_code = (body.get("typeCode") or "leave").strip()
    if type_code not in ("purchase", "reimburse", "leave", "contract", "sales_order", "purchase_order"):
        err_body, err_status = _err("BAD_REQUEST", "typeCode 须为 purchase|reimburse|leave|contract|sales_order|purchase_order", _request_id(), "仅支持上述类型")
        return jsonify(err_body), err_status
    applicant_id = request.headers.get("X-User-Id") or "system"
    a = store.approval_create(tenant_id, applicant_id, type_code, body.get("formData", {}))
    store.idem_set(req_id, a["instanceId"])
    _human_audit(tenant_id, f"创建审批 {a['instanceId']}", req_id)
    return jsonify(a), 201

@app.route("/approvals/<instance_id>/submit", methods=["POST"])
def submit_approval(instance_id: str):
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    a = store.approval_submit(tenant_id, instance_id, req_id)
    if not a:
        err_body, err_status = _err("NOT_FOUND", "审批单不存在或已提交", _request_id(), "请检查 instanceId")
        return jsonify(err_body), err_status
    _human_audit(tenant_id, f"提交审批 {instance_id}", req_id)
    return jsonify(a), 200


@app.route("/approvals/<instance_id>/complete", methods=["POST"])
def complete_approval(instance_id: str):
    """审批完成：body { "approved": true|false }。通过后发布 oa.approval.completed 供联动 Worker 回传业务模块。"""
    tenant_id = _tenant()
    user_id = _user_id()
    body = request.get_json() or {}
    approved = body.get("approved", True)
    a = get_store().approval_complete(tenant_id, instance_id, approved, processor_id=user_id)
    if not a:
        err_body, err_status = _err("NOT_FOUND", "审批单不存在或已处理", _request_id(), "请检查审批单编号")
        return jsonify(err_body), err_status
    try:
        from . import event_publisher as _ev
        _ev.publish(
            "oa.approval.completed",
            {"instanceId": instance_id, "tenantId": tenant_id, "status": a.get("status"), "formData": a.get("formData") or {}, "typeCode": a.get("typeCode", "")},
            trace_id=_request_id(),
        )
    except Exception:
        pass
    return jsonify(a), 200


@app.route("/approvals/<instance_id>/seal", methods=["POST"])
def seal_approval(instance_id: str):
    """电子签章：对审批单加盖电子章，记录签章人与时间。"""
    tenant_id = _tenant()
    user_id = request.headers.get("X-User-Id") or request.headers.get("X-Tenant-Id") or "system"
    store = get_store()
    a = store.approval_seal(tenant_id, instance_id, user_id)
    if not a:
        err_body, err_status = _err("NOT_FOUND", "审批单不存在或无权操作", _request_id(), "请检查审批单编号")
        return jsonify(err_body), err_status
    _human_audit(tenant_id, f"审批单 {instance_id} 电子签章", _request_id())
    return jsonify(a), 200


@app.route("/approvals/<instance_id>/print", methods=["GET"])
def print_approval(instance_id: str):
    """审批单打印模板：返回 HTML，可浏览器打印或另存为 PDF。"""
    from flask import Response
    tenant_id = _tenant()
    a = get_store().approval_get(tenant_id, instance_id)
    if not a:
        err_body, err_status = _err("NOT_FOUND", "审批单不存在", _request_id(), "请检查审批单编号")
        return jsonify(err_body), err_status
    type_name = {"purchase": "采购审批", "reimburse": "报销审批", "leave": "请假审批"}.get(a.get("typeCode", ""), "审批单")
    sealed = "已签章" if a.get("sealedAt") else "未签章"
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"/><title>{type_name} - {instance_id}</title>
<style>body{{font-family:SimSun,serif;margin:2em;}} table{{border-collapse:collapse;width:100%;}} th,td{{border:1px solid #333;padding:6px;text-align:left;}} th{{background:#f0f0f0;}}</style></head><body>
<h2>{type_name}</h2>
<table><tr><th>审批单号</th><td>{a.get('instanceId','')}</td></tr>
<tr><th>类型</th><td>{a.get('typeCode','')}</td></tr>
<tr><th>状态</th><td>{a.get('status','')}</td></tr>
<tr><th>签章状态</th><td>{sealed}</td></tr>
<tr><th>签章人</th><td>{a.get('sealedBy','') or '—'}</td></tr>
<tr><th>签章时间</th><td>{a.get('sealedAt','') or '—'}</td></tr>
<tr><th>创建时间</th><td>{a.get('createdAt','')}</td></tr></table>
<p style="margin-top:1.5em;color:#666;">表单数据见系统详情。本页可用于打印或另存为 PDF。</p>
</body></html>"""
    return Response(html, mimetype="text/html; charset=utf-8")


# ---------- 公告 ----------
@app.route("/announcements", methods=["GET"])
def list_announcements():
    tenant_id = _tenant()
    page = max(1, int(request.args.get("page", 1)))
    page_size = max(1, min(100, int(request.args.get("pageSize", 20))))
    data, total = get_store().announcement_list(tenant_id, page=page, page_size=page_size)
    _human_audit(tenant_id, "查询公告列表")
    return jsonify({"data": data, "total": total, "page": page, "pageSize": page_size}), 200

@app.route("/announcements", methods=["POST"])
def create_announcement():
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    if store.idem_get(req_id):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "details": "", "requestId": req_id}), 409
    body = request.get_json() or {}
    title = (body.get("title") or "").strip()
    if not title:
        err_body, err_status = _err("BAD_REQUEST", "title 必填", req_id, "请填写公告标题")
        return jsonify(err_body), err_status
    a = store.announcement_create(tenant_id, title, body.get("content", ""), request.headers.get("X-User-Id") or "")
    store.idem_set(req_id, a["announcementId"])
    store.audit_append(tenant_id, _user_id(), "announcement.create", "announcement", a["announcementId"], req_id)
    _human_audit(tenant_id, f"发布公告 {a['announcementId']}", req_id)
    return jsonify(a), 201


@app.route("/audit-logs", methods=["GET"])
def list_audit_logs():
    tenant_id = _tenant()
    page = max(1, int(request.args.get("page", 1)))
    page_size = max(1, min(200, int(request.args.get("pageSize", 50))))
    resource_type = (request.args.get("resourceType") or "").strip() or None
    data, total = get_store().audit_list(tenant_id, page=page, page_size=page_size, resource_type=resource_type)
    return jsonify({"data": data, "total": total, "page": page, "pageSize": page_size}), 200


@app.route("/tasks/batch-complete", methods=["POST"])
def batch_complete_tasks():
    """批量办结任务。body: { "taskIds": ["id1", "id2"] }。"""
    tenant_id = _tenant()
    body = request.get_json() or {}
    task_ids = body.get("taskIds") or []
    if not task_ids or not isinstance(task_ids, list):
        return jsonify({"code": "BAD_REQUEST", "message": "请提供 taskIds 数组", "details": "请求体需包含 taskIds 字段", "requestId": _request_id()}), 400
    if len(task_ids) > 200:
        return jsonify({"code": "BAD_REQUEST", "message": "单次最多 200 条", "details": "请分批操作", "requestId": _request_id()}), 400
    done, not_found = get_store().task_batch_complete(tenant_id, task_ids)
    _human_audit(tenant_id, f"批量办结任务 {done} 条")
    return jsonify({"completed": done, "notFound": not_found}), 200


@app.route("/reminders", methods=["GET"])
def get_reminders():
    """待办提醒：未完成任务与待审批数量。可选 X-User-Id 仅查本人待办。"""
    tenant_id = _tenant()
    assignee_id = (request.args.get("assigneeId") or request.headers.get("X-User-Id") or "").strip() or None
    limit = max(1, min(100, int(request.args.get("limit", 50))))
    data = get_store().task_reminders(tenant_id, assignee_id=assignee_id, limit=limit)
    return jsonify(data), 200


@app.route("/announcements/<announcement_id>", methods=["GET"])
def get_announcement(announcement_id: str):
    tenant_id = _tenant()
    a = get_store().announcement_get(tenant_id, announcement_id)
    if not a:
        err_body, err_status = _err("NOT_FOUND", "公告不存在", _request_id(), "请检查公告编号或刷新列表")
        return jsonify(err_body), err_status
    return jsonify(a), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8005))
    app.run(host="0.0.0.0", port=port, debug=False)
