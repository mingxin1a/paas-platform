# 商用化：合同管理，创建幂等，合同编号重复商用提示
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from .. import database as db
from ..dependencies import get_tenant_id, get_request_id, require_auth
from ..schemas import ContractCreate, ListResponse
from ..masking import apply_contract_masking

router = APIRouter()


@router.get("", response_model=ListResponse)
async def list_contracts(
    customerId: Optional[str] = None,
    page: int = 1,
    pageSize: int = 20,
    tenant_id: str = Depends(get_tenant_id),
    _auth=Depends(require_auth),
):
    data, total = db.contract_list(tenant_id, customer_id=customerId, page=page, page_size=pageSize)
    data = [apply_contract_masking(d) for d in data]
    return ListResponse(data=data, total=total)


@router.patch("/{contract_id}")
async def update_contract_status(
    contract_id: str,
    body: dict,
    tenant_id: str = Depends(get_tenant_id),
    _auth=Depends(require_auth),
):
    """联动回写：审批完成后更新合同状态。body { "status": 1|2 }。"""
    status = body.get("status")
    if status is None:
        raise HTTPException(status_code=400, detail={"code": "BAD_REQUEST", "message": "status 必填", "details": "", "requestId": get_request_id()})
    c = db.contract_update_status(tenant_id, contract_id, int(status))
    if not c:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "合同不存在", "details": "", "requestId": get_request_id()})
    return apply_contract_masking(c)


@router.get("/{contract_id}")
async def get_contract(
    contract_id: str,
    tenant_id: str = Depends(get_tenant_id),
    _auth=Depends(require_auth),
):
    c = db.contract_get(tenant_id, contract_id)
    if not c:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "合同不存在", "details": "", "requestId": get_request_id()},
        )
    return apply_contract_masking(c)


@router.post("", status_code=201)
async def create_contract(
    body: ContractCreate,
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
    if existing and existing[0] == "contract":
        c = db.contract_get(tenant_id, existing[1])
        if c:
            raise HTTPException(status_code=409, detail={"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突", "details": "", "requestId": rid})
    if db.contract_exists_by_no(tenant_id, body.contractNo.strip()):
        raise HTTPException(
            status_code=400,
            detail={"code": "BUSINESS_RULE_VIOLATION", "message": "合同编号已存在", "details": "请使用其他合同编号", "requestId": rid},
        )
    c = db.contract_create(
        tenant_id, body.customerId, body.contractNo.strip(), body.amountCents,
        opportunity_id=body.opportunityId, currency=body.currency, signed_at=body.signedAt,
    )
    db.idempotent_set(rid, "contract", c["contractId"])
    if body.signedAt:
        try:
            from ..event_publisher import publish
            publish(
                "crm.contract.signed",
                {
                    "contractId": c["contractId"],
                    "customerId": c["customerId"],
                    "contractNo": c["contractNo"],
                    "amountCents": c["amountCents"],
                    "currency": c.get("currency", "CNY"),
                    "tenantId": tenant_id,
                    "opportunityId": c.get("opportunityId") or "",
                    "signedAt": c.get("signedAt") or "",
                },
                trace_id=rid,
            )
        except Exception:
            pass
    return apply_contract_masking(c)
