from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import Response

from .. import database as db
from ..dependencies import get_tenant_id, get_request_id, require_auth
from ..schemas import OpportunityCreate, OpportunityUpdate, ListResponse

router = APIRouter()


def _user_id(request: Request) -> str:
    return (request.headers.get("X-User-Id") or "").strip() or "system"


@router.get("", response_model=ListResponse)
async def list_opportunities(
    customerId: Optional[str] = None,
    page: int = 1,
    pageSize: int = 20,
    tenant_id: str = Depends(get_tenant_id),
    _auth=Depends(require_auth),
):
    data, total = db.opportunity_list(tenant_id, customer_id=customerId, page=page, page_size=pageSize)
    return ListResponse(data=data, total=total)


@router.get("/export")
async def export_opportunities(
    format: str = Query("json", alias="format"),
    customerId: Optional[str] = None,
    page: int = 1,
    pageSize: int = Query(1000, ge=1, le=5000),
    tenant_id: str = Depends(get_tenant_id),
    _auth=Depends(require_auth),
):
    """标准化导出：format=csv 返回 CSV；否则返回 JSON 分页。"""
    import csv
    import io
    data, total = db.opportunity_list(tenant_id, customer_id=customerId, page=page, page_size=pageSize)
    fmt = (format or "json").lower()
    if fmt == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["商机ID", "客户ID", "标题", "金额(分)", "币种", "阶段", "状态", "创建时间"])
        for o in data:
            w.writerow([o.get("opportunityId"), o.get("customerId"), o.get("title"), o.get("amountCents"), o.get("currency"), o.get("stage"), o.get("status"), o.get("createdAt")])
        return Response(
            content=buf.getvalue().encode("utf-8-sig"),
            media_type="text/csv; charset=utf-8-sig",
            headers={"Content-Disposition": "attachment; filename=opportunities.csv"},
        )
    return {"data": data, "total": total, "page": page, "pageSize": pageSize}


@router.post("/import", status_code=202)
async def import_opportunities_batch(
    body: dict,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    _auth=Depends(require_auth),
):
    """批量导入商机。body.items 每项 {customerId, title, amountCents?, currency?, stage?}；单次建议不超过 1000 条。"""
    items = body.get("items") or body.get("data") or []
    if not items or not isinstance(items, list):
        raise HTTPException(status_code=400, detail={"code": "BAD_REQUEST", "message": "请提供 items 数组", "details": "请求体需包含 items 或 data 字段", "requestId": get_request_id()})
    if len(items) > 2000:
        raise HTTPException(status_code=400, detail={"code": "BAD_REQUEST", "message": "单次导入不超过 2000 条", "details": "请分批导入以保证系统稳定", "requestId": get_request_id()})
    created, errors = [], []
    for i, row in enumerate(items):
        customer_id = (row.get("customerId") or "").strip()
        title = (row.get("title") or "").strip()
        if not customer_id or not title:
            errors.append({"index": i, "reason": "customerId 与 title 必填"})
            continue
        if not db.customer_get(tenant_id, customer_id):
            errors.append({"index": i, "reason": "客户不存在", "customerId": customer_id})
            continue
        try:
            o = db.opportunity_create(
                tenant_id, customer_id, title,
                amount_cents=int(row.get("amountCents", 0)),
                currency=(row.get("currency") or "CNY").strip(),
                stage=int(row.get("stage", 1)),
            )
            created.append({"index": i, "opportunityId": o["opportunityId"], "title": title})
        except Exception as e:
            errors.append({"index": i, "reason": str(e), "title": title})
    return {"accepted": True, "created": len(created), "errors": len(errors), "details": created, "errorsDetail": errors}


@router.get("/{opportunity_id}")
async def get_opportunity(
    opportunity_id: str,
    tenant_id: str = Depends(get_tenant_id),
    _auth=Depends(require_auth),
):
    o = db.opportunity_get(tenant_id, opportunity_id)
    if not o:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "商机不存在", "details": "", "requestId": get_request_id()})
    return o


@router.post("", status_code=201)
async def create_opportunity(
    body: OpportunityCreate,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    _auth=Depends(require_auth),
):
    rid = request.headers.get("X-Request-ID", "").strip()
    if not rid:
        raise HTTPException(status_code=400, detail={"code": "BAD_REQUEST", "message": "POST 必须包含 X-Request-ID", "details": "", "requestId": get_request_id()})
    existing = db.idempotent_get(rid)
    if existing and existing[0] == "opportunity":
        o = db.opportunity_get(tenant_id, existing[1])
        if o:
            raise HTTPException(status_code=409, detail={"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "details": "", "requestId": rid})
    o = db.opportunity_create(tenant_id, body.customerId, body.title.strip(), body.amountCents, body.currency, body.stage)
    db.idempotent_set(rid, "opportunity", o["opportunityId"])
    db.audit_append(tenant_id, _user_id(request), "opportunity.create", "opportunity", o["opportunityId"], rid)
    return o


@router.patch("/{opportunity_id}")
async def update_opportunity(
    opportunity_id: str,
    body: OpportunityUpdate,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    _auth=Depends(require_auth),
):
    rid = request.headers.get("X-Request-ID", "").strip()
    if not rid:
        raise HTTPException(status_code=400, detail={"code": "BAD_REQUEST", "message": "PATCH 必须包含 X-Request-ID", "details": "", "requestId": get_request_id()})
    o = db.opportunity_update(tenant_id, opportunity_id, body.title, body.amountCents, body.stage)
    if not o:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "商机不存在", "details": "请检查商机编号或刷新列表后重试", "requestId": rid})
    db.audit_append(tenant_id, _user_id(request), "opportunity.update", "opportunity", opportunity_id, rid)
    return o


@router.delete("/{opportunity_id}", status_code=204)
async def delete_opportunity(
    opportunity_id: str,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    _auth=Depends(require_auth),
):
    ok = db.opportunity_delete(tenant_id, opportunity_id)
    if not ok:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "商机不存在", "details": "该商机可能已被删除，请刷新列表", "requestId": get_request_id()})
    db.audit_append(tenant_id, _user_id(request), "opportunity.delete", "opportunity", opportunity_id, get_request_id())
