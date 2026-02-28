# 《接口设计说明书》3.1.3：统一错误格式 + 请求/响应模型
from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel


# ---------- 统一错误响应（code, message, details, requestId） ----------
class ErrorResponse(BaseModel):
    code: str
    message: str
    details: str = ""
    requestId: str = ""


# ---------- 统一列表响应 ----------
class ListResponse(BaseModel):
    data: List[Any]
    total: int


# ---------- 示例资源：复制模板后替换为订单、工单等 ----------
class ItemCreate(BaseModel):
    name: str


class ItemUpdate(BaseModel):
    name: Optional[str] = None
