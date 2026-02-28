from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from .. import database as db
from ..dependencies import get_tenant_id, get_request_id, require_auth
from ..schemas import FollowUpCreate, FollowUpUpdate, ListResponse

router = APIRouter()


@router.get("", response_model=ListResponse)
async def list_follow_ups(
    customerId: Optional[str] = None,
    opportunityId: Optional[str] = None,
    page: int = 1,
    pageSize: int = 20,
    tenant_id: str = Depends(get_tenant_id),
    _auth=Depends(require_auth),
):
    data, total = db.follow_up_list(tenant_id, customer_id=customerId, opportunity_id=opportunityId, page=page, page_size=pageSize)
    return ListResponse(data=data, total=total)


@router.get("/{follow_up_id}")
async def get_follow_up(
    follow_up_id: str,
    tenant_id: str = Depends(get_tenant_id),
    _auth=Depends(require_auth),
):
    f = db.follow_up_get(tenant_id, follow_up_id)
    if not f:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "跟进记录不存在", "details": "", "requestId": get_request_id()})
    return f


@router.post("", status_code=201)
async def create_follow_up(
    body: FollowUpCreate,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    _auth=Depends(require_auth),
):
    rid = request.headers.get("X-Request-ID", "").strip()
    if not rid:
        raise HTTPException(status_code=400, detail={"code": "BAD_REQUEST", "message": "POST 必须包含 X-Request-ID", "details": "", "requestId": get_request_id()})
    existing = db.idempotent_get(rid)
    if existing and existing[0] == "follow_up":
        f = db.follow_up_get(tenant_id, existing[1])
        if f:
            raise HTTPException(status_code=409, detail={"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "details": "", "requestId": rid})
    f = db.follow_up_create(tenant_id, body.content.strip(), body.customerId, body.opportunityId, body.contactId, body.followUpType or "call")
    db.idempotent_set(rid, "follow_up", f["followUpId"])
    return f


@router.patch("/{follow_up_id}")
async def update_follow_up(
    follow_up_id: str,
    body: FollowUpUpdate,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    _auth=Depends(require_auth),
):
    rid = request.headers.get("X-Request-ID", "").strip()
    if not rid:
        raise HTTPException(status_code=400, detail={"code": "BAD_REQUEST", "message": "PATCH 必须包含 X-Request-ID", "details": "", "requestId": get_request_id()})
    f = db.follow_up_update(tenant_id, follow_up_id, body.content)
    if not f:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "跟进记录不存在", "details": "", "requestId": rid})
    return f


@router.delete("/{follow_up_id}", status_code=204)
async def delete_follow_up(
    follow_up_id: str,
    tenant_id: str = Depends(get_tenant_id),
    _auth=Depends(require_auth),
):
    ok = db.follow_up_delete(tenant_id, follow_up_id)
    if not ok:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "跟进记录不存在", "details": "", "requestId": get_request_id()})
