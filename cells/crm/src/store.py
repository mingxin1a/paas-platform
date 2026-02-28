"""
内存存储（读模型 + 幂等键）。
遵循《01_核心法律》：金额以分存储；多租户 tenant_id 隔离；事件可溯源语义由 event_store 承担，此处为读模型简化实现。
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

# 商机阶段状态机（Salesforce 式）：阶段码 -> (名称, 赢率%)
STAGE_CONFIG = {
    1: ("qualification", 10),
    2: ("needs_analysis", 20),
    3: ("proposal", 40),
    4: ("negotiation", 60),
    5: ("closed_won", 100),
    6: ("closed_lost", 0),
}


class InMemoryStore:
    def __init__(self) -> None:
        self.customers: Dict[str, Dict[str, Any]] = {}
        self.contacts: Dict[str, Dict[str, Any]] = {}
        self.opportunities: Dict[str, Dict[str, Any]] = {}
        self.leads: Dict[str, Dict[str, Any]] = {}
        self.relationships: List[Dict[str, Any]] = []
        self.activities: Dict[str, Dict[str, Any]] = {}
        self.products: Dict[str, Dict[str, Any]] = {}
        self.opportunity_line_items: List[Dict[str, Any]] = []
        self.approval_requests: Dict[str, Dict[str, Any]] = {}
        self._idempotent: Dict[str, str] = {}  # idempotent_key -> resource_id

    def _ts(self) -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())

    def _id(self) -> str:
        return str(uuid.uuid4()).replace("-", "")[:16]

    def idempotent_get(self, key: str) -> Optional[str]:
        return self._idempotent.get(key)

    def idempotent_set(self, key: str, resource_id: str) -> None:
        self._idempotent[key] = resource_id

    # ---------- Customers（行级权限：可选按 ownerId 过滤） ----------
    def customer_list(self, tenant_id: str, page: int = 1, page_size: int = 20, owner_id: Optional[str] = None) -> tuple[List[Dict], int]:
        out = [c for c in self.customers.values() if c.get("tenantId") == tenant_id]
        if owner_id:
            out = [c for c in out if (c.get("ownerId") or "") == owner_id]
        total = len(out)
        start = (page - 1) * page_size
        return out[start : start + page_size], total

    def customer_get(self, tenant_id: str, customer_id: str) -> Optional[Dict]:
        c = self.customers.get(customer_id)
        if c and c.get("tenantId") == tenant_id:
            return c
        return None

    def customer_create(
        self,
        tenant_id: str,
        name: str,
        contact_phone: Optional[str] = None,
        contact_email: Optional[str] = None,
        owner_id: Optional[str] = None,
    ) -> Dict:
        cid = self._id()
        now = self._ts()
        c = {
            "customerId": cid,
            "tenantId": tenant_id,
            "name": name,
            "contactPhone": contact_phone or "",
            "contactEmail": contact_email or "",
            "status": 1,
            "ownerId": owner_id or "",
            "createdAt": now,
            "updatedAt": now,
        }
        self.customers[cid] = c
        return c

    # ---------- Contacts ----------
    def contact_list(
        self,
        tenant_id: str,
        customer_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[Dict], int]:
        out = [x for x in self.contacts.values() if x.get("tenantId") == tenant_id]
        if customer_id:
            out = [x for x in out if x.get("customerId") == customer_id]
        total = len(out)
        start = (page - 1) * page_size
        return out[start : start + page_size], total

    def contact_create(
        self,
        tenant_id: str,
        customer_id: str,
        name: str,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        is_primary: bool = False,
    ) -> Dict:
        cid = self._id()
        now = self._ts()
        c = {
            "contactId": cid,
            "tenantId": tenant_id,
            "customerId": customer_id,
            "name": name,
            "phone": phone or "",
            "email": email or "",
            "isPrimary": is_primary,
            "createdAt": now,
            "updatedAt": now,
        }
        self.contacts[cid] = c
        return c

    # ---------- Opportunities（行级权限：可选按 ownerId 过滤） ----------
    def opportunity_list(
        self,
        tenant_id: str,
        customer_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        owner_id: Optional[str] = None,
    ) -> tuple[List[Dict], int]:
        out = [o for o in self.opportunities.values() if o.get("tenantId") == tenant_id]
        if customer_id:
            out = [o for o in out if o.get("customerId") == customer_id]
        if owner_id:
            out = [o for o in out if (o.get("ownerId") or "") == owner_id]
        total = len(out)
        start = (page - 1) * page_size
        return out[start : start + page_size], total

    def opportunity_get(self, tenant_id: str, opportunity_id: str) -> Optional[Dict]:
        o = self.opportunities.get(opportunity_id)
        if o and o.get("tenantId") == tenant_id:
            return o
        return None

    def opportunity_create(
        self,
        tenant_id: str,
        customer_id: str,
        title: str,
        amount_cents: int = 0,
        currency: str = "CNY",
        stage: int = 1,
        owner_id: Optional[str] = None,
    ) -> Dict:
        oid = self._id()
        now = self._ts()
        o = {
            "opportunityId": oid,
            "tenantId": tenant_id,
            "customerId": customer_id,
            "title": title,
            "amountCents": amount_cents,
            "currency": currency,
            "stage": stage,
            "status": 1,
            "ownerId": owner_id or "",
            "createdAt": now,
            "updatedAt": now,
        }
        self.opportunities[oid] = o
        return o

    def opportunity_update_stage(self, tenant_id: str, opportunity_id: str, stage: int, status: int) -> Optional[Dict]:
        o = self.opportunity_get(tenant_id, opportunity_id)
        if not o:
            return None
        o["stage"] = stage
        o["status"] = status
        o["updatedAt"] = self._ts()
        return o

    # ---------- Leads ----------
    def lead_list(
        self,
        tenant_id: str,
        status: Optional[str] = None,
        assigned_to: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[Dict], int]:
        out = [l for l in self.leads.values() if l.get("tenantId") == tenant_id]
        if status:
            out = [l for l in out if l.get("status") == status]
        if assigned_to:
            out = [l for l in out if l.get("assignedTo") == assigned_to]
        total = len(out)
        start = (page - 1) * page_size
        return out[start : start + page_size], total

    def lead_get(self, tenant_id: str, lead_id: str) -> Optional[Dict]:
        l = self.leads.get(lead_id)
        if l and l.get("tenantId") == tenant_id:
            return l
        return None

    def lead_create(
        self,
        tenant_id: str,
        name: str,
        company: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        source: Optional[str] = None,
    ) -> Dict:
        lid = self._id()
        now = self._ts()
        lead = {
            "leadId": lid,
            "tenantId": tenant_id,
            "name": name,
            "company": company or "",
            "phone": phone or "",
            "email": email or "",
            "source": source or "",
            "status": "new",
            "assignedTo": "",
            "convertedCustomerId": "",
            "convertedOpportunityId": "",
            "createdAt": now,
            "updatedAt": now,
        }
        self.leads[lid] = lead
        return lead

    def lead_assign(self, tenant_id: str, lead_id: str, assigned_to: str) -> Optional[Dict]:
        lead = self.lead_get(tenant_id, lead_id)
        if not lead:
            return None
        lead["assignedTo"] = assigned_to
        lead["updatedAt"] = self._ts()
        return lead

    def lead_convert(
        self,
        tenant_id: str,
        lead_id: str,
        convert_to: str,
        create_opportunity_title: Optional[str] = None,
        amount_cents: int = 0,
    ) -> tuple[Optional[Dict], Optional[str], Optional[str]]:
        lead = self.lead_get(tenant_id, lead_id)
        if not lead or lead.get("status") == "converted":
            return None, None, None
        customer_id: Optional[str] = None
        opportunity_id: Optional[str] = None
        if convert_to in ("account", "both", "opportunity"):
            c = self.customer_create(
                tenant_id,
                lead.get("company") or lead.get("name", ""),
                lead.get("phone"),
                lead.get("email"),
            )
            customer_id = c["customerId"]
        if convert_to in ("opportunity", "both"):
            title = create_opportunity_title or (lead.get("company") or lead.get("name", "")) + " - 转化商机"
            o = self.opportunity_create(
                tenant_id, customer_id or "", title, amount_cents, "CNY", 1
            )
            opportunity_id = o["opportunityId"]
        lead["status"] = "converted"
        lead["convertedCustomerId"] = customer_id or ""
        lead["convertedOpportunityId"] = opportunity_id or ""
        lead["updatedAt"] = self._ts()
        return lead, customer_id, opportunity_id

    # ---------- Relationships ----------
    def relationship_add(
        self,
        tenant_id: str,
        from_customer_id: str,
        to_customer_id: str,
        relationship_type: str,
    ) -> None:
        now = self._ts()
        self.relationships.append({
            "tenantId": tenant_id,
            "fromCustomerId": from_customer_id,
            "toCustomerId": to_customer_id,
            "relationshipType": relationship_type,
            "createdAt": now,
        })

    def relationship_list(self, tenant_id: str, customer_id: str) -> tuple[List[Dict], List[Dict]]:
        nodes = []
        edges = []
        seen = set()
        for r in self.relationships:
            if r.get("tenantId") != tenant_id:
                continue
            if r.get("fromCustomerId") != customer_id and r.get("toCustomerId") != customer_id:
                continue
            fid, tid = r["fromCustomerId"], r["toCustomerId"]
            for nid in (fid, tid):
                if nid not in seen:
                    seen.add(nid)
                    cust = self.customer_get(tenant_id, nid)
                    nodes.append({"customerId": nid, "name": (cust or {}).get("name", nid)})
            edges.append({
                "fromCustomerId": fid,
                "toCustomerId": tid,
                "relationshipType": r.get("relationshipType", ""),
            })
        return nodes, edges

    # ---------- Activities ----------
    def activity_create(
        self,
        tenant_id: str,
        activity_type: str,
        subject: str,
        related_lead_id: Optional[str] = None,
        related_opportunity_id: Optional[str] = None,
        related_customer_id: Optional[str] = None,
        due_at: Optional[str] = None,
    ) -> Dict:
        aid = self._id()
        now = self._ts()
        a = {
            "activityId": aid,
            "tenantId": tenant_id,
            "activityType": activity_type,
            "subject": subject,
            "relatedLeadId": related_lead_id or "",
            "relatedOpportunityId": related_opportunity_id or "",
            "relatedCustomerId": related_customer_id or "",
            "dueAt": due_at or "",
            "completedAt": "",
            "status": 1,
            "createdAt": now,
            "updatedAt": now,
        }
        self.activities[aid] = a
        return a

    def activity_list(
        self,
        tenant_id: str,
        related_opportunity_id: Optional[str] = None,
        related_customer_id: Optional[str] = None,
        activity_type: Optional[str] = None,
        status: Optional[int] = None,
        due_from: Optional[str] = None,
        due_to: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[Dict], int]:
        out = [a for a in self.activities.values() if a.get("tenantId") == tenant_id]
        if related_opportunity_id:
            out = [a for a in out if a.get("relatedOpportunityId") == related_opportunity_id]
        if related_customer_id:
            out = [a for a in out if a.get("relatedCustomerId") == related_customer_id]
        if activity_type:
            out = [a for a in out if a.get("activityType") == activity_type]
        if status is not None:
            out = [a for a in out if a.get("status") == status]
        if due_from:
            out = [a for a in out if (a.get("dueAt") or "") >= due_from]
        if due_to:
            out = [a for a in out if (a.get("dueAt") or "") <= due_to]
        total = len(out)
        out.sort(key=lambda x: x.get("dueAt") or x.get("createdAt") or "")
        start = (page - 1) * page_size
        return out[start : start + page_size], total

    def activity_get(self, tenant_id: str, activity_id: str) -> Optional[Dict]:
        a = self.activities.get(activity_id)
        if a and a.get("tenantId") == tenant_id:
            return a
        return None

    def activity_complete(self, tenant_id: str, activity_id: str) -> Optional[Dict]:
        a = self.activity_get(tenant_id, activity_id)
        if not a:
            return None
        now = self._ts()
        a["status"] = 2
        a["completedAt"] = now
        a["updatedAt"] = now
        return a

    def activity_todo_list(self, tenant_id: str, due_before: Optional[str] = None) -> List[Dict]:
        out = [a for a in self.activities.values() if a.get("tenantId") == tenant_id and a.get("status") == 1]
        if due_before:
            out = [a for a in out if (a.get("dueAt") or "") <= due_before]
        out.sort(key=lambda x: x.get("dueAt") or "z")
        return out

    # ---------- Products ----------
    def product_create(
        self,
        tenant_id: str,
        product_code: str,
        name: str,
        unit: str = "PCS",
        standard_price_cents: int = 0,
    ) -> Dict:
        pid = self._id()
        now = self._ts()
        p = {
            "productId": pid,
            "tenantId": tenant_id,
            "productCode": product_code,
            "name": name,
            "unit": unit,
            "standardPriceCents": standard_price_cents,
            "createdAt": now,
        }
        self.products[pid] = p
        return p

    def product_list(self, tenant_id: str, page: int = 1, page_size: int = 20) -> tuple[List[Dict], int]:
        out = [p for p in self.products.values() if p.get("tenantId") == tenant_id]
        total = len(out)
        start = (page - 1) * page_size
        return out[start : start + page_size], total

    def product_get(self, tenant_id: str, product_id: str) -> Optional[Dict]:
        p = self.products.get(product_id)
        if p and p.get("tenantId") == tenant_id:
            return p
        return None

    # ---------- Opportunity Line Items ----------
    def _opp_line_total_cents(self, tenant_id: str, opportunity_id: str) -> int:
        total = 0
        for line in self.opportunity_line_items:
            if line.get("tenantId") == tenant_id and line.get("opportunityId") == opportunity_id:
                total += line.get("totalCents", 0)
        return total

    def opportunity_line_add(
        self,
        tenant_id: str,
        opportunity_id: str,
        product_id: str,
        quantity: float,
        unit_price_cents: int,
    ) -> Optional[Dict]:
        if not self.opportunity_get(tenant_id, opportunity_id):
            return None
        prod = self.product_get(tenant_id, product_id)
        if not prod:
            return None
        line_id = self._id()
        now = self._ts()
        total_cents = int(quantity * unit_price_cents)
        line = {
            "lineId": line_id,
            "tenantId": tenant_id,
            "opportunityId": opportunity_id,
            "productId": product_id,
            "productCode": prod.get("productCode", ""),
            "productName": prod.get("name", ""),
            "quantity": quantity,
            "unitPriceCents": unit_price_cents,
            "totalCents": total_cents,
            "createdAt": now,
        }
        self.opportunity_line_items.append(line)
        opp = self.opportunities.get(opportunity_id)
        if opp:
            opp["amountCents"] = self._opp_line_total_cents(tenant_id, opportunity_id)
            opp["updatedAt"] = now
        return line

    def opportunity_line_list(self, tenant_id: str, opportunity_id: str) -> List[Dict]:
        return [l for l in self.opportunity_line_items if l.get("tenantId") == tenant_id and l.get("opportunityId") == opportunity_id]

    def opportunity_line_remove(self, tenant_id: str, opportunity_id: str, line_id: str) -> bool:
        for i, line in enumerate(self.opportunity_line_items):
            if line.get("lineId") == line_id and line.get("tenantId") == tenant_id and line.get("opportunityId") == opportunity_id:
                self.opportunity_line_items.pop(i)
                opp = self.opportunities.get(opportunity_id)
                if opp:
                    opp["amountCents"] = self._opp_line_total_cents(tenant_id, opportunity_id)
                    opp["updatedAt"] = self._ts()
                return True
        return False

    # ---------- Approval ----------
    def approval_request_create(
        self,
        tenant_id: str,
        opportunity_id: str,
        request_type: str,
        requested_by: str,
        requested_value_cents: Optional[int] = None,
        requested_discount_pct: Optional[int] = None,
    ) -> Optional[Dict]:
        if not self.opportunity_get(tenant_id, opportunity_id):
            return None
        rid = self._id()
        now = self._ts()
        req = {
            "requestId": rid,
            "tenantId": tenant_id,
            "opportunityId": opportunity_id,
            "requestType": request_type,
            "requestedValueCents": requested_value_cents,
            "requestedDiscountPct": requested_discount_pct,
            "status": "pending",
            "requestedBy": requested_by,
            "processedBy": "",
            "processedAt": "",
            "comment": "",
            "createdAt": now,
        }
        self.approval_requests[rid] = req
        return req

    def approval_request_list(
        self,
        tenant_id: str,
        opportunity_id: Optional[str] = None,
        status: Optional[str] = None,
        pending_for_user: Optional[str] = None,
    ) -> List[Dict]:
        out = [r for r in self.approval_requests.values() if r.get("tenantId") == tenant_id]
        if opportunity_id:
            out = [r for r in out if r.get("opportunityId") == opportunity_id]
        if status:
            out = [r for r in out if r.get("status") == status]
        if pending_for_user:
            out = [r for r in out if r.get("status") == "pending"]
        return out

    def approval_process(self, tenant_id: str, request_id: str, approved: bool, processed_by: str, comment: str = "") -> Optional[Dict]:
        req = self.approval_requests.get(request_id)
        if not req or req.get("tenantId") != tenant_id or req.get("status") != "pending":
            return None
        now = self._ts()
        req["status"] = "approved" if approved else "rejected"
        req["processedBy"] = processed_by
        req["processedAt"] = now
        req["comment"] = comment
        return req

    # ---------- Pipeline & Funnel ----------
    def pipeline_summary(self, tenant_id: str) -> Dict:
        return self.forecast_summary(tenant_id)

    def funnel_data(self, tenant_id: str) -> Dict:
        by_stage: Dict[int, Dict[str, Any]] = {}
        for o in self.opportunities.values():
            if o.get("tenantId") != tenant_id or o.get("status") != 1:
                continue
            st = o.get("stage", 1)
            name, prob = STAGE_CONFIG.get(st, ("unknown", 0))
            amt = o.get("amountCents") or 0
            if st not in by_stage:
                by_stage[st] = {"stage": st, "stageName": name, "count": 0, "totalAmountCents": 0}
            by_stage[st]["count"] += 1
            by_stage[st]["totalAmountCents"] += amt
        stages = sorted(by_stage.keys())
        return {"stages": [by_stage[s] for s in stages], "totalCount": sum(by_stage[s]["count"] for s in stages)}

    def activity_stats(self, tenant_id: str, group_by: str = "type") -> List[Dict]:
        out = [a for a in self.activities.values() if a.get("tenantId") == tenant_id]
        if group_by == "type":
            by_type: Dict[str, int] = {}
            for a in out:
                t = a.get("activityType") or "other"
                by_type[t] = by_type.get(t, 0) + 1
            return [{"activityType": k, "count": v} for k, v in by_type.items()]
        return []

    # ---------- Forecast & Win rate ----------
    def forecast_summary(self, tenant_id: str) -> Dict:
        by_stage: Dict[int, Dict[str, Any]] = {}
        total_weighted = 0
        for o in self.opportunities.values():
            if o.get("tenantId") != tenant_id or o.get("status") != 1:
                continue
            st = o.get("stage", 1)
            name, prob = STAGE_CONFIG.get(st, ("unknown", 0))
            amt = o.get("amountCents") or 0
            if st not in by_stage:
                by_stage[st] = {"stage": st, "stageName": name, "totalAmountCents": 0, "count": 0}
            by_stage[st]["totalAmountCents"] += amt
            by_stage[st]["count"] += 1
            total_weighted += int(amt * prob / 100)
        return {
            "byStage": list(by_stage.values()),
            "totalWeightedCents": total_weighted,
        }

    def win_rate_analysis(self, tenant_id: str, period_days: int = 90) -> Dict:
        import datetime
        from datetime import timezone
        now = datetime.datetime.now(timezone.utc)
        cutoff = (now - datetime.timedelta(days=period_days)).strftime("%Y-%m-%d")
        won = lost = 0
        for o in self.opportunities.values():
            if o.get("tenantId") != tenant_id:
                continue
            if o.get("updatedAt", "") < cutoff:
                continue
            if o.get("status") == 2:
                won += 1
            elif o.get("status") == 3:
                lost += 1
        total = won + lost
        win_rate = (won / total * 100) if total else 0
        return {"periodDays": period_days, "wonCount": won, "lostCount": lost, "winRatePct": round(win_rate, 2)}


_store: Optional[InMemoryStore] = None


def get_store() -> InMemoryStore:
    global _store
    if _store is None:
        _store = InMemoryStore()
    return _store


def template_merge(template: str, context: Dict[str, Any]) -> str:
    """邮件/文档模板合并：将 {{key}} 替换为 context[key]。封闭实现，无外部依赖。"""
    import re
    result = template
    for key, value in context.items():
        result = result.replace("{{" + key + "}}", str(value))
    result = re.sub(r"\{\{[^}]+\}\}", "", result)
    return result
