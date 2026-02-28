from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from .. import database as db
from ..dependencies import get_tenant_id, get_request_id, require_auth
from ..schemas import ContactCreate, ContactUpdate, ListResponse
from ..masking import apply_contact_masking

router = APIRouter()


@router.get("", response_model=ListResponse)
async def list_contacts(
    customerId: Optional[str] = None,
    page: int = 1,
    pageSize: int = 20,
    tenant_id: str = Depends(get_tenant_id),
    _auth=Depends(require_auth),
):
    data, total = db.contact_list(tenant_id, customer_id=customerId, page=page, page_size=pageSize)
    data = [apply_contact_masking(d) for d in data]
    return ListResponse(data=data, total=total)


@router.get("/{contact_id}")
async def get_contact(
    contact_id: str,
    tenant_id: str = Depends(get_tenant_id),
    _auth=Depends(require_auth),
):
    c = db.contact_get(tenant_id, contact_id)
    if not c:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "联系人不存在", "details": "", "requestId": get_request_id()})
    return apply_contact_masking(c)


@router.post("", status_code=201)
async def create_contact(
    body: ContactCreate,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    _auth=Depends(require_auth),
):
    rid = request.headers.get("X-Request-ID", "").strip()
    if not rid:
        raise HTTPException(status_code=400, detail={"code": "BAD_REQUEST", "message": "POST 必须包含 X-Request-ID", "details": "", "requestId": get_request_id()})
    existing = db.idempotent_get(rid)
    if existing and existing[0] == "contact":
        c = db.contact_get(tenant_id, existing[1])
        if c:
            raise HTTPException(status_code=409, detail={"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "details": "", "requestId": rid})
    c = db.contact_create(tenant_id, body.customerId, body.name.strip(), body.phone, body.email, body.isPrimary)
    db.idempotent_set(rid, "contact", c["contactId"])
    return apply_contact_masking(c)


@router.patch("/{contact_id}")
async def update_contact(
    contact_id: str,
    body: ContactUpdate,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    _auth=Depends(require_auth),
):
    rid = request.headers.get("X-Request-ID", "").strip()
    if not rid:
        raise HTTPException(status_code=400, detail={"code": "BAD_REQUEST", "message": "PATCH 必须包含 X-Request-ID", "details": "", "requestId": get_request_id()})
    c = db.contact_update(tenant_id, contact_id, body.name, body.phone, body.email, body.isPrimary)
    if not c:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "联系人不存在", "details": "", "requestId": rid})
    return c


@router.delete("/{contact_id}", status_code=204)
async def delete_contact(
    contact_id: str,
    tenant_id: str = Depends(get_tenant_id),
    _auth=Depends(require_auth),
):
    ok = db.contact_delete(tenant_id, contact_id)
    if not ok:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "联系人不存在", "details": "", "requestId": get_request_id()})
