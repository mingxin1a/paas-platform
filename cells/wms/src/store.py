"""
WMS 内存存储：入库/出库、库位、库存、批次。多租户 tenant_id。
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())

def _id() -> str:
    return str(uuid.uuid4()).replace("-", "")[:16]


class WMSStore:
    def __init__(self) -> None:
        self.inventory: Dict[tuple, Dict] = {}  # (tenant_id, warehouse_id, sku_id) -> {quantity, updatedAt}
        self.inbound_orders: Dict[str, Dict] = {}
        self.inbound_lines: List[Dict] = []
        self.outbound_orders: Dict[str, Dict] = {}
        self.outbound_lines: List[Dict] = []
        self.locations: Dict[str, Dict] = {}
        self.lots: Dict[str, Dict] = {}
        self.transfers: Dict[str, Dict] = {}
        self.cycle_counts: List[Dict] = []
        self.freezes: Dict[str, Dict] = {}
        self.waves: Dict[str, Dict] = {}
        self.wave_pick_lines: List[Dict] = []
        self._idem: Dict[str, str] = {}
        self._receive_idem: Dict[str, tuple] = {}
        self._ship_idem: Dict[str, tuple] = {}
        self.safety_stock: Dict[tuple, int] = {}  # (tenant_id, warehouse_id, sku_id) -> min_quantity
        self._audit_log: List[Dict] = []

    def idem_get(self, k: str) -> Optional[str]:
        return self._idem.get(k)
    def idem_set(self, k: str, v: str) -> None:
        self._idem[k] = v

    def _inv_key(self, tenant_id: str, warehouse_id: str, sku_id: str) -> tuple:
        return (tenant_id, warehouse_id, sku_id)

    def inventory_get(self, tenant_id: str, warehouse_id: Optional[str], sku_id: Optional[str]) -> List[Dict]:
        out = []
        for (t, w, s), v in self.inventory.items():
            if t != tenant_id:
                continue
            if warehouse_id and w != warehouse_id:
                continue
            if sku_id and s != sku_id:
                continue
            out.append({"warehouseId": w, "skuId": s, "quantity": v.get("quantity", 0), "updatedAt": v.get("updatedAt", "")})
        return out

    def inventory_add(self, tenant_id: str, warehouse_id: str, sku_id: str, delta: int) -> int:
        k = self._inv_key(tenant_id, warehouse_id, sku_id)
        now = _ts()
        if k not in self.inventory:
            self.inventory[k] = {"quantity": 0, "updatedAt": now}
        self.inventory[k]["quantity"] = self.inventory[k]["quantity"] + delta
        self.inventory[k]["updatedAt"] = now
        return self.inventory[k]["quantity"]

    def inbound_list(self, tenant_id: str, warehouse_id: Optional[str] = None, status: Optional[int] = None) -> List[Dict]:
        out = [o for o in self.inbound_orders.values() if o.get("tenantId") == tenant_id]
        if warehouse_id:
            out = [o for o in out if o.get("warehouseId") == warehouse_id]
        if status is not None:
            out = [o for o in out if o.get("status") == status]
        return out

    def inbound_get(self, tenant_id: str, order_id: str) -> Optional[Dict]:
        o = self.inbound_orders.get(order_id)
        if not o or o.get("tenantId") != tenant_id:
            return None
        lines = [ln for ln in self.inbound_lines if ln.get("orderId") == order_id and ln.get("tenantId") == tenant_id]
        out = dict(o)
        out["lines"] = lines
        return out

    def inbound_create(self, tenant_id: str, warehouse_id: str, type_code: str = "purchase", source_order_id: str = "", erp_order_id: str = "") -> Dict:
        """typeCode: purchase | production | return；sourceOrderId/erpOrderId 用于生产入库联动追溯。"""
        oid = _id()
        now = _ts()
        o = {"orderId": oid, "tenantId": tenant_id, "warehouseId": warehouse_id, "typeCode": type_code, "status": 1, "createdAt": now, "updatedAt": now}
        if source_order_id:
            o["sourceOrderId"] = source_order_id
        if erp_order_id:
            o["erpOrderId"] = erp_order_id
        self.inbound_orders[oid] = o
        return o

    def inbound_add_line(self, tenant_id: str, order_id: str, sku_id: str, quantity: int, lot_number: Optional[str] = None, serial_numbers: Optional[List[str]] = None) -> Optional[Dict]:
        if order_id not in self.inbound_orders or self.inbound_orders[order_id].get("tenantId") != tenant_id:
            return None
        lid = _id()
        line = {"lineId": lid, "orderId": order_id, "tenantId": tenant_id, "skuId": sku_id, "quantity": quantity, "receivedQuantity": 0, "lotNumber": lot_number or "", "serialNumbers": serial_numbers or []}
        self.inbound_lines.append(line)
        return line

    def inbound_receive(self, tenant_id: str, order_id: str, line_id: str, received_quantity: int, warehouse_id: str, lot_number: Optional[str] = None, idempotent_key: str = "") -> Optional[Dict]:
        if idempotent_key and self._receive_idem.get(idempotent_key) == (order_id, line_id):
            for line in self.inbound_lines:
                if line.get("lineId") == line_id and line.get("orderId") == order_id:
                    return line
        if order_id not in self.inbound_orders or self.inbound_orders[order_id].get("tenantId") != tenant_id:
            return None
        for line in self.inbound_lines:
            if line.get("lineId") == line_id and line.get("orderId") == order_id:
                line["receivedQuantity"] = line.get("receivedQuantity", 0) + received_quantity
                self.inventory_add(tenant_id, warehouse_id, line["skuId"], received_quantity)
                lot_num = lot_number or line.get("lotNumber") or _id()[:8]
                if lot_num:
                    self._lot_add(tenant_id, warehouse_id, None, line["skuId"], lot_num, received_quantity, None, None, line.get("serialNumbers"))
                self.inbound_orders[order_id]["status"] = 2
                self.inbound_orders[order_id]["updatedAt"] = _ts()
                if idempotent_key:
                    self._receive_idem[idempotent_key] = (order_id, line_id)
                return line
        return None

    def outbound_list(self, tenant_id: str, warehouse_id: Optional[str] = None, status: Optional[int] = None) -> List[Dict]:
        out = [o for o in self.outbound_orders.values() if o.get("tenantId") == tenant_id]
        if warehouse_id:
            out = [o for o in out if o.get("warehouseId") == warehouse_id]
        if status is not None:
            out = [o for o in out if o.get("status") == status]
        return out

    def outbound_get(self, tenant_id: str, order_id: str) -> Optional[Dict]:
        o = self.outbound_orders.get(order_id)
        if not o or o.get("tenantId") != tenant_id:
            return None
        lines = [ln for ln in self.outbound_lines if ln.get("orderId") == order_id and ln.get("tenantId") == tenant_id]
        out = dict(o)
        out["lines"] = lines
        return out

    def outbound_create(self, tenant_id: str, warehouse_id: str, type_code: str = "sales", source_order_id: str = "", erp_order_id: str = "") -> Dict:
        """typeCode: sales | picking | transfer；sourceOrderId/erpOrderId 用于销售出库→TMS 联动与回写。"""
        oid = _id()
        now = _ts()
        o = {"orderId": oid, "tenantId": tenant_id, "warehouseId": warehouse_id, "typeCode": type_code, "status": 1, "createdAt": now, "updatedAt": now}
        if source_order_id:
            o["sourceOrderId"] = source_order_id
        if erp_order_id:
            o["erpOrderId"] = erp_order_id
        self.outbound_orders[oid] = o
        return o

    def outbound_update_status(self, tenant_id: str, order_id: str, status: int) -> Optional[Dict]:
        """更新出库单状态（如 3=已签收/已送达），供 TMS 签收回传。"""
        o = self.outbound_orders.get(order_id)
        if not o or o.get("tenantId") != tenant_id:
            return None
        o["status"] = status
        o["updatedAt"] = _ts()
        return dict(o)

    def outbound_add_line(self, tenant_id: str, order_id: str, sku_id: str, quantity: int) -> Optional[Dict]:
        if order_id not in self.outbound_orders or self.outbound_orders[order_id].get("tenantId") != tenant_id:
            return None
        lid = _id()
        line = {"lineId": lid, "orderId": order_id, "tenantId": tenant_id, "skuId": sku_id, "quantity": quantity, "pickedQuantity": 0}
        self.outbound_lines.append(line)
        return line

    def outbound_ship(self, tenant_id: str, order_id: str, line_id: str, picked_quantity: int, warehouse_id: str, idempotent_key: str = "") -> Optional[Dict]:
        """出库；防负库存：扣减前检查可用量。幂等：同一 idempotent_key 返回已处理结果。"""
        if idempotent_key and hasattr(self, "_ship_idem") and self._ship_idem.get(idempotent_key):
            oid, lid = self._ship_idem[idempotent_key]
            if oid == order_id and lid == line_id:
                for line in self.outbound_lines:
                    if line.get("lineId") == line_id and line.get("orderId") == order_id:
                        return line
        if order_id not in self.outbound_orders or self.outbound_orders[order_id].get("tenantId") != tenant_id:
            return None
        for line in self.outbound_lines:
            if line.get("lineId") == line_id and line.get("orderId") == order_id:
                key = self._inv_key(tenant_id, warehouse_id, line["skuId"])
                available = self.inventory.get(key, {}).get("quantity", 0)
                if available < picked_quantity:
                    return None  # 防负库存
                line["pickedQuantity"] = line.get("pickedQuantity", 0) + picked_quantity
                self.inventory_add(tenant_id, warehouse_id, line["skuId"], -picked_quantity)
                self.outbound_orders[order_id]["status"] = 2
                self.outbound_orders[order_id]["updatedAt"] = _ts()
                if idempotent_key:
                    if not hasattr(self, "_ship_idem"):
                        self._ship_idem = {}
                    self._ship_idem[idempotent_key] = (order_id, line_id)
                return line
        return None

    def _lot_add(self, tenant_id: str, warehouse_id: str, location_id: Optional[str], sku_id: str, lot_number: str, quantity: int, production_date: Optional[str], expiry_date: Optional[str], serial_numbers: Optional[List[str]] = None) -> Dict:
        lid = _id()
        now = _ts()
        lot = {"lotId": lid, "tenantId": tenant_id, "warehouseId": warehouse_id, "locationId": location_id or "", "skuId": sku_id, "lotNumber": lot_number, "quantity": quantity, "productionDate": production_date or "", "expiryDate": expiry_date or "", "serialNumbers": serial_numbers or [], "createdAt": now}
        self.lots[lid] = lot
        return lot

    def lot_list(self, tenant_id: str, sku_id: Optional[str] = None, lot_number: Optional[str] = None, warehouse_id: Optional[str] = None) -> List[Dict]:
        out = [dict(l) for l in self.lots.values() if l.get("tenantId") == tenant_id and l.get("quantity", 0) > 0]
        if sku_id:
            out = [l for l in out if l.get("skuId") == sku_id]
        if lot_number:
            out = [l for l in out if l.get("lotNumber") == lot_number]
        if warehouse_id:
            out = [l for l in out if l.get("warehouseId") == warehouse_id]
        return out

    def trace_by_serial(self, tenant_id: str, serial_number: str) -> List[Dict]:
        """批次/序列号追溯：按序列号查批次及库存信息"""
        out = []
        for lot in self.lots.values():
            if lot.get("tenantId") != tenant_id:
                continue
            if serial_number not in (lot.get("serialNumbers") or []):
                continue
            out.append({"lotId": lot["lotId"], "lotNumber": lot.get("lotNumber"), "warehouseId": lot.get("warehouseId"), "skuId": lot.get("skuId"), "quantity": lot.get("quantity", 0), "expiryDate": lot.get("expiryDate"), "createdAt": lot.get("createdAt")})
        return out

    def set_safety_stock(self, tenant_id: str, warehouse_id: str, sku_id: str, min_quantity: int) -> None:
        self.safety_stock[self._inv_key(tenant_id, warehouse_id, sku_id)] = max(0, min_quantity)

    def stock_alert_list(self, tenant_id: str, warehouse_id: Optional[str] = None) -> List[Dict]:
        """库存预警：当前库存低于安全库存的 SKU 列表"""
        out = []
        for (t, w, s), inv in self.inventory.items():
            if t != tenant_id or inv.get("quantity", 0) is None:
                continue
            if warehouse_id and w != warehouse_id:
                continue
            safe = self.safety_stock.get((t, w, s), 0)
            if safe <= 0:
                continue
            if inv.get("quantity", 0) < safe:
                out.append({"warehouseId": w, "skuId": s, "quantity": inv.get("quantity", 0), "safetyStock": safe, "alertType": "LOW_STOCK"})
        return out

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

    def lot_get(self, tenant_id: str, lot_id: str) -> Optional[Dict]:
        lot = self.lots.get(lot_id)
        if not lot or lot.get("tenantId") != tenant_id:
            return None
        return dict(lot)

    def lot_fifo(self, tenant_id: str, warehouse_id: str, sku_id: str, quantity: int) -> List[Dict]:
        out = [l for l in self.lots.values() if l.get("tenantId") == tenant_id and l.get("warehouseId") == warehouse_id and l.get("skuId") == sku_id and l.get("quantity", 0) > 0]
        out.sort(key=lambda x: x.get("expiryDate") or "9999-12-31")
        result = []
        need = quantity
        for l in out:
            if need <= 0:
                break
            take = min(need, l.get("quantity", 0))
            if take > 0:
                result.append({"lotId": l["lotId"], "lotNumber": l["lotNumber"], "quantityToTake": take, "expiryDate": l.get("expiryDate")})
            need -= take
        return result

    def location_list(self, tenant_id: str, warehouse_id: Optional[str] = None) -> List[Dict]:
        out = [loc for loc in self.locations.values() if loc.get("tenantId") == tenant_id]
        if warehouse_id:
            out = [loc for loc in out if loc.get("warehouseId") == warehouse_id]
        return out

    def location_get(self, tenant_id: str, location_id: str) -> Optional[Dict]:
        loc = self.locations.get(location_id)
        if not loc or loc.get("tenantId") != tenant_id:
            return None
        return dict(loc)

    def location_create(self, tenant_id: str, warehouse_id: str, location_id: str, zone_code: str = "", aisle: str = "", level: str = "", position: str = "") -> Dict:
        now = _ts()
        loc = {"locationId": location_id, "tenantId": tenant_id, "warehouseId": warehouse_id, "zoneCode": zone_code, "aisle": aisle, "level": level, "position": position, "status": 1, "createdAt": now}
        self.locations[location_id] = loc
        return loc

    # ---------- 调拨 ----------
    def transfer_create(self, tenant_id: str, from_wh: str, to_wh: str, sku_id: str, quantity: int, idempotent_key: str = "") -> Optional[Dict]:
        key = self._inv_key(tenant_id, from_wh, sku_id)
        available = self.inventory.get(key, {}).get("quantity", 0)
        if available < quantity:
            return None
        tid = _id()
        now = _ts()
        t = {"transferId": tid, "tenantId": tenant_id, "fromWarehouseId": from_wh, "toWarehouseId": to_wh, "skuId": sku_id, "quantity": quantity, "status": 1, "createdAt": now, "idempotentKey": idempotent_key or ""}
        self.transfers[tid] = t
        self.inventory_add(tenant_id, from_wh, sku_id, -quantity)
        self.inventory_add(tenant_id, to_wh, sku_id, quantity)
        return t

    def transfer_list(self, tenant_id: str) -> List[Dict]:
        return [t for t in self.transfers.values() if t.get("tenantId") == tenant_id]

    # ---------- 盘点（批量 1000+） ----------
    def cycle_count_batch(self, tenant_id: str, warehouse_id: str, items: List[Dict]) -> List[Dict]:
        """items: [{skuId, locationId?, bookQuantity, countQuantity}]"""
        result = []
        now = _ts()
        for it in items:
            cid = _id()
            c = {"countId": cid, "tenantId": tenant_id, "warehouseId": warehouse_id, "skuId": it.get("skuId", ""), "locationId": it.get("locationId", ""), "bookQuantity": int(it.get("bookQuantity", 0)), "countQuantity": it.get("countQuantity"), "countAt": now, "createdAt": now}
            self.cycle_counts.append(c)
            result.append(c)
        return result

    def cycle_count_list(self, tenant_id: str, warehouse_id: Optional[str] = None) -> List[Dict]:
        out = [c for c in self.cycle_counts if c.get("tenantId") == tenant_id]
        if warehouse_id:
            out = [c for c in out if c.get("warehouseId") == warehouse_id]
        return out

    # ---------- 库存冻结/解冻 ----------
    def freeze_add(self, tenant_id: str, warehouse_id: str, sku_id: str, quantity: int, reason: str = "") -> Optional[Dict]:
        key = self._inv_key(tenant_id, warehouse_id, sku_id)
        available = self.inventory.get(key, {}).get("quantity", 0)
        if available < quantity:
            return None
        fid = _id()
        now = _ts()
        f = {"freezeId": fid, "tenantId": tenant_id, "warehouseId": warehouse_id, "skuId": sku_id, "quantity": quantity, "reason": reason or "", "createdAt": now}
        self.freezes[fid] = f
        self.inventory_add(tenant_id, warehouse_id, sku_id, -quantity)
        return f

    def freeze_release(self, tenant_id: str, freeze_id: str) -> Optional[Dict]:
        f = self.freezes.get(freeze_id)
        if not f or f.get("tenantId") != tenant_id:
            return None
        self.inventory_add(tenant_id, f["warehouseId"], f["skuId"], f["quantity"])
        del self.freezes[freeze_id]
        return f

    def expiry_alert_list(self, tenant_id: str, days_ahead: int = 30) -> List[Dict]:
        from datetime import datetime, timedelta, timezone
        threshold = (datetime.now(timezone.utc) + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        out = [l for l in self.lots.values() if l.get("tenantId") == tenant_id and l.get("quantity", 0) > 0 and l.get("expiryDate") and l.get("expiryDate") <= threshold]
        return out

    # ---------- 波次拣货 ----------
    def wave_list(self, tenant_id: str, warehouse_id: Optional[str] = None, status: Optional[int] = None) -> List[Dict]:
        out = [w for w in self.waves.values() if w.get("tenantId") == tenant_id]
        if warehouse_id:
            out = [w for w in out if w.get("warehouseId") == warehouse_id]
        if status is not None:
            out = [w for w in out if w.get("status") == status]
        return out

    def wave_create(self, tenant_id: str, warehouse_id: str, outbound_order_ids: List[str]) -> Dict:
        wid = _id()
        now = _ts()
        w = {"waveId": wid, "tenantId": tenant_id, "warehouseId": warehouse_id, "outboundOrderIds": outbound_order_ids or [], "status": 1, "createdAt": now}
        self.waves[wid] = w
        lines = []
        for idx, oid in enumerate(outbound_order_ids or []):
            for ln in self.outbound_lines:
                if ln.get("orderId") == oid and ln.get("tenantId") == tenant_id:
                    plid = _id()
                    lines.append({"pickLineId": plid, "tenantId": tenant_id, "waveId": wid, "orderId": oid, "lineId": ln["lineId"], "skuId": ln["skuId"], "quantity": ln.get("quantity", 0), "pickedQuantity": 0, "sortOrder": idx})
        self.wave_pick_lines.extend(lines)
        return w

    def wave_get_picks(self, tenant_id: str, wave_id: str) -> List[Dict]:
        if wave_id not in self.waves or self.waves[wave_id].get("tenantId") != tenant_id:
            return []
        return [p for p in self.wave_pick_lines if p.get("waveId") == wave_id and p.get("tenantId") == tenant_id]

    def wave_confirm_pick(self, tenant_id: str, wave_id: str, pick_line_id: str, picked_qty: int) -> Optional[Dict]:
        for p in self.wave_pick_lines:
            if p.get("pickLineId") == pick_line_id and p.get("waveId") == wave_id and p.get("tenantId") == tenant_id:
                p["pickedQuantity"] = p.get("pickedQuantity", 0) + picked_qty
                return p
        return None

    def board_data(self, tenant_id: str) -> Dict:
        in_list = self.inbound_list(tenant_id, status=1)
        out_list = self.outbound_list(tenant_id, status=1)
        inv = self.inventory_get(tenant_id, None, None)
        total_qty = sum(i.get("quantity", 0) for i in inv)
        return {"inboundPending": len(in_list), "outboundPending": len(out_list), "inventorySkus": len(inv), "inventoryTotalQuantity": total_qty}


_store: Optional[WMSStore] = None
def get_store() -> WMSStore:
    global _store
    if _store is None:
        _store = WMSStore()
    return _store
