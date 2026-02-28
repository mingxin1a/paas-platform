# 《接口设计说明书》统一请求/响应与错误码
from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel


class ErrorBody(BaseModel):
    code: str
    message: str
    details: str = ""
    requestId: str = ""


# ---------- Customer ----------
class CustomerCreate(BaseModel):
    name: str
    contactPhone: Optional[str] = None
    contactEmail: Optional[str] = None


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    contactPhone: Optional[str] = None
    contactEmail: Optional[str] = None


# ---------- Contact ----------
class ContactCreate(BaseModel):
    customerId: str
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    isPrimary: bool = False


class ContactUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    isPrimary: Optional[bool] = None


# ---------- Opportunity ----------
class OpportunityCreate(BaseModel):
    customerId: str
    title: str
    amountCents: int = 0
    currency: str = "CNY"
    stage: int = 1


class OpportunityUpdate(BaseModel):
    title: Optional[str] = None
    amountCents: Optional[int] = None
    stage: Optional[int] = None


# ---------- Follow-up ----------
class FollowUpCreate(BaseModel):
    content: str
    customerId: Optional[str] = None
    opportunityId: Optional[str] = None
    contactId: Optional[str] = None
    followUpType: str = "call"


class FollowUpUpdate(BaseModel):
    content: Optional[str] = None


# ---------- Contract 合同 ----------
class ContractCreate(BaseModel):
    customerId: str
    contractNo: str
    amountCents: int
    opportunityId: Optional[str] = None
    currency: str = "CNY"
    signedAt: Optional[str] = None


# ---------- Payment 回款 ----------
class PaymentCreate(BaseModel):
    contractId: str
    amountCents: int
    paymentAt: str
    remark: Optional[str] = None


# ---------- List response ----------
class ListResponse(BaseModel):
    data: List[Any]
    total: int
