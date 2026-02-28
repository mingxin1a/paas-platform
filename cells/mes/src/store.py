"""MES 内存存储：工单、BOM、生产计划、生产订单、领料、报工、生产入库、追溯。多租户，工业场景。"""
from __future__ import annotations

import time
import uuid
from typing import Dict, List, Optional

def _ts(): return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
def _id(): return str(uuid.uuid4()).replace("-", "")[:16]


class MESStore:
    def __init__(self) -> None:
        self.work_orders: Dict[str, dict] = {}
        self.workshops: Dict[str, dict] = {}
        self.boms: Dict[str, dict] = {}
        self.bom_lines: List[dict] = []
        self.production_orders: Dict[str, dict] = {}
        self.material_issues: Dict[str, dict] = {}
        self.work_reports: List[dict] = []
        self.production_inbounds: Dict[str, dict] = {}
        self.production_traces: List[dict] = []
        self.production_plans: Dict[str, dict] = {}
        self.quality_inspections: Dict[str, dict] = {}
        self.device_telemetry: List[dict] = []
        self._idem: Dict[str, str] = {}
        self._order_progress: Dict[str, float] = {}
        self._audit_log: List[dict] = []

    def idem_get(self, k: str) -> Optional[str]:
        return self._idem.get(k)

    def idem_set(self, k: str, v: str) -> None:
        self._idem[k] = v

    def _by_tenant(self, items: Dict[str, dict], tenant_id: str) -> List[dict]:
        return [v for v in items.values() if v.get("tenantId") == tenant_id]

    # ---------- 工单（兼容原接口，增加 workshop_id） ----------
    def work_order_list(self, tenant_id: str, workshop_id: Optional[str] = None, page: int = 1, page_size: int = 20) -> tuple[List[dict], int]:
        out = self._by_tenant(self.work_orders, tenant_id)
        if workshop_id:
            out = [o for o in out if o.get("workshopId") == workshop_id]
        total = len(out)
        start = (page - 1) * page_size
        return out[start:start + page_size], total

    def work_order_create(self, tenant_id: str, order_no: str, product_code: str = "", qty: int = 1, workshop_id: str = "") -> dict:
        wid = _id()
        now = _ts()
        w = {
            "workOrderId": wid, "tenantId": tenant_id, "orderNo": order_no, "productCode": product_code,
            "qty": qty, "status": 1, "workshopId": workshop_id or "", "createdAt": now, "updatedAt": now,
        }
        self.work_orders[wid] = w
        return w

    def work_order_get(self, tenant_id: str, work_order_id: str) -> Optional[dict]:
        w = self.work_orders.get(work_order_id)
        return w if w and w.get("tenantId") == tenant_id else None

    def work_order_update_status(self, tenant_id: str, work_order_id: str, status: int) -> Optional[dict]:
        w = self.work_order_get(tenant_id, work_order_id)
        if not w:
            return None
        w["status"] = status
        w["updatedAt"] = _ts()
        return w

    # ---------- BOM ----------
    def bom_list(self, tenant_id: str, product_sku: Optional[str] = None) -> List[dict]:
        out = [b for b in self.boms.values() if b.get("tenantId") == tenant_id]
        if product_sku:
            out = [b for b in out if b.get("productSku") == product_sku]
        return out

    def bom_create(self, tenant_id: str, product_sku: str, version: int = 1, lines: Optional[List[dict]] = None) -> dict:
        bid = _id()
        now = _ts()
        b = {"bomId": bid, "tenantId": tenant_id, "productSku": product_sku, "version": version, "createdAt": now}
        self.boms[bid] = b
        for ln in (lines or []):
            self.bom_lines.append({"bomLineId": _id(), "tenantId": tenant_id, "bomId": bid, "materialSku": ln.get("materialSku", ""), "quantityPer": float(ln.get("quantityPer", 1)), "createdAt": now})
        return b

    def bom_get(self, tenant_id: str, bom_id: str) -> Optional[dict]:
        b = self.boms.get(bom_id)
        if not b or b.get("tenantId") != tenant_id:
            return None
        out = dict(b)
        out["lines"] = [l for l in self.bom_lines if l.get("bomId") == bom_id and l.get("tenantId") == tenant_id]
        return out

    def bom_lines_by_bom(self, tenant_id: str, bom_id: str) -> List[dict]:
        return [dict(l) for l in self.bom_lines if l.get("bomId") == bom_id and l.get("tenantId") == tenant_id]

    def material_requirements(self, tenant_id: str, order_id: str) -> Optional[List[dict]]:
        """根据生产订单数量与 BOM 计算物料需求（物料需求计算）。"""
        o = self.production_order_get(tenant_id, order_id)
        if not o:
            return None
        product_sku = o.get("productSku", "")
        qty = float(o.get("quantity", 1))
        boms = [b for b in self.boms.values() if b.get("tenantId") == tenant_id and b.get("productSku") == product_sku]
        if not boms:
            return []
        bom_id = boms[-1]["bomId"]
        lines = self.bom_lines_by_bom(tenant_id, bom_id)
        by_sku: Dict[str, float] = {}
        for ln in lines:
            sku = ln.get("materialSku", "")
            if not sku:
                continue
            per = float(ln.get("quantityPer", 1))
            by_sku[sku] = by_sku.get(sku, 0) + per * qty
        return [{"materialSku": k, "requiredQuantity": round(v, 4)} for k, v in by_sku.items()]

    def audit_append(self, tenant_id: str, user_id: str, operation_type: str, resource_type: str = "", resource_id: str = "", trace_id: str = "") -> None:
        self._audit_log.append({"tenantId": tenant_id, "userId": user_id, "operationType": operation_type, "resourceType": resource_type or "", "resourceId": resource_id or "", "traceId": trace_id or "", "occurredAt": _ts()})

    def audit_list(self, tenant_id: str, page: int = 1, page_size: int = 50, resource_type: Optional[str] = None) -> tuple[List[dict], int]:
        out = [e for e in self._audit_log if e.get("tenantId") == tenant_id]
        if resource_type:
            out = [e for e in out if (e.get("resourceType") or "") == resource_type]
        total = len(out)
        out = sorted(out, key=lambda x: x.get("occurredAt", ""), reverse=True)
        start = (page - 1) * page_size
        return out[start:start + page_size], total

    # ---------- 生产计划 ----------
    def production_plan_list(self, tenant_id: str, page: int = 1, page_size: int = 20) -> tuple[List[dict], int]:
        out = [p for p in self.production_plans.values() if p.get("tenantId") == tenant_id]
        total = len(out)
        start = (page - 1) * page_size
        return out[start:start + page_size], total

    def production_plan_create(self, tenant_id: str, plan_no: str, product_sku: str, planned_qty: float, plan_date: str = "") -> dict:
        pid = _id()
        now = _ts()
        p = {"planId": pid, "tenantId": tenant_id, "planNo": plan_no, "productSku": product_sku, "plannedQty": planned_qty, "planDate": plan_date or now[:10], "status": 1, "createdAt": now}
        self.production_plans[pid] = p
        return p

    # ---------- 生产订单（车间数据权限） ----------
    def production_order_list(self, tenant_id: str, workshop_id: Optional[str] = None, page: int = 1, page_size: int = 20) -> tuple[List[dict], int]:
        out = self._by_tenant(self.production_orders, tenant_id)
        if workshop_id:
            out = [o for o in out if o.get("workshopId") == workshop_id]
        total = len(out)
        start = (page - 1) * page_size
        return out[start:start + page_size], total

    def production_order_create(self, tenant_id: str, workshop_id: str, order_no: str, product_sku: str, quantity: float, plan_id: str = "") -> dict:
        oid = _id()
        now = _ts()
        o = {
            "orderId": oid, "tenantId": tenant_id, "workshopId": workshop_id, "planId": plan_id,
            "orderNo": order_no, "productSku": product_sku, "quantity": quantity, "status": 1,
            "createdAt": now, "updatedAt": now,
        }
        self.production_orders[oid] = o
        return o

    def production_order_get(self, tenant_id: str, order_id: str) -> Optional[dict]:
        o = self.production_orders.get(order_id)
        return o if o and o.get("tenantId") == tenant_id else None

    def production_order_update_status(self, tenant_id: str, order_id: str, status: int) -> Optional[dict]:
        o = self.production_order_get(tenant_id, order_id)
        if not o:
            return None
        o["status"] = status
        o["updatedAt"] = _ts()
        return o

    # ---------- 领料（防超领：已领+本次 ≤ 应领） ----------
    def material_issue_list(self, tenant_id: str, order_id: Optional[str] = None) -> List[dict]:
        out = [m for m in self.material_issues.values() if m.get("tenantId") == tenant_id]
        if order_id:
            out = [m for m in out if m.get("orderId") == order_id]
        return out

    def material_issue_create(self, tenant_id: str, order_id: str, material_sku: str, required_qty: float) -> Optional[dict]:
        if not self.production_order_get(tenant_id, order_id):
            return None
        iid = _id()
        now = _ts()
        m = {"issueId": iid, "tenantId": tenant_id, "orderId": order_id, "materialSku": material_sku, "requiredQty": required_qty, "issuedQty": 0.0, "createdAt": now}
        self.material_issues[iid] = m
        return m

    def material_issue_issue(self, tenant_id: str, issue_id: str, issue_qty: float) -> Optional[dict]:
        m = self.material_issues.get(issue_id)
        if not m or m.get("tenantId") != tenant_id:
            return None
        required = float(m.get("requiredQty", 0))
        issued = float(m.get("issuedQty", 0))
        if issued + issue_qty > required:
            return None  # 防超领
        m["issuedQty"] = issued + issue_qty
        return m

    # ---------- 报工（支持批量 100+ 工序） ----------
    def work_report_list(self, tenant_id: str, order_id: Optional[str] = None, page: int = 1, page_size: int = 100) -> tuple[List[dict], int]:
        out = [r for r in self.work_reports if r.get("tenantId") == tenant_id]
        if order_id:
            out = [r for r in out if r.get("orderId") == order_id]
        total = len(out)
        start = (page - 1) * page_size
        return out[start:start + page_size], total

    def work_report_batch(self, tenant_id: str, order_id: str, items: List[dict]) -> List[dict]:
        """批量报工：items = [{"operationCode":"OP10","completedQty":10}, ...]"""
        created = []
        now = _ts()
        for it in items:
            rid = _id()
            r = {"reportId": rid, "tenantId": tenant_id, "orderId": order_id, "operationCode": it.get("operationCode", ""), "completedQty": float(it.get("completedQty", 0)), "reportAt": now, "createdAt": now}
            self.work_reports.append(r)
            created.append(r)
            self._order_progress[order_id] = self._order_progress.get(order_id, 0) + float(it.get("completedQty", 0))
        return created

    # ---------- 生产入库（幂等：idempotent_key） ----------
    def production_inbound_create(self, tenant_id: str, order_id: str, warehouse_id: str, quantity: float, lot_number: str = "", serial_numbers: Optional[List[str]] = None, idempotent_key: str = "") -> tuple[Optional[dict], bool]:
        """返回 (record, is_new)。幂等：同一 idempotent_key 返回已存在记录且 is_new=False。支持序列号追溯。"""
        if idempotent_key:
            for p in self.production_inbounds.values():
                if p.get("idempotentKey") == idempotent_key and p.get("tenantId") == tenant_id:
                    return (p, False)
        if not self.production_order_get(tenant_id, order_id):
            return (None, False)
        iid = _id()
        now = _ts()
        product_sku = self.production_orders.get(order_id, {}).get("productSku", "")
        p = {"inboundId": iid, "tenantId": tenant_id, "orderId": order_id, "warehouseId": warehouse_id, "quantity": quantity, "lotNumber": lot_number or "", "serialNumbers": serial_numbers or [], "createdAt": now, "idempotentKey": idempotent_key or ""}
        self.production_inbounds[iid] = p
        serials = serial_numbers or []
        if serials:
            for sn in serials:
                self.production_traces.append({"traceId": _id(), "tenantId": tenant_id, "orderId": order_id, "lotNumber": lot_number or "", "serialNumber": sn, "productSku": product_sku, "quantity": 1.0, "createdAt": now})
        else:
            self.production_traces.append({"traceId": _id(), "tenantId": tenant_id, "orderId": order_id, "lotNumber": lot_number or "", "serialNumber": "", "productSku": product_sku, "quantity": quantity, "createdAt": now})
        return (p, True)

    # ---------- 追溯 ----------
    def trace_by_lot(self, tenant_id: str, lot_number: str) -> List[dict]:
        return [t for t in self.production_traces if t.get("tenantId") == tenant_id and t.get("lotNumber") == lot_number]

    def trace_by_order(self, tenant_id: str, order_id: str) -> List[dict]:
        return [t for t in self.production_traces if t.get("tenantId") == tenant_id and t.get("orderId") == order_id]

    def trace_by_serial(self, tenant_id: str, serial_number: str) -> List[dict]:
        return [dict(t) for t in self.production_traces if t.get("tenantId") == tenant_id and (t.get("serialNumber") or "") == serial_number]

    # ---------- 产能统计（基础） ----------
    def capacity_stats(self, tenant_id: str) -> dict:
        orders = self._by_tenant(self.production_orders, tenant_id)
        total = len(orders)
        completed = sum(1 for o in orders if o.get("status") == 2)
        return {"totalOrders": total, "completedOrders": completed, "completionRatePct": round(100 * completed / total, 2) if total else 0}

    def issue_accuracy(self, tenant_id: str) -> dict:
        issues = [m for m in self.material_issues.values() if m.get("tenantId") == tenant_id]
        if not issues:
            return {"totalRequired": 0, "totalIssued": 0, "accuracyPct": 100}
        total_r = sum(float(m.get("requiredQty", 0)) for m in issues)
        total_i = sum(float(m.get("issuedQty", 0)) for m in issues)
        return {"totalRequired": total_r, "totalIssued": total_i, "accuracyPct": round(100 * total_i / total_r, 2) if total_r else 100}

    # ---------- 质检 ----------
    def quality_inspection_list(self, tenant_id: str, order_id: Optional[str] = None, page: int = 1, page_size: int = 20) -> tuple[List[dict], int]:
        out = [q for q in self.quality_inspections.values() if q.get("tenantId") == tenant_id]
        if order_id:
            out = [q for q in out if q.get("orderId") == order_id]
        total = len(out)
        start = (page - 1) * page_size
        return out[start:start + page_size], total

    def quality_inspection_create(self, tenant_id: str, order_id: str, lot_number: str = "", result: str = "pass", defect_code: str = "") -> Optional[dict]:
        if not self.production_order_get(tenant_id, order_id):
            return None
        qid = _id()
        now = _ts()
        q = {"inspectionId": qid, "tenantId": tenant_id, "orderId": order_id, "lotNumber": lot_number or "", "result": result, "defectCode": defect_code or "", "inspectedAt": now, "createdAt": now}
        self.quality_inspections[qid] = q
        return q

    # ---------- 生产/仓储看板实时数据 ----------
    def board_data(self, tenant_id: str) -> dict:
        wo_list = self._by_tenant(self.work_orders, tenant_id)
        po_list = self._by_tenant(self.production_orders, tenant_id)
        by_status_wo = {}
        for w in wo_list:
            s = w.get("status", 1)
            by_status_wo[s] = by_status_wo.get(s, 0) + 1
        by_status_po = {}
        for p in po_list:
            s = p.get("status", 1)
            by_status_po[s] = by_status_po.get(s, 0) + 1
        cap = self.capacity_stats(tenant_id)
        return {"workOrdersByStatus": by_status_wo, "productionOrdersByStatus": by_status_po, "capacityStats": cap, "orderProgress": dict(self._order_progress)}

    # ---------- 工业设备标准化 HTTP 接入（遥测上报） ----------
    def device_telemetry_submit(self, tenant_id: str, device_id: str, metric: str, value: float, ts: str = "") -> dict:
        now = ts or _ts()
        t = {"telemetryId": _id(), "tenantId": tenant_id, "deviceId": device_id, "metric": metric, "value": value, "ts": now, "createdAt": _ts()}
        self.device_telemetry.append(t)
        if len(self.device_telemetry) > 5000:
            self.device_telemetry.pop(0)
        return t

    def device_telemetry_list(self, tenant_id: str, device_id: Optional[str] = None, limit: int = 100) -> List[dict]:
        out = [t for t in self.device_telemetry if t.get("tenantId") == tenant_id]
        if device_id:
            out = [t for t in out if t.get("deviceId") == device_id]
        return out[-limit:]


_store: Optional[MESStore] = None


def get_store() -> MESStore:
    global _store
    if _store is None:
        _store = MESStore()
    return _store
