# 商用化：脱敏、数据权限、客户名称重复提示
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query

from .. import database as db
from ..dependencies import get_tenant_id, get_request_id, get_owner_id, get_data_scope_owner, require_auth
from ..schemas import CustomerCreate, CustomerUpdate, ListResponse
from ..masking import apply_customer_masking

router = APIRouter()


def _user_id(request: Request) -> str:
    return (request.headers.get("X-User-Id") or "").strip() or "system"


@router.get("", response_model=ListResponse)
async def list_customers(
    page: int = 1,
    pageSize: int = Query(20, ge=1, le=500),
    keyword: Optional[str] = Query(None, description="名称/电话/邮箱模糊查询"),
    tenant_id: str = Depends(get_tenant_id),
    data_scope_owner: Optional[str] = Depends(get_data_scope_owner),
    _auth=Depends(require_auth),
):
    """行级权限：X-Data-Scope=self 时仅返回本人负责的客户；支持 keyword 高级查询。"""
    if data_scope_owner:
        data, total = db.customer_list_by_owner_keyword(tenant_id, data_scope_owner, keyword=keyword, page=page, page_size=pageSize)
    else:
        data, total = db.customer_list(tenant_id, page=page, page_size=pageSize, keyword=keyword)
    data = [apply_customer_masking(d) for d in data]
    return ListResponse(data=data, total=total)


@router.get("/{customer_id}")
async def get_customer(
    customer_id: str,
    tenant_id: str = Depends(get_tenant_id),
    _auth=Depends(require_auth),
):
    c = db.customer_get(tenant_id, customer_id)
    if not c:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "客户不存在", "details": "", "requestId": get_request_id()},
        )
    return apply_customer_masking(c)


@router.post("", status_code=201)
async def create_customer(
    body: CustomerCreate,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    owner_id: Optional[str] = Depends(get_owner_id),
    _auth=Depends(require_auth),
):
    rid = request.headers.get("X-Request-ID", "").strip()
    if not rid:
        raise HTTPException(
            status_code=400,
            detail={"code": "BAD_REQUEST", "message": "POST 必须包含 X-Request-ID", "details": "", "requestId": get_request_id()},
        )
    if not (body.name and body.name.strip()):
        raise HTTPException(
            status_code=400,
            detail={"code": "BAD_REQUEST", "message": "请填写客户名称", "details": "客户名称为必填项", "requestId": get_request_id()},
        )
    existing = db.idempotent_get(rid)
    if existing:
        if existing[0] == "customer":
            c = db.customer_get(tenant_id, existing[1])
            if c:
                raise HTTPException(status_code=409, detail={"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突，已存在同 X-Request-ID 的资源", "details": "", "requestId": rid})
    dup = db.customer_get_by_name(tenant_id, body.name.strip())
    if dup:
        raise HTTPException(
            status_code=400,
            detail={"code": "BUSINESS_RULE_VIOLATION", "message": "客户名称已存在", "details": "请使用其他客户名称或先查询是否已录入", "requestId": rid},
        )
    c = db.customer_create(tenant_id, body.name.strip(), body.contactPhone, body.contactEmail, owner_id=owner_id)
    db.idempotent_set(rid, "customer", c["customerId"])
    db.audit_append(tenant_id, _user_id(request), "customer.create", "customer", c["customerId"], rid)
    return apply_customer_masking(c)


@router.patch("/{customer_id}")
async def update_customer(
    customer_id: str,
    body: CustomerUpdate,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    _auth=Depends(require_auth),
):
    rid = request.headers.get("X-Request-ID", "").strip()
    if not rid:
        raise HTTPException(status_code=400, detail={"code": "BAD_REQUEST", "message": "PATCH 必须包含 X-Request-ID", "details": "", "requestId": get_request_id()})
    c = db.customer_update(tenant_id, customer_id, body.name, body.contactPhone, body.contactEmail)
    if not c:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "客户不存在", "details": "请检查客户编号或刷新列表后重试", "requestId": rid})
    db.audit_append(tenant_id, _user_id(request), "customer.update", "customer", customer_id, rid)
    return apply_customer_masking(c)


@router.delete("/{customer_id}", status_code=204)
async def delete_customer(
    customer_id: str,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    _auth=Depends(require_auth),
):
    ok = db.customer_delete(tenant_id, customer_id)
    if not ok:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "客户不存在", "details": "该客户可能已被删除，请刷新列表", "requestId": get_request_id()})
    db.audit_append(tenant_id, _user_id(request), "customer.delete", "customer", customer_id, get_request_id())


# ---------- 批量导入/导出（商用：支持 1000+ 条） ----------
@router.post("/import", status_code=202)
async def import_customers_batch(
    body: dict,
    tenant_id: str = Depends(get_tenant_id),
    owner_id: Optional[str] = Depends(get_owner_id),
    _auth=Depends(require_auth),
):
    """批量导入客户。body.items 为列表，每项 {name, contactPhone?, contactEmail?}；单次建议不超过 1000 条。"""
    items = body.get("items") or body.get("data") or []
    if not items or not isinstance(items, list):
        raise HTTPException(status_code=400, detail={"code": "BAD_REQUEST", "message": "请提供 items 数组", "details": "", "requestId": get_request_id()})
    if len(items) > 2000:
        raise HTTPException(status_code=400, detail={"code": "BAD_REQUEST", "message": "单次导入不超过 2000 条", "details": "", "requestId": get_request_id()})
    created, errors = [], []
    for i, row in enumerate(items):
        name = (row.get("name") or "").strip()
        if not name:
            errors.append({"index": i, "reason": "客户名称为空"})
            continue
        if db.customer_get_by_name(tenant_id, name):
            errors.append({"index": i, "reason": "客户名称已存在", "name": name})
            continue
        try:
            c = db.customer_create(
                tenant_id, name,
                contact_phone=row.get("contactPhone"),
                contact_email=row.get("contactEmail") or row.get("contactEmail"),
                owner_id=owner_id,
            )
            created.append({"index": i, "customerId": c["customerId"], "name": name})
        except Exception as e:
            errors.append({"index": i, "reason": str(e), "name": name})
    return {"accepted": True, "created": len(created), "errors": len(errors), "details": created, "errorsDetail": errors}


@router.get("/export")
async def export_customers(
    format: str = Query("json", alias="format"),
    page: int = 1,
    pageSize: int = 1000,
    tenant_id: str = Depends(get_tenant_id),
    data_scope_owner: Optional[str] = Depends(get_data_scope_owner),
    _auth=Depends(require_auth),
):
    """标准化导出：format=csv 返回 CSV（Excel 可打开）；否则返回 JSON 分页。行级权限同列表。"""
    from fastapi.responses import Response
    import csv, io
    pageSize = min(max(1, pageSize), 5000)
    if data_scope_owner:
        data, total = db.customer_list_by_owner(tenant_id, data_scope_owner, page=page, page_size=pageSize)
    else:
        data, total = db.customer_list(tenant_id, page=page, page_size=pageSize)
    data = [apply_customer_masking(d) for d in data]
    fmt = (format or "json").lower()
    if fmt == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["客户ID", "名称", "联系电话", "邮箱", "状态", "创建时间"])
        for c in data:
            w.writerow([c.get("customerId"), c.get("name"), c.get("contactPhone"), c.get("contactEmail"), c.get("status"), c.get("createdAt")])
        return Response(
            content=buf.getvalue().encode("utf-8-sig"),
            media_type="text/csv; charset=utf-8-sig",
            headers={"Content-Disposition": "attachment; filename=customers.csv"},
        )
    return {"data": data, "total": total, "page": page, "pageSize": pageSize}
