# 商用化：客户敏感信息脱敏展示（手机号/合同金额）
# 存储层可存明文或加密；展示时统一经本模块脱敏，符合《接口设计说明书》与合规要求
from __future__ import annotations

import re
from typing import Any, Dict, Optional


def mask_phone(phone: Optional[str]) -> str:
    """手机号脱敏：13812345678 -> 138****5678；不足 7 位不脱敏。"""
    if not phone or not isinstance(phone, str):
        return ""
    s = re.sub(r"\D", "", phone)
    if len(s) < 7:
        return "***"
    return s[:3] + "****" + s[-4:]


def mask_amount_cents(amount_cents: Optional[int], mask: bool = False) -> Any:
    """合同/回款金额：若不脱敏则返回原值；若 mask=True 则返回脱敏描述（如「已脱敏」）。"""
    if mask:
        return "***"
    return amount_cents if amount_cents is not None else 0


def apply_customer_masking(row: Dict[str, Any], mask_phone_field: bool = True) -> Dict[str, Any]:
    """对客户/联系人返回体应用脱敏：contactPhone/phone 脱敏。"""
    out = dict(row)
    if mask_phone_field and out.get("contactPhone"):
        out["contactPhone"] = mask_phone(out["contactPhone"])
    return out


def apply_contact_masking(row: Dict[str, Any]) -> Dict[str, Any]:
    """对联系人返回体应用脱敏：phone 脱敏。"""
    out = dict(row)
    if out.get("phone"):
        out["phone"] = mask_phone(out["phone"])
    return out


def apply_contract_masking(row: Dict[str, Any], mask_amount: bool = False) -> Dict[str, Any]:
    """对合同返回体应用脱敏：可选金额脱敏。"""
    out = dict(row)
    if mask_amount and "amountCents" in out:
        out["amountCents"] = mask_amount_cents(out.get("amountCents"), mask=True)
    return out
