# 商用化：回款记录，创建幂等
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from .. import database as db
from ..dependencies import get_tenant_id, get_request_id, require_auth
from ..schemas import PaymentCreate, ListResponse

router = APIRouter()


@router.get("", response_model=ListResponse)
async def list_payments(
    contractId: Optional[str] = None,
    page: int = 1,
    pageSize: int = 20,
    tenant_id: str = Depends(get_tenant_id),
    _auth=Depends(require_auth),
):
    data, total = db.payment_list(tenant_id, contract_id=contractId, page=page, page_size=pageSize)
    return ListResponse(data=data, total=total)


@router.post("", status_code=201)
async def create_payment(
    body: PaymentCreate,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    _auth=Depends(require_auth),
):
    rid = request.headers.get("X-Request-ID", "").strip()
    if not rid:
        raise HTTPException(
            status_code=400,
            detail={"code": "BAD_REQUEST", "message": "POST 必须包含 X-Request-ID", "details": "", "requestId": get_request_id()},
        )
    existing = db.idempotent_get(rid)
    if existing and existing[0] == "payment":
        existing_p = db.payment_get(tenant_id, existing[1])
        if existing_p:
            return existing_p
    contract = db.contract_get(tenant_id, body.contractId)
    if not contract:
        raise HTTPException(
            status_code=400,
            detail={"code": "BUSINESS_RULE_VIOLATION", "message": "合同不存在", "details": "请先创建合同再登记回款", "requestId": rid},
        )
    p = db.payment_create(tenant_id, body.contractId, body.amountCents, body.paymentAt, body.remark)
    db.idempotent_set(rid, "payment", p["paymentId"])
    return p
