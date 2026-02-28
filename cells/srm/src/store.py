"""SRM 内存存储：供应商、采购订单、询报价、评估。多租户，商用级闭环。"""
from __future__ import annotations
import time
import uuid
from typing import Dict, List, Optional

def _ts(): return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
def _id(): return str(uuid.uuid4()).replace("-", "")[:16]

class SRMStore:
    def __init__(self) -> None:
        self.suppliers: Dict[str, dict] = {}
        self.purchase_orders: Dict[str, dict] = {}
        self.rfqs: Dict[str, dict] = {}
        self.quotes: Dict[str, dict] = {}
        self.evaluations: Dict[str, dict] = {}
        self.bidding_projects: Dict[str, dict] = {}
        self._idem: Dict[str, str] = {}
        self._audit_log: List[dict] = []

    def idem_get(self, k: str) -> Optional[str]:
        return self._idem.get(k)
    def idem_set(self, k: str, v: str) -> None:
        self._idem[k] = v

    def audit_append(self, tenant_id: str, user_id: str, operation_type: str, resource_type: str = "", resource_id: str = "", trace_id: str = "") -> None:
        self._audit_log.append({
            "tenantId": tenant_id, "userId": user_id, "operationType": operation_type,
            "resourceType": resource_type or "", "resourceId": resource_id or "", "traceId": trace_id or "",
            "occurredAt": _ts(),
        })

    def audit_list(self, tenant_id: str, page: int = 1, page_size: int = 50, resource_type: Optional[str] = None) -> tuple[List[dict], int]:
        out = [e for e in self._audit_log if e.get("tenantId") == tenant_id]
        if resource_type:
            out = [e for e in out if (e.get("resourceType") or "") == resource_type]
        total = len(out)
        out = sorted(out, key=lambda x: x.get("occurredAt", ""), reverse=True)
        start = (page - 1) * page_size
        return out[start : start + page_size], total

    def _by_tenant(self, d: Dict[str, dict], tenant_id: str) -> List[dict]:
        return [v for v in d.values() if v.get("tenantId") == tenant_id]

    def supplier_list(self, tenant_id: str) -> List[dict]:
        return self._by_tenant(self.suppliers, tenant_id)

    def supplier_create(self, tenant_id: str, name: str, code: str = "", contact: str = "") -> dict:
        sid = _id()
        now = _ts()
        s = {"supplierId": sid, "tenantId": tenant_id, "name": name, "code": code, "contact": contact, "status": 1, "createdAt": now, "updatedAt": now}
        self.suppliers[sid] = s
        return s

    def purchase_order_list(self, tenant_id: str) -> List[dict]:
        return self._by_tenant(self.purchase_orders, tenant_id)

    def purchase_order_create(self, tenant_id: str, supplier_id: str, order_no: str = "", amount_cents: int = 0) -> dict:
        oid = _id()
        now = _ts()
        o = {"orderId": oid, "tenantId": tenant_id, "supplierId": supplier_id, "orderNo": order_no or oid[:8], "amountCents": amount_cents, "status": 1, "createdAt": now, "updatedAt": now}
        self.purchase_orders[oid] = o
        return o

    def supplier_get(self, tenant_id: str, supplier_id: str) -> Optional[dict]:
        s = self.suppliers.get(supplier_id)
        return s if s and s.get("tenantId") == tenant_id else None

    def purchase_order_get(self, tenant_id: str, order_id: str) -> Optional[dict]:
        o = self.purchase_orders.get(order_id)
        return o if o and o.get("tenantId") == tenant_id else None

    def purchase_order_update_status(self, tenant_id: str, order_id: str, status: int) -> Optional[dict]:
        o = self.purchase_order_get(tenant_id, order_id)
        if not o:
            return None
        o["status"] = status
        o["updatedAt"] = _ts()
        return o

    # ---------- 询价 RFQ ----------
    def rfq_list(self, tenant_id: str, page: int = 1, page_size: int = 20) -> tuple[List[dict], int]:
        items = self._by_tenant(self.rfqs, tenant_id)
        total = len(items)
        start = (page - 1) * page_size
        return items[start:start + page_size], total

    def rfq_get(self, tenant_id: str, rfq_id: str) -> Optional[dict]:
        r = self.rfqs.get(rfq_id)
        return r if r and r.get("tenantId") == tenant_id else None

    def rfq_create(self, tenant_id: str, demand_id: str = "") -> dict:
        rid = _id()
        now = _ts()
        r = {"rfqId": rid, "tenantId": tenant_id, "demandId": demand_id, "status": "open", "createdAt": now}
        self.rfqs[rid] = r
        return r

    # ---------- 报价 Quote（幂等） ----------
    def quote_list(self, tenant_id: str, rfq_id: Optional[str] = None, page: int = 1, page_size: int = 20) -> tuple[List[dict], int]:
        items = self._by_tenant(self.quotes, tenant_id)
        if rfq_id:
            items = [x for x in items if x.get("rfqId") == rfq_id]
        total = len(items)
        start = (page - 1) * page_size
        return items[start:start + page_size], total

    def quote_get(self, tenant_id: str, quote_id: str) -> Optional[dict]:
        q = self.quotes.get(quote_id)
        return q if q and q.get("tenantId") == tenant_id else None

    def quote_create(self, tenant_id: str, rfq_id: str, supplier_id: str, amount_cents: int, currency: str = "CNY", valid_until: str = "") -> dict:
        qid = _id()
        now = _ts()
        q = {"quoteId": qid, "tenantId": tenant_id, "rfqId": rfq_id, "supplierId": supplier_id, "amountCents": amount_cents, "currency": currency, "validUntil": valid_until, "createdAt": now, "awarded": False}
        self.quotes[qid] = q
        return q

    def quote_award(self, tenant_id: str, quote_id: str) -> Optional[dict]:
        """报价中标：标记为中标并返回报价信息，供联动 Worker 回传 ERP 生成采购订单。"""
        q = self.quote_get(tenant_id, quote_id)
        if not q:
            return None
        q["awarded"] = True
        q["awardedAt"] = _ts()
        return q

    # ---------- 供应商评估 ----------
    def evaluation_list(self, tenant_id: str, supplier_id: Optional[str] = None, page: int = 1, page_size: int = 20) -> tuple[List[dict], int]:
        items = [v for v in self.evaluations.values() if v.get("tenantId") == tenant_id]
        if supplier_id:
            items = [x for x in items if x.get("supplierId") == supplier_id]
        total = len(items)
        start = (page - 1) * page_size
        return items[start:start + page_size], total

    def evaluation_create(self, tenant_id: str, supplier_id: str, score: int, dimension: str = "", comment: str = "") -> dict:
        eid = _id()
        now = _ts()
        e = {"evaluationId": eid, "tenantId": tenant_id, "supplierId": supplier_id, "score": score, "dimension": dimension, "comment": comment, "evaluatedAt": now, "createdAt": now}
        self.evaluations[eid] = e
        return e

    # ---------- 供应商招投标（项目） ----------
    def bidding_project_list(self, tenant_id: str, status: Optional[str] = None, page: int = 1, page_size: int = 20) -> tuple[List[dict], int]:
        items = self._by_tenant(self.bidding_projects, tenant_id)
        if status:
            items = [x for x in items if x.get("status") == status]
        total = len(items)
        start = (page - 1) * page_size
        return items[start:start + page_size], total

    def bidding_project_get(self, tenant_id: str, project_id: str) -> Optional[dict]:
        p = self.bidding_projects.get(project_id)
        return p if p and p.get("tenantId") == tenant_id else None

    def bidding_project_create(self, tenant_id: str, title: str, description: str = "", rfq_ids: Optional[List[str]] = None) -> dict:
        pid = _id()
        now = _ts()
        p = {
            "projectId": pid,
            "tenantId": tenant_id,
            "title": title,
            "description": description or "",
            "status": "open",
            "rfqIds": rfq_ids or [],
            "createdAt": now,
            "updatedAt": now,
        }
        self.bidding_projects[pid] = p
        return p

    def bidding_project_update_status(self, tenant_id: str, project_id: str, status: str) -> Optional[dict]:
        p = self.bidding_project_get(tenant_id, project_id)
        if not p:
            return None
        if status not in ("open", "closed", "awarded"):
            return None
        p["status"] = status
        p["updatedAt"] = _ts()
        return p

_store: Optional[SRMStore] = None

def get_store() -> SRMStore:
    global _store
    if _store is None:
        _store = SRMStore()
    return _store
