"""
PLM 细胞 Flask 应用 - 产品设计→BOM版本管理→工艺管理→变更管理→文档管理→图纸管理全流程。行业合规：版本追溯、变更可审计、研发数据权限。
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

def _human_audit(tenant_id: str, operation_desc: str, trace_id: str = "") -> None:
    user_id = request.headers.get("X-User-Id") or request.headers.get("X-Tenant-Id") or "system"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    trace_id = trace_id or request.headers.get("X-Trace-Id") or request.headers.get("X-Request-ID") or ""
    import logging
    logging.getLogger("plm.audit").info(f"【人性化审计】租户 {tenant_id} 用户 {user_id} 在 {ts} {operation_desc}，trace_id={trace_id}")

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

def _tenant() -> str:
    return (request.headers.get("X-Tenant-Id") or "").strip() or "default"

def _request_id() -> str:
    return (request.headers.get("X-Request-ID") or "").strip() or str(uuid.uuid4())

def _owner_id() -> str:
    """研发数据权限：研发工程师只能看自己负责的产品"""
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
    return jsonify({"status": "up", "cell": "plm"}), 200

@app.route("/products", methods=["GET"])
def list_products():
    tenant_id = _tenant()
    owner_id = _owner_id() or request.args.get("ownerId")
    page = max(1, int(request.args.get("page", 1)))
    page_size = max(1, min(100, int(request.args.get("pageSize", 20))))
    data, total = get_store().product_list(tenant_id, owner_id=owner_id or None, page=page, page_size=page_size)
    _human_audit(tenant_id, "查询产品列表")
    return jsonify({"data": data, "total": total, "page": page, "pageSize": page_size}), 200

@app.route("/products", methods=["POST"])
def create_product():
    tenant_id = _tenant()
    req_id = _request_id()
    owner_id = _owner_id()
    store = get_store()
    if store.idem_get(req_id):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "details": "", "requestId": req_id}), 409
    body = request.get_json() or {}
    code = (body.get("productCode") or "").strip()
    name = (body.get("name") or "").strip()
    if not code or not name:
        return jsonify({"code": "BAD_REQUEST", "message": "productCode 与 name 必填", "details": "", "requestId": req_id}), 400
    p = store.product_create(tenant_id, code, name, body.get("version", "1.0"), owner_id or body.get("ownerId", ""))
    store.idem_set(req_id, p["productId"])
    store.audit_append(tenant_id, request.headers.get("X-User-Id") or "system", "CREATE", "Product", p["productId"], req_id)
    _human_audit(tenant_id, f"创建产品 {p['productId']}", req_id)
    if _events:
        _events.publish("plm.product.created", {"productId": p["productId"], "tenantId": tenant_id, "productCode": code}, trace_id=req_id)
    return jsonify(p), 201

@app.route("/products/<product_id>", methods=["GET"])
def get_product(product_id: str):
    p = get_store().product_get(_tenant(), product_id)
    if not p:
        return jsonify({"code": "NOT_FOUND", "message": "产品不存在", "details": "", "requestId": _request_id()}), 404
    _human_audit(_tenant(), f"查询产品 {product_id}")
    return jsonify(p), 200

@app.route("/boms", methods=["GET"])
def list_boms():
    tenant_id = _tenant()
    product_id = request.args.get("productId")
    version = request.args.get("version")
    version_int = int(version) if version is not None and str(version).isdigit() else None
    data = get_store().bom_list(tenant_id, product_id=product_id, version=version_int)
    _human_audit(tenant_id, "查询 BOM 列表")
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/boms", methods=["POST"])
def create_bom():
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    if store.idem_get(req_id):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "details": "", "requestId": req_id}), 409
    body = request.get_json() or {}
    product_id = (body.get("productId") or "").strip()
    if not product_id:
        return jsonify({"code": "BAD_REQUEST", "message": "productId 必填", "details": "", "requestId": req_id}), 400
    b = store.bom_create(tenant_id, product_id, body.get("parentId", ""), float(body.get("quantity", 1)), int(body.get("version", 1)))
    store.idem_set(req_id, b["bomId"])
    store.audit_append(tenant_id, request.headers.get("X-User-Id") or "system", "CREATE", "BOM", b["bomId"], req_id)
    _human_audit(tenant_id, f"创建 BOM {b['bomId']}", req_id)
    if _events:
        _events.publish("plm.bom.created", {"bomId": b["bomId"], "tenantId": tenant_id, "productId": product_id, "version": b.get("version")}, trace_id=req_id)
    return jsonify(b), 201

@app.route("/boms/<bom_id>", methods=["GET"])
def get_bom(bom_id: str):
    b = get_store().bom_get(_tenant(), bom_id)
    if not b:
        return jsonify({"code": "NOT_FOUND", "message": "BOM 不存在", "details": "", "requestId": _request_id()}), 404
    _human_audit(_tenant(), f"查询 BOM {bom_id}")
    return jsonify(b), 200

@app.route("/change-records", methods=["GET"])
def list_change_records():
    tenant_id = _tenant()
    entity_type = request.args.get("entityType")
    entity_id = request.args.get("entityId")
    page = max(1, int(request.args.get("page", 1)))
    page_size = max(1, min(100, int(request.args.get("pageSize", 20))))
    data, total = get_store().change_record_list(tenant_id, entity_type=entity_type, entity_id=entity_id, page=page, page_size=page_size)
    return jsonify({"data": data, "total": total, "page": page, "pageSize": page_size}), 200

@app.route("/change-records", methods=["POST"])
def create_change_record():
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    body = request.get_json() or {}
    entity_type = (body.get("entityType") or "").strip()
    entity_id = (body.get("entityId") or "").strip()
    if not entity_type or not entity_id:
        return jsonify({"code": "BAD_REQUEST", "message": "entityType、entityId 必填", "details": "", "requestId": req_id}), 400
    changed_by = request.headers.get("X-User-Id") or "system"
    c = store.change_record_add(tenant_id, entity_type, entity_id, body.get("changeType", "update"), body.get("description", ""), changed_by)
    store.audit_append(tenant_id, changed_by, "CREATE", "ChangeRecord", c["changeId"], req_id)
    _human_audit(tenant_id, f"变更记录 {c['changeId']}", req_id)
    if _events:
        _events.publish("plm.change.recorded", {"changeId": c["changeId"], "tenantId": tenant_id, "entityType": entity_type, "entityId": entity_id}, trace_id=req_id)
    return jsonify(c), 201

@app.route("/documents", methods=["GET"])
def list_documents():
    tenant_id = _tenant()
    product_id = request.args.get("productId")
    doc_type = request.args.get("docType")
    data = get_store().document_list(tenant_id, product_id=product_id, doc_type=doc_type)
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/documents", methods=["POST"])
def create_document():
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    if store.idem_get(req_id):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "details": "", "requestId": req_id}), 409
    body = request.get_json() or {}
    product_id = (body.get("productId") or "").strip()
    doc_type = (body.get("docType") or "drawing").strip()
    if not product_id or doc_type not in ("drawing", "process_file"):
        return jsonify({"code": "BAD_REQUEST", "message": "productId 必填，docType 为 drawing|process_file", "details": "", "requestId": req_id}), 400
    d = store.document_add(tenant_id, product_id, doc_type, int(body.get("version", 1)), body.get("storagePath", ""))
    store.idem_set(req_id, d["docId"])
    store.audit_append(tenant_id, request.headers.get("X-User-Id") or "system", "CREATE", "Document", d["docId"], req_id)
    _human_audit(tenant_id, f"上传文档 {d['docId']}", req_id)
    if _events:
        _events.publish("plm.document.added", {"docId": d["docId"], "tenantId": tenant_id, "productId": product_id, "docType": doc_type}, trace_id=req_id)
    return jsonify(d), 201

@app.route("/process-routes", methods=["GET"])
def list_process_routes():
    tenant_id = _tenant()
    product_id = request.args.get("productId", "").strip() or None
    data = get_store().process_route_list(tenant_id, product_id=product_id)
    _human_audit(tenant_id, "查询工艺路线列表")
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/process-routes", methods=["POST"])
def create_process_route():
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    if store.idem_get(req_id):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "details": "", "requestId": req_id}), 409
    body = request.get_json() or {}
    product_id = (body.get("productId") or "").strip()
    name = (body.get("name") or "").strip()
    if not product_id or not name:
        return jsonify({"code": "BAD_REQUEST", "message": "productId 与 name 必填", "details": "", "requestId": req_id}), 400
    p = store.process_route_create(tenant_id, product_id, name, int(body.get("version", 1)), body.get("steps", ""))
    store.idem_set(req_id, p["processRouteId"])
    store.audit_append(tenant_id, request.headers.get("X-User-Id") or "system", "CREATE", "ProcessRoute", p["processRouteId"], req_id)
    _human_audit(tenant_id, f"创建工艺路线 {p['processRouteId']}", req_id)
    if _events:
        _events.publish("plm.process_route.created", {"processRouteId": p["processRouteId"], "tenantId": tenant_id, "productId": product_id}, trace_id=req_id)
    return jsonify(p), 201

@app.route("/process-routes/<process_route_id>", methods=["GET"])
def get_process_route(process_route_id: str):
    p = get_store().process_route_get(_tenant(), process_route_id)
    if not p:
        return jsonify({"code": "NOT_FOUND", "message": "工艺路线不存在", "details": "", "requestId": _request_id()}), 404
    return jsonify(p), 200

@app.route("/drawings", methods=["GET"])
def list_drawings():
    """图纸管理：即 docType=drawing 的文档列表。"""
    tenant_id = _tenant()
    product_id = request.args.get("productId", "").strip() or None
    data = get_store().document_list(tenant_id, product_id=product_id, doc_type="drawing")
    return jsonify({"data": data, "total": len(data)}), 200

@app.route("/drawings", methods=["POST"])
def create_drawing():
    """图纸上传：即 docType=drawing 的文档。"""
    tenant_id = _tenant()
    req_id = _request_id()
    store = get_store()
    if store.idem_get(req_id):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "details": "", "requestId": req_id}), 409
    body = request.get_json() or {}
    product_id = (body.get("productId") or "").strip()
    if not product_id:
        return jsonify({"code": "BAD_REQUEST", "message": "productId 必填", "details": "", "requestId": req_id}), 400
    d = store.document_add(tenant_id, product_id, "drawing", int(body.get("version", 1)), body.get("storagePath", ""))
    store.idem_set(req_id, d["docId"])
    store.audit_append(tenant_id, request.headers.get("X-User-Id") or "system", "CREATE", "Drawing", d["docId"], req_id)
    _human_audit(tenant_id, f"上传图纸 {d['docId']}", req_id)
    if _events:
        _events.publish("plm.drawing.added", {"docId": d["docId"], "tenantId": tenant_id, "productId": product_id}, trace_id=req_id)
    return jsonify(d), 201

@app.route("/audit-logs", methods=["GET"])
def list_audit_logs():
    """研发合规：不可篡改操作审计日志。"""
    tenant_id = _tenant()
    page = max(1, int(request.args.get("page", 1)))
    page_size = max(1, min(100, int(request.args.get("pageSize", 50))))
    resource_type = request.args.get("resourceType", "").strip() or None
    data, total = get_store().audit_list(tenant_id, page=page, page_size=page_size, resource_type=resource_type)
    return jsonify({"data": data, "total": total, "page": page, "pageSize": page_size}), 200

@app.route("/products/export", methods=["GET"])
def export_products():
    """产品列表导出（CSV），研发数据权限过滤。"""
    tenant_id = _tenant()
    owner_id = _owner_id() or request.args.get("ownerId")
    data, _ = get_store().product_list(tenant_id, owner_id=owner_id or None, page=1, page_size=10000)
    import csv, io
    from flask import Response
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["productId", "productCode", "name", "version", "status", "ownerId", "createdAt"])
    for row in data:
        w.writerow([row.get("productId", ""), row.get("productCode", ""), row.get("name", ""), row.get("version", ""), row.get("status", ""), row.get("ownerId", ""), row.get("createdAt", "")])
    get_store().audit_append(tenant_id, request.headers.get("X-User-Id") or "system", "EXPORT", "Product", "", _request_id())
    _human_audit(tenant_id, f"导出产品 {len(data)} 条")
    return Response(buf.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=plm_products.csv"})

@app.route("/products/import", methods=["POST"])
def import_products():
    tenant_id = _tenant()
    req_id = _request_id()
    owner_id = _owner_id()
    store = get_store()
    if store.idem_get(req_id):
        return jsonify({"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "details": "", "requestId": req_id}), 409
    body = request.get_json() or {}
    items = body.get("items") or body.get("data") or []
    if not items or len(items) > 500:
        return jsonify({"code": "BAD_REQUEST", "message": "items 必填且不超过 500 条", "details": "", "requestId": req_id}), 400
    created = store.product_batch_import(tenant_id, owner_id or "system", items)
    store.idem_set(req_id, "import_batch")
    _human_audit(tenant_id, f"批量导入产品 {len(created)} 条", req_id)
    return jsonify({"accepted": True, "count": len(created), "data": created}), 201

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8009))
    app.run(host="0.0.0.0", port=port, debug=False)
