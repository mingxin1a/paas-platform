"""TMS 内存存储：运单、车辆、司机、轨迹（模拟）、到货确认、费用、对账。多租户，工业物流。"""
from __future__ import annotations

import time
import uuid
from typing import Dict, List, Optional

def _ts(): return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
def _id(): return str(uuid.uuid4()).replace("-", "")[:16]


def _mask_phone(s: Optional[str]) -> str:
    if not s or len(s) < 7:
        return "***"
    return s[:3] + "****" + s[-4:]


def _mask_id_no(s: Optional[str]) -> str:
    if not s or len(s) < 8:
        return "***"
    return s[:4] + "**********" + s[-2:]


class TMSStore:
    def __init__(self) -> None:
        self.shipments: Dict[str, dict] = {}
        self.vehicles: Dict[str, dict] = {}
        self.drivers: Dict[str, dict] = {}
        self.tracks: List[dict] = []
        self.delivery_confirms: Dict[str, dict] = {}
        self.transport_costs: List[dict] = []
        self.reconciliations: Dict[str, dict] = {}
        self.route_plans: Dict[str, dict] = {}
        self._idem: Dict[str, str] = {}
        self._audit_log: List[dict] = []

    def idem_get(self, k: str) -> Optional[str]:
        return self._idem.get(k)

    def idem_set(self, k: str, v: str) -> None:
        self._idem[k] = v

    def _by_tenant(self, items: Dict[str, dict], tenant_id: str) -> List[dict]:
        return [v for v in items.values() if v.get("tenantId") == tenant_id]

    # ---------- 运单/运输订单（数据权限：物流专员只看自己负责的） ----------
    def shipment_list(self, tenant_id: str, owner_id: Optional[str] = None, page: int = 1, page_size: int = 20) -> tuple[List[dict], int]:
        out = self._by_tenant(self.shipments, tenant_id)
        if owner_id:
            out = [s for s in out if s.get("ownerId") == owner_id]
        total = len(out)
        start = (page - 1) * page_size
        return out[start:start + page_size], total

    def shipment_create(self, tenant_id: str, tracking_no: str = "", origin: str = "", destination: str = "", status: int = 1, owner_id: str = "", vehicle_id: str = "", driver_id: str = "", wms_outbound_order_id: str = "", erp_order_id: str = "") -> dict:
        sid = _id()
        now = _ts()
        s = {"shipmentId": sid, "tenantId": tenant_id, "trackingNo": tracking_no or sid[:8], "origin": origin, "destination": destination, "status": status, "ownerId": owner_id or "", "vehicleId": vehicle_id or "", "driverId": driver_id or "", "createdAt": now, "updatedAt": now}
        if wms_outbound_order_id:
            s["wmsOutboundOrderId"] = wms_outbound_order_id
        if erp_order_id:
            s["erpOrderId"] = erp_order_id
        self.shipments[sid] = s
        return s

    def shipment_get(self, tenant_id: str, shipment_id: str) -> Optional[dict]:
        s = self.shipments.get(shipment_id)
        return s if s and s.get("tenantId") == tenant_id else None

    def shipment_update_status(self, tenant_id: str, shipment_id: str, status: int) -> Optional[dict]:
        s = self.shipment_get(tenant_id, shipment_id)
        if not s:
            return None
        s["status"] = status
        s["updatedAt"] = _ts()
        return s

    def shipment_assign_vehicle_driver(self, tenant_id: str, shipment_id: str, vehicle_id: str = "", driver_id: str = "") -> Optional[dict]:
        s = self.shipment_get(tenant_id, shipment_id)
        if not s:
            return None
        if vehicle_id:
            s["vehicleId"] = vehicle_id
        if driver_id:
            s["driverId"] = driver_id
        s["updatedAt"] = _ts()
        return s

    # ---------- 车辆 ----------
    def vehicle_list(self, tenant_id: str) -> List[dict]:
        return self._by_tenant(self.vehicles, tenant_id)

    def vehicle_create(self, tenant_id: str, plate_no: str, model: str = "") -> dict:
        vid = _id()
        now = _ts()
        v = {"vehicleId": vid, "tenantId": tenant_id, "plateNo": plate_no, "model": model or "", "status": 1, "createdAt": now}
        self.vehicles[vid] = v
        return v

    # ---------- 司机（脱敏：手机号/身份证） ----------
    def driver_list(self, tenant_id: str, mask: bool = True) -> List[dict]:
        out = self._by_tenant(self.drivers, tenant_id)
        if mask:
            result = []
            for d in out:
                x = dict(d)
                x["phone"] = _mask_phone(x.get("phone"))
                x["idNo"] = _mask_id_no(x.get("idNo"))
                result.append(x)
            return result
        return out

    def driver_create(self, tenant_id: str, name: str, phone: str = "", id_no: str = "") -> dict:
        did = _id()
        now = _ts()
        d = {"driverId": did, "tenantId": tenant_id, "name": name, "phone": phone or "", "idNo": id_no or "", "status": 1, "createdAt": now}
        self.drivers[did] = d
        return d

    # ---------- 运输轨迹（模拟） ----------
    def track_add(self, tenant_id: str, shipment_id: str, lat: str = "", lng: str = "", node_name: str = "") -> dict:
        tid = _id()
        now = _ts()
        t = {"trackId": tid, "tenantId": tenant_id, "shipmentId": shipment_id, "lat": lat or "", "lng": lng or "", "nodeName": node_name or "", "occurredAt": now}
        self.tracks.append(t)
        return t

    def track_list(self, tenant_id: str, shipment_id: Optional[str] = None) -> List[dict]:
        out = [t for t in self.tracks if t.get("tenantId") == tenant_id]
        if shipment_id:
            out = [t for t in out if t.get("shipmentId") == shipment_id]
        return out

    # ---------- 到货确认 ----------
    def delivery_confirm_create(self, tenant_id: str, shipment_id: str, status: str = "confirmed") -> Optional[dict]:
        if not self.shipment_get(tenant_id, shipment_id):
            return None
        cid = _id()
        now = _ts()
        c = {"confirmId": cid, "tenantId": tenant_id, "shipmentId": shipment_id, "status": status, "signedAt": now, "createdAt": now}
        self.delivery_confirms[cid] = c
        self.shipment_update_status(tenant_id, shipment_id, 2)
        return c

    # ---------- 运输费用（支持结算状态 draft/settled） ----------
    def transport_cost_create(self, tenant_id: str, shipment_id: str, amount_cents: int, cost_type: str = "") -> dict:
        cid = _id()
        now = _ts()
        c = {"costId": cid, "tenantId": tenant_id, "shipmentId": shipment_id, "amountCents": amount_cents, "currency": "CNY", "costType": cost_type or "", "status": "draft", "createdAt": now}
        self.transport_costs.append(c)
        return c

    def transport_cost_settle(self, tenant_id: str, cost_id: str) -> Optional[dict]:
        for c in self.transport_costs:
            if c.get("costId") == cost_id and c.get("tenantId") == tenant_id:
                c["status"] = "settled"
                return c
        return None

    def transport_cost_list(self, tenant_id: str, shipment_id: Optional[str] = None, status: Optional[str] = None) -> List[dict]:
        out = [c for c in self.transport_costs if c.get("tenantId") == tenant_id]
        if shipment_id:
            out = [c for c in out if c.get("shipmentId") == shipment_id]
        if status:
            out = [c for c in out if (c.get("status") or "draft") == status]
        return out

    # ---------- 物流对账 ----------
    def reconciliation_create(self, tenant_id: str, period_start: str, period_end: str, total_amount_cents: int) -> dict:
        rid = _id()
        now = _ts()
        r = {"reconciliationId": rid, "tenantId": tenant_id, "periodStart": period_start, "periodEnd": period_end, "totalAmountCents": total_amount_cents, "status": "draft", "createdAt": now}
        self.reconciliations[rid] = r
        return r

    def reconciliation_list(self, tenant_id: str) -> List[dict]:
        return [r for r in self.reconciliations.values() if r.get("tenantId") == tenant_id]

    def reconciliation_confirm(self, tenant_id: str, reconciliation_id: str) -> Optional[dict]:
        r = self.reconciliations.get(reconciliation_id)
        if not r or r.get("tenantId") != tenant_id:
            return None
        r["status"] = "confirmed"
        return r

    def reconciliation_complete(self, tenant_id: str, reconciliation_id: str) -> Optional[dict]:
        r = self.reconciliations.get(reconciliation_id)
        if not r or r.get("tenantId") != tenant_id:
            return None
        r["status"] = "completed"
        return r

    def audit_append(self, tenant_id: str, user_id: str, operation_type: str, resource_type: str = "", resource_id: str = "", trace_id: str = "") -> None:
        self._audit_log.append({"tenantId": tenant_id, "userId": user_id, "operationType": operation_type, "resourceType": resource_type or "", "resourceId": resource_id or "", "traceId": trace_id or "", "occurredAt": _ts()})

    def audit_list(self, tenant_id: str, page: int = 1, page_size: int = 50, resource_type: Optional[str] = None) -> tuple:
        out = [e for e in self._audit_log if e.get("tenantId") == tenant_id]
        if resource_type:
            out = [e for e in out if (e.get("resourceType") or "") == resource_type]
        total = len(out)
        out = sorted(out, key=lambda x: x.get("occurredAt", ""), reverse=True)
        start = (page - 1) * page_size
        return out[start:start + page_size], total

    def shipment_batch_import(self, tenant_id: str, owner_id: str, items: List[dict]) -> List[dict]:
        created = []
        for it in items:
            s = self.shipment_create(tenant_id, it.get("trackingNo", ""), it.get("origin", ""), it.get("destination", ""), 1, owner_id)
            created.append(s)
        return created

    # ---------- 智能路线规划（返回途经点与预估距离/时长） ----------
    def route_plan_create(self, tenant_id: str, from_address: str, to_address: str, shipment_id: str = "") -> dict:
        rid = _id()
        now = _ts()
        waypoints = [from_address, to_address]
        distance_km = 0.0
        duration_min = 0
        r = {"routePlanId": rid, "tenantId": tenant_id, "shipmentId": shipment_id or "", "fromAddress": from_address, "toAddress": to_address, "waypoints": waypoints, "distanceKm": distance_km, "durationMin": duration_min, "createdAt": now}
        self.route_plans[rid] = r
        return r

    def route_plan_list(self, tenant_id: str, shipment_id: Optional[str] = None) -> List[dict]:
        out = [r for r in self.route_plans.values() if r.get("tenantId") == tenant_id]
        if shipment_id:
            out = [r for r in out if r.get("shipmentId") == shipment_id]
        return out

    def board_data(self, tenant_id: str) -> dict:
        shipments = self._by_tenant(self.shipments, tenant_id)
        by_status = {}
        for s in shipments:
            st = s.get("status", 1)
            by_status[st] = by_status.get(st, 0) + 1
        costs = self.transport_cost_list(tenant_id)
        total_cents = sum(c.get("amountCents", 0) for c in costs)
        return {"shipmentsByStatus": by_status, "totalShipments": len(shipments), "transportCostTotalCents": total_cents}


_store: Optional[TMSStore] = None


def get_store() -> TMSStore:
    global _store
    if _store is None:
        _store = TMSStore()
    return _store
