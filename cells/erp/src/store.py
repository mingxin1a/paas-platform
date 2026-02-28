"""
ERP 内存存储：订单、GL、AR、AP、MM、PP。金额统一分（Long），多租户 tenant_id。
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())

def _id() -> str:
    return str(uuid.uuid4()).replace("-", "")[:16]


class ERPStore:
    def __init__(self) -> None:
        self.orders: Dict[str, Dict] = {}
        self.gl_accounts: Dict[str, Dict] = {}
        self.gl_entries: Dict[str, Dict] = {}
        self.gl_lines: List[Dict] = []
        self.ar_invoices: Dict[str, Dict] = {}
        self.ap_invoices: Dict[str, Dict] = {}
        self.materials: Dict[str, Dict] = {}
        self.purchase_orders: Dict[str, Dict] = {}
        self.boms: Dict[str, Dict] = {}
        self.work_orders: Dict[str, Dict] = {}
        self.purchase_requisitions: Dict[str, Dict] = {}
        self._idem: Dict[str, str] = {}
        self._idem_receipt: Dict[str, Dict] = {}  # X-Request-ID -> 收款后发票快照
        self._idem_payment: Dict[str, Dict] = {}  # X-Request-ID -> 付款后发票快照
        self._audit_log: List[Dict] = []

    def idem_get(self, k: str) -> Optional[str]:
        return self._idem.get(k)
    def idem_set(self, k: str, v: str) -> None:
        self._idem[k] = v

    def _by_tenant(self, d: Dict[str, Dict], tenant_id: str, exclude_deleted: bool = True) -> List[Dict]:
        out = [v for v in d.values() if v.get("tenantId") == tenant_id]
        if exclude_deleted:
            out = [v for v in out if not v.get("deletedAt")]
        return out

    def _paginate(self, items: List[Dict], page: int, page_size: int) -> Tuple[List[Dict], int]:
        total = len(items)
        if page_size <= 0:
            page_size = 20
        if page <= 0:
            page = 1
        start = (page - 1) * page_size
        return items[start : start + page_size], total

    def audit_append(
        self,
        tenant_id: str,
        user_id: str,
        operation_type: str,
        operation_result: int,
        trace_id: str = "",
        resource_type: str = "",
        resource_id: str = "",
    ) -> None:
        """写入审计日志（内存，对接 DB 时可改为写 audit_log 表）。operation_result: 1 成功 0 失败。"""
        self._audit_log.append({
            "tenantId": tenant_id,
            "userId": user_id,
            "operationType": operation_type,
            "operationResult": operation_result,
            "traceId": trace_id or "",
            "resourceType": resource_type or "",
            "resourceId": resource_id or "",
            "occurredAt": _ts(),
        })

    def audit_list(
        self, tenant_id: str, page: int = 1, page_size: int = 50, resource_type: Optional[str] = None
    ) -> Tuple[List[Dict], int]:
        """分页查询审计日志，可按 resource_type 筛选。"""
        out = [e for e in self._audit_log if e.get("tenantId") == tenant_id]
        if resource_type:
            out = [e for e in out if (e.get("resourceType") or "") == resource_type]
        total = len(out)
        out = sorted(out, key=lambda x: x.get("occurredAt", ""), reverse=True)
        start = (page - 1) * page_size
        return out[start : start + page_size], total

    def order_list(self, tenant_id: str, page: int = 1, page_size: int = 20) -> Tuple[List[Dict], int]:
        items = self._by_tenant(self.orders, tenant_id)
        return self._paginate(items, page, page_size)
    def order_get(self, tenant_id: str, order_id: str) -> Optional[Dict]:
        o = self.orders.get(order_id)
        if not o or o.get("tenantId") != tenant_id or o.get("deletedAt"):
            return None
        return dict(o)
    def order_soft_delete(self, tenant_id: str, order_id: str) -> bool:
        o = self.orders.get(order_id)
        if not o or o.get("tenantId") != tenant_id or o.get("deletedAt"):
            return False
        o["deletedAt"] = _ts()
        return True
    def order_create(self, tenant_id: str, customer_id: str, total_amount_cents: int, currency: str = "CNY", order_lines: Optional[List[Dict]] = None) -> Dict:
        oid = _id()
        now = _ts()
        o = {"orderId": oid, "tenantId": tenant_id, "customerId": customer_id, "orderStatus": 1, "totalAmountCents": total_amount_cents, "currency": currency, "createdAt": now, "updatedAt": now}
        if order_lines:
            o["orderLines"] = [{"productSku": ln.get("productSku", ""), "quantity": float(ln.get("quantity", 1))} for ln in order_lines]
        self.orders[oid] = o
        return o
    def order_update_status(self, tenant_id: str, order_id: str, order_status: int) -> Optional[Dict]:
        o = self.orders.get(order_id)
        if not o or o.get("tenantId") != tenant_id or o.get("deletedAt"):
            return None
        o["orderStatus"] = order_status
        o["updatedAt"] = _ts()
        return o

    def gl_account_list(self, tenant_id: str, page: int = 1, page_size: int = 20) -> Tuple[List[Dict], int]:
        items = self._by_tenant(self.gl_accounts, tenant_id)
        return self._paginate(items, page, page_size)
    def gl_account_get(self, tenant_id: str, account_code: str) -> Optional[Dict]:
        a = self.gl_accounts.get(f"{tenant_id}:{account_code}")
        if not a or a.get("tenantId") != tenant_id or a.get("deletedAt"):
            return None
        return dict(a)
    def gl_account_soft_delete(self, tenant_id: str, account_code: str) -> bool:
        a = self.gl_accounts.get(f"{tenant_id}:{account_code}")
        if not a or a.get("tenantId") != tenant_id or a.get("deletedAt"):
            return False
        a["deletedAt"] = _ts()
        return True
    def gl_account_create(self, tenant_id: str, account_code: str, name: str, account_type: int) -> Dict:
        key = f"{tenant_id}:{account_code}"
        now = _ts()
        a = {"accountCode": account_code, "tenantId": tenant_id, "name": name, "accountType": account_type, "createdAt": now}
        self.gl_accounts[key] = a
        return a
    def gl_entry_list(self, tenant_id: str) -> List[Dict]:
        return self._by_tenant(self.gl_entries, tenant_id)
    def gl_entry_get(self, tenant_id: str, entry_id: str) -> Optional[Dict]:
        e = self.gl_entries.get(entry_id)
        if not e or e.get("tenantId") != tenant_id or e.get("deletedAt"):
            return None
        lines = [l for l in self.gl_lines if l.get("entryId") == entry_id and l.get("tenantId") == tenant_id]
        out = dict(e)
        out["lines"] = lines
        return out
    def gl_entry_create(self, tenant_id: str, document_no: str, posting_date: str, lines: List[Dict]) -> Dict:
        eid = _id()
        now = _ts()
        total_d = sum(l.get("debitCents", 0) for l in lines)
        total_c = sum(l.get("creditCents", 0) for l in lines)
        e = {"entryId": eid, "tenantId": tenant_id, "documentNo": document_no, "postingDate": posting_date, "totalDebitCents": total_d, "totalCreditCents": total_c, "status": 1, "createdAt": now}
        self.gl_entries[eid] = e
        for l in lines:
            l["entryId"] = eid
            l["tenantId"] = tenant_id
            self.gl_lines.append(l)
        return e

    def ar_list(self, tenant_id: str, page: int = 1, page_size: int = 20) -> Tuple[List[Dict], int]:
        items = self._by_tenant(self.ar_invoices, tenant_id)
        return self._paginate(items, page, page_size)
    def ar_get(self, tenant_id: str, invoice_id: str) -> Optional[Dict]:
        inv = self.ar_invoices.get(invoice_id)
        if not inv or inv.get("tenantId") != tenant_id or inv.get("deletedAt"):
            return None
        return dict(inv)
    def ar_soft_delete(self, tenant_id: str, invoice_id: str) -> bool:
        inv = self.ar_invoices.get(invoice_id)
        if not inv or inv.get("tenantId") != tenant_id or inv.get("deletedAt"):
            return False
        inv["deletedAt"] = _ts()
        return True
    def ar_create(self, tenant_id: str, customer_id: str, document_no: str, amount_cents: int, currency: str = "CNY", due_date: Optional[str] = None) -> Dict:
        iid = _id()
        now = _ts()
        inv = {"invoiceId": iid, "tenantId": tenant_id, "customerId": customer_id, "documentNo": document_no, "amountCents": amount_cents, "paidAmountCents": 0, "currency": currency, "status": 1, "dueDate": due_date or "", "createdAt": now}
        self.ar_invoices[iid] = inv
        return inv
    def ap_list(self, tenant_id: str, page: int = 1, page_size: int = 20) -> Tuple[List[Dict], int]:
        items = self._by_tenant(self.ap_invoices, tenant_id)
        return self._paginate(items, page, page_size)
    def ap_get(self, tenant_id: str, invoice_id: str) -> Optional[Dict]:
        inv = self.ap_invoices.get(invoice_id)
        if not inv or inv.get("tenantId") != tenant_id or inv.get("deletedAt"):
            return None
        return dict(inv)
    def ap_soft_delete(self, tenant_id: str, invoice_id: str) -> bool:
        inv = self.ap_invoices.get(invoice_id)
        if not inv or inv.get("tenantId") != tenant_id or inv.get("deletedAt"):
            return False
        inv["deletedAt"] = _ts()
        return True
    def ap_create(self, tenant_id: str, supplier_id: str, document_no: str, amount_cents: int, currency: str = "CNY", due_date: Optional[str] = None) -> Dict:
        iid = _id()
        now = _ts()
        inv = {"invoiceId": iid, "tenantId": tenant_id, "supplierId": supplier_id, "documentNo": document_no, "amountCents": amount_cents, "paidAmountCents": 0, "currency": currency, "status": 1, "dueDate": due_date or "", "createdAt": now}
        self.ap_invoices[iid] = inv
        return inv

    def material_list(self, tenant_id: str, page: int = 1, page_size: int = 20) -> Tuple[List[Dict], int]:
        items = self._by_tenant(self.materials, tenant_id)
        return self._paginate(items, page, page_size)
    def material_get(self, tenant_id: str, material_id: str) -> Optional[Dict]:
        m = self.materials.get(material_id)
        if not m or m.get("tenantId") != tenant_id or m.get("deletedAt"):
            return None
        return dict(m)
    def material_soft_delete(self, tenant_id: str, material_id: str) -> bool:
        m = self.materials.get(material_id)
        if not m or m.get("tenantId") != tenant_id or m.get("deletedAt"):
            return False
        m["deletedAt"] = _ts()
        return True
    def material_create(self, tenant_id: str, material_code: str, name: str, unit: str = "PCS") -> Dict:
        mid = _id()
        now = _ts()
        m = {"materialId": mid, "tenantId": tenant_id, "materialCode": material_code, "name": name, "unit": unit, "createdAt": now}
        self.materials[mid] = m
        return m
    def po_list(self, tenant_id: str, page: int = 1, page_size: int = 20) -> Tuple[List[Dict], int]:
        items = self._by_tenant(self.purchase_orders, tenant_id)
        return self._paginate(items, page, page_size)
    def po_get(self, tenant_id: str, po_id: str) -> Optional[Dict]:
        po = self.purchase_orders.get(po_id)
        if not po or po.get("tenantId") != tenant_id or po.get("deletedAt"):
            return None
        return dict(po)
    def po_soft_delete(self, tenant_id: str, po_id: str) -> bool:
        po = self.purchase_orders.get(po_id)
        if not po or po.get("tenantId") != tenant_id or po.get("deletedAt"):
            return False
        po["deletedAt"] = _ts()
        return True
    def po_create(self, tenant_id: str, supplier_id: str, document_no: str, total_amount_cents: int = 0) -> Dict:
        pid = _id()
        now = _ts()
        po = {"poId": pid, "tenantId": tenant_id, "supplierId": supplier_id, "documentNo": document_no, "status": 1, "totalAmountCents": total_amount_cents, "createdAt": now, "updatedAt": now}
        self.purchase_orders[pid] = po
        return po
    def po_update_status(self, tenant_id: str, po_id: str, status: int) -> Optional[Dict]:
        po = self.purchase_orders.get(po_id)
        if not po or po.get("tenantId") != tenant_id or po.get("deletedAt"):
            return None
        po["status"] = status
        po["updatedAt"] = _ts()
        return po

    def requisition_list(self, tenant_id: str, page: int = 1, page_size: int = 20) -> Tuple[List[Dict], int]:
        items = self._by_tenant(self.purchase_requisitions, tenant_id)
        return self._paginate(items, page, page_size)

    def requisition_get(self, tenant_id: str, req_id: str) -> Optional[Dict]:
        r = self.purchase_requisitions.get(req_id)
        if not r or r.get("tenantId") != tenant_id:
            return None
        return dict(r)

    def requisition_create(self, tenant_id: str, demand_desc: str = "", total_amount_cents: int = 0) -> Dict:
        rid = _id()
        now = _ts()
        req = {"requisitionId": rid, "tenantId": tenant_id, "demandDesc": demand_desc, "totalAmountCents": total_amount_cents, "status": 1, "createdAt": now}
        self.purchase_requisitions[rid] = req
        return req

    def bom_list(self, tenant_id: str, page: int = 1, page_size: int = 20) -> Tuple[List[Dict], int]:
        items = self._by_tenant(self.boms, tenant_id)
        return self._paginate(items, page, page_size)
    def bom_get(self, tenant_id: str, bom_id: str) -> Optional[Dict]:
        b = self.boms.get(bom_id)
        if not b or b.get("tenantId") != tenant_id or b.get("deletedAt"):
            return None
        return dict(b)
    def bom_soft_delete(self, tenant_id: str, bom_id: str) -> bool:
        b = self.boms.get(bom_id)
        if not b or b.get("tenantId") != tenant_id or b.get("deletedAt"):
            return False
        b["deletedAt"] = _ts()
        return True
    def bom_create(self, tenant_id: str, product_material_id: str, version: int = 1) -> Dict:
        bid = _id()
        now = _ts()
        b = {"bomId": bid, "tenantId": tenant_id, "productMaterialId": product_material_id, "version": version, "status": 1, "createdAt": now}
        self.boms[bid] = b
        return b
    def work_order_list(self, tenant_id: str, page: int = 1, page_size: int = 20) -> Tuple[List[Dict], int]:
        items = self._by_tenant(self.work_orders, tenant_id)
        return self._paginate(items, page, page_size)
    def work_order_get(self, tenant_id: str, work_order_id: str) -> Optional[Dict]:
        w = self.work_orders.get(work_order_id)
        if not w or w.get("tenantId") != tenant_id or w.get("deletedAt"):
            return None
        return dict(w)
    def work_order_soft_delete(self, tenant_id: str, work_order_id: str) -> bool:
        w = self.work_orders.get(work_order_id)
        if not w or w.get("tenantId") != tenant_id or w.get("deletedAt"):
            return False
        w["deletedAt"] = _ts()
        return True
    def work_order_create(self, tenant_id: str, bom_id: str, product_material_id: str, planned_quantity: float) -> Dict:
        wid = _id()
        now = _ts()
        w = {"workOrderId": wid, "tenantId": tenant_id, "bomId": bom_id, "productMaterialId": product_material_id, "plannedQuantity": planned_quantity, "completedQuantity": 0, "status": 1, "materialCostCents": 0, "laborCostCents": 0, "createdAt": now, "updatedAt": now}
        self.work_orders[wid] = w
        return w

    def work_order_report(self, tenant_id: str, work_order_id: str, completed_quantity: float, unit_material_cost_cents: float = 0, unit_labor_cost_cents: float = 0) -> Optional[Dict]:
        w = self.work_orders.get(work_order_id)
        if not w or w.get("tenantId") != tenant_id:
            return None
        w["completedQuantity"] = completed_quantity
        w["status"] = 4
        w["updatedAt"] = _ts()
        if "materialCostCents" not in w:
            w["materialCostCents"] = 0
        if "laborCostCents" not in w:
            w["laborCostCents"] = 0
        qty = max(0, float(completed_quantity))
        w["materialCostCents"] = int(qty * unit_material_cost_cents)
        w["laborCostCents"] = int(qty * unit_labor_cost_cents)
        if "updatedAt" not in w:
            w["updatedAt"] = w.get("createdAt", _ts())
        return w

    def pp_cost_summary(self, tenant_id: str, page: int = 1, page_size: int = 20) -> Tuple[List[Dict], int]:
        """生产成本核算：按工单汇总材料费、人工费、总成本。"""
        items = self._by_tenant(self.work_orders, tenant_id)
        out = []
        for w in items:
            mat = w.get("materialCostCents") or 0
            labor = w.get("laborCostCents") or 0
            out.append({
                "workOrderId": w.get("workOrderId"),
                "bomId": w.get("bomId"),
                "productMaterialId": w.get("productMaterialId"),
                "plannedQuantity": w.get("plannedQuantity"),
                "completedQuantity": w.get("completedQuantity"),
                "materialCostCents": mat,
                "laborCostCents": labor,
                "totalCostCents": mat + labor,
                "status": w.get("status"),
            })
        return self._paginate(out, page, page_size)

    def pp_work_order_cost(self, tenant_id: str, work_order_id: str) -> Optional[Dict]:
        """单工单生产成本明细。"""
        w = self.work_order_get(tenant_id, work_order_id)
        if not w:
            return None
        mat = w.get("materialCostCents") or 0
        labor = w.get("laborCostCents") or 0
        return {
            "workOrderId": w.get("workOrderId"),
            "plannedQuantity": w.get("plannedQuantity"),
            "completedQuantity": w.get("completedQuantity"),
            "materialCostCents": mat,
            "laborCostCents": labor,
            "totalCostCents": mat + labor,
        }

    def gl_entry_list_filtered(
        self, tenant_id: str, date_from: Optional[str] = None, date_to: Optional[str] = None, page: int = 1, page_size: int = 20
    ) -> Tuple[List[Dict], int]:
        out = self._by_tenant(self.gl_entries, tenant_id)
        if date_from:
            out = [e for e in out if (e.get("postingDate") or "") >= date_from]
        if date_to:
            out = [e for e in out if (e.get("postingDate") or "") <= date_to]
        out = sorted(out, key=lambda x: (x.get("postingDate"), x.get("createdAt")))
        return self._paginate(out, page, page_size)

    def gl_balance(self, tenant_id: str) -> List[Dict]:
        by_account: Dict[str, Dict] = {}
        for line in self.gl_lines:
            if line.get("tenantId") != tenant_id:
                continue
            entry = self.gl_entries.get(line.get("entryId"))
            if entry and entry.get("deletedAt"):
                continue
            ac = line.get("accountCode", "")
            if ac not in by_account:
                acc = self.gl_accounts.get(f"{tenant_id}:{ac}") or {}
                by_account[ac] = {"accountCode": ac, "name": acc.get("name", ""), "debitCents": 0, "creditCents": 0, "balanceCents": 0}
            by_account[ac]["debitCents"] = by_account[ac].get("debitCents", 0) + line.get("debitCents", 0)
            by_account[ac]["creditCents"] = by_account[ac].get("creditCents", 0) + line.get("creditCents", 0)
        for v in by_account.values():
            v["balanceCents"] = v["debitCents"] - v["creditCents"]
        return list(by_account.values())

    def ar_register_receipt(
        self, tenant_id: str, invoice_id: str, amount_cents: int, idem_key: Optional[str] = None
    ) -> Optional[Dict]:
        if idem_key and idem_key in self._idem_receipt:
            return dict(self._idem_receipt[idem_key])
        inv = self.ar_invoices.get(invoice_id)
        if not inv or inv.get("tenantId") != tenant_id or inv.get("deletedAt"):
            return None
        paid = inv.get("paidAmountCents", 0) + amount_cents
        inv["paidAmountCents"] = paid
        inv["status"] = 2 if paid < inv.get("amountCents", 0) else 3
        inv["updatedAt"] = _ts()
        out = dict(inv)
        if idem_key:
            self._idem_receipt[idem_key] = out
        return out
    def ap_register_payment(
        self, tenant_id: str, invoice_id: str, amount_cents: int, idem_key: Optional[str] = None
    ) -> Optional[Dict]:
        if idem_key and idem_key in self._idem_payment:
            return dict(self._idem_payment[idem_key])
        inv = self.ap_invoices.get(invoice_id)
        if not inv or inv.get("tenantId") != tenant_id or inv.get("deletedAt"):
            return None
        paid = inv.get("paidAmountCents", 0) + amount_cents
        inv["paidAmountCents"] = paid
        inv["status"] = 2 if paid < inv.get("amountCents", 0) else 3
        inv["updatedAt"] = _ts()
        out = dict(inv)
        if idem_key:
            self._idem_payment[idem_key] = out
        return out

    def ar_ageing(self, tenant_id: str) -> List[Dict]:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        buckets = []
        for inv in self.ar_invoices.values():
            if inv.get("tenantId") != tenant_id or inv.get("status") == 3 or inv.get("deletedAt"):
                continue
            due = inv.get("dueDate") or ""
            amt = inv.get("amountCents", 0) - inv.get("paidAmountCents", 0)
            if amt <= 0:
                continue
            if not due:
                bucket = "no_due"
            elif due >= now:
                bucket = "future"
            else:
                try:
                    d = (datetime.strptime(now[:10], "%Y-%m-%d") - datetime.strptime(due[:10], "%Y-%m-%d")).days
                    if d <= 30: bucket = "0-30"
                    elif d <= 60: bucket = "31-60"
                    elif d <= 90: bucket = "61-90"
                    else: bucket = "91+"
                except Exception:
                    bucket = "no_due"
            buckets.append({"customerId": inv.get("customerId"), "documentNo": inv.get("documentNo"), "amountCents": amt, "dueDate": due, "bucket": bucket})
        by_bucket: Dict[str, int] = {}
        for b in buckets:
            by_bucket[b["bucket"]] = by_bucket.get(b["bucket"], 0) + b["amountCents"]
        return [{"bucket": k, "totalAmountCents": v} for k, v in sorted(by_bucket.items())]
    def ap_ageing(self, tenant_id: str) -> List[Dict]:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        by_bucket: Dict[str, int] = {}
        for inv in self.ap_invoices.values():
            if inv.get("tenantId") != tenant_id or inv.get("status") == 3 or inv.get("deletedAt"):
                continue
            amt = inv.get("amountCents", 0) - inv.get("paidAmountCents", 0)
            if amt <= 0:
                continue
            due = inv.get("dueDate") or ""
            if not due: bucket = "no_due"
            elif due >= now: bucket = "future"
            else:
                try:
                    d = (datetime.strptime(now[:10], "%Y-%m-%d") - datetime.strptime(due[:10], "%Y-%m-%d")).days
                    if d <= 30: bucket = "0-30"
                    elif d <= 60: bucket = "31-60"
                    elif d <= 90: bucket = "61-90"
                    else: bucket = "91+"
                except Exception:
                    bucket = "no_due"
            by_bucket[bucket] = by_bucket.get(bucket, 0) + amt
        return [{"bucket": k, "totalAmountCents": v} for k, v in sorted(by_bucket.items())]


_store: Optional[ERPStore] = None
def get_store() -> ERPStore:
    global _store
    if _store is None:
        _store = ERPStore()
    return _store
