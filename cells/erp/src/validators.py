"""
ERP 请求校验：必填项、数据格式、业务规则。
统一错误码：VALIDATION_ERROR, BUSINESS_RULE_VIOLATION。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# 必填字段配置：接口标识 -> (字段名, 中文描述)
REQUIRED_FIELDS: Dict[str, List[Tuple[str, str]]] = {
    "orders_create": [("customerId", "客户ID"), ("totalAmountCents", "订单金额(分)")],
    "gl_accounts_create": [("accountCode", "科目代码"), ("name", "科目名称")],
    "gl_entries_create": [("documentNo", "凭证号"), ("postingDate", "过账日期"), ("lines", "分录行")],
    "ar_create": [("customerId", "客户ID"), ("documentNo", "凭证号"), ("amountCents", "金额(分)")],
    "ap_create": [("supplierId", "供应商ID"), ("documentNo", "凭证号"), ("amountCents", "金额(分)")],
    "mm_materials_create": [("materialCode", "物料编码"), ("name", "物料名称")],
    "mm_po_create": [("supplierId", "供应商ID"), ("documentNo", "采购订单凭证号")],
    "pp_bom_create": [("productMaterialId", "产品物料ID")],
    "pp_wo_create": [("bomId", "BOM ID"), ("productMaterialId", "产品物料ID"), ("plannedQuantity", "计划数量")],
    "ar_receipt": [("amountCents", "收款金额(分)")],
    "ap_payment": [("amountCents", "付款金额(分)")],
    "pp_wo_report": [("completedQuantity", "完成数量")],
}


def validate_required(body: Dict[str, Any], endpoint: str) -> Optional[str]:
    """
    校验必填项。返回 None 表示通过，否则返回错误描述。
    """
    if endpoint not in REQUIRED_FIELDS:
        return None
    for field, label in REQUIRED_FIELDS[endpoint]:
        val = body.get(field)
        if val is None or (isinstance(val, str) and (val.strip() if val else "") == ""):
            return f"必填项缺失或为空: {label}({field})"
        if field in ("totalAmountCents", "amountCents", "accountType") and isinstance(val, int) and val < 0:
            return f"{label}不能为负数"
        if field in ("plannedQuantity", "completedQuantity") and isinstance(val, (int, float)) and val <= 0:
            return f"{label}必须大于0"
    return None


def validate_gl_entry_lines(lines: List[Dict]) -> Optional[str]:
    """校验分录借贷平衡。返回 None 表示通过。"""
    if not lines:
        return "分录行不能为空"
    total_d = sum(l.get("debitCents") or 0 for l in lines)
    total_c = sum(l.get("creditCents") or 0 for l in lines)
    if total_d != total_c:
        return f"借贷不平衡: 借方合计={total_d}, 贷方合计={total_c}"
    return None


def validate_receipt_amount(amount_cents: int, invoice_amount: int, paid_amount: int) -> Optional[str]:
    """校验收款金额：大于0且不超过待收金额。"""
    if amount_cents <= 0:
        return "收款金额必须大于0"
    remaining = invoice_amount - paid_amount
    if amount_cents > remaining:
        return f"收款金额不能超过待收金额: 待收={remaining}分, 本次={amount_cents}分"
    return None


def validate_payment_amount(amount_cents: int, invoice_amount: int, paid_amount: int) -> Optional[str]:
    """校验付款金额：大于0且不超过待付金额。"""
    if amount_cents <= 0:
        return "付款金额必须大于0"
    remaining = invoice_amount - paid_amount
    if amount_cents > remaining:
        return f"付款金额不能超过待付金额: 待付={remaining}分, 本次={amount_cents}分"
    return None
