# 示例路由：复制模板后替换为 orders、work_orders 等资源
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from api.schemas import ItemCreate, ItemUpdate, ListResponse
from api.middleware import get_tenant_id, get_request_id, require_auth, require_request_id
from service import ItemService

router = APIRouter()


@router.get("", response_model=ListResponse)
async def list_items(
    page: int = 1,
    pageSize: int = 20,
    tenant_id: str = Depends(get_tenant_id),
    _auth=Depends(require_auth),
):
    data, total = ItemService.list(tenant_id, page=page, page_size=pageSize)
    return ListResponse(data=data, total=total)


@router.get("/{item_id}")
async def get_item(
    item_id: str,
    tenant_id: str = Depends(get_tenant_id),
    _auth=Depends(require_auth),
):
    obj = ItemService.get(tenant_id, item_id)
    if not obj:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "资源不存在", "details": "", "requestId": get_request_id()})
    return obj


@router.post("", status_code=201)
async def create_item(
    body: ItemCreate,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    _auth=Depends(require_auth),
):
    require_request_id(request, "POST")
    rid = request.headers.get("X-Request-ID", "").strip()
    obj, created = ItemService.create(tenant_id, body.name.strip(), rid)
    if not created:
        raise HTTPException(status_code=409, detail={"code": "IDEMPOTENT_CONFLICT", "message": "幂等冲突，已存在同 X-Request-ID 的资源", "details": "", "requestId": rid})
    return obj


@router.patch("/{item_id}")
async def update_item(
    item_id: str,
    body: ItemUpdate,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    _auth=Depends(require_auth),
):
    require_request_id(request, "PATCH")
    obj = ItemService.update(tenant_id, item_id, body.name)
    if not obj:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "资源不存在", "details": "", "requestId": get_request_id()})
    return obj


@router.delete("/{item_id}", status_code=204)
async def delete_item(
    item_id: str,
    tenant_id: str = Depends(get_tenant_id),
    _auth=Depends(require_auth),
):
    ok = ItemService.delete(tenant_id, item_id)
    if not ok:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "资源不存在", "details": "", "requestId": get_request_id()})
