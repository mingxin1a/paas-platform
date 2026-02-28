"""PLM 内存存储：产品、BOM 版本、工艺、变更记录、产品文档。多租户；研发数据权限（owner_id）。"""
from __future__ import annotations

import time
import uuid
from typing import Dict, List, Optional, Tuple

def _ts(): return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
def _id(): return str(uuid.uuid4()).replace("-", "")[:16]


class PLMStore:
    def __init__(self) -> None:
        self.products: Dict[str, dict] = {}
        self.boms: Dict[str, dict] = {}
        self.change_records: List[dict] = []
        self.documents: List[dict] = []
        self.process_routes: Dict[str, dict] = {}  # 工艺路线
        self._audit_log: List[dict] = []  # 研发合规：不可篡改操作日志
        self._idem: Dict[str, str] = {}

    def idem_get(self, k: str) -> Optional[str]:
        return self._idem.get(k)

    def idem_set(self, k: str, v: str) -> None:
        self._idem[k] = v

    def _by_tenant(self, d: Dict[str, dict], tenant_id: str) -> List[dict]:
        return [v for v in d.values() if v.get("tenantId") == tenant_id]

    def product_list(self, tenant_id: str, owner_id: Optional[str] = None, page: int = 1, page_size: int = 20) -> Tuple[List[dict], int]:
        out = self._by_tenant(self.products, tenant_id)
        if owner_id:
            out = [p for p in out if p.get("ownerId") == owner_id]
        total = len(out)
        start = (page - 1) * page_size
        return out[start:start + page_size], total

    def product_create(self, tenant_id: str, product_code: str, name: str, version: str = "1.0", owner_id: str = "") -> dict:
        pid = _id()
        now = _ts()
        p = {"productId": pid, "tenantId": tenant_id, "productCode": product_code, "name": name, "version": version, "status": 1, "ownerId": owner_id or "", "createdAt": now, "updatedAt": now}
        self.products[pid] = p
        return p

    def product_get(self, tenant_id: str, product_id: str) -> Optional[dict]:
        p = self.products.get(product_id)
        return p if p and p.get("tenantId") == tenant_id else None

    def bom_list(self, tenant_id: str, product_id: Optional[str] = None, version: Optional[int] = None) -> List[dict]:
        out = self._by_tenant(self.boms, tenant_id)
        if product_id:
            out = [b for b in out if b.get("productId") == product_id]
        if version is not None:
            out = [b for b in out if b.get("version") == version]
        return out

    def bom_create(self, tenant_id: str, product_id: str, parent_id: str = "", quantity: float = 1.0, version: int = 1) -> dict:
        bid = _id()
        now = _ts()
        b = {"bomId": bid, "tenantId": tenant_id, "productId": product_id, "parentId": parent_id, "quantity": quantity, "version": version, "createdAt": now}
        self.boms[bid] = b
        return b

    def bom_get(self, tenant_id: str, bom_id: str) -> Optional[dict]:
        b = self.boms.get(bom_id)
        return b if b and b.get("tenantId") == tenant_id else None

    def change_record_add(self, tenant_id: str, entity_type: str, entity_id: str, change_type: str, description: str, changed_by: str) -> dict:
        cid = _id()
        now = _ts()
        c = {"changeId": cid, "tenantId": tenant_id, "entityType": entity_type, "entityId": entity_id, "changeType": change_type, "description": description or "", "changedBy": changed_by, "createdAt": now}
        self.change_records.append(c)
        return c

    def change_record_list(self, tenant_id: str, entity_type: Optional[str] = None, entity_id: Optional[str] = None, page: int = 1, page_size: int = 20) -> Tuple[List[dict], int]:
        out = [c for c in self.change_records if c.get("tenantId") == tenant_id]
        if entity_type:
            out = [c for c in out if c.get("entityType") == entity_type]
        if entity_id:
            out = [c for c in out if c.get("entityId") == entity_id]
        out.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
        total = len(out)
        start = (page - 1) * page_size
        return out[start:start + page_size], total

    def document_add(self, tenant_id: str, product_id: str, doc_type: str, version: int = 1, storage_path: str = "") -> dict:
        did = _id()
        now = _ts()
        d = {"docId": did, "tenantId": tenant_id, "productId": product_id, "docType": doc_type, "version": version, "storagePath": storage_path or "", "createdAt": now}
        self.documents.append(d)
        return d

    def document_list(self, tenant_id: str, product_id: Optional[str] = None, doc_type: Optional[str] = None) -> List[dict]:
        out = [d for d in self.documents if d.get("tenantId") == tenant_id]
        if product_id:
            out = [d for d in out if d.get("productId") == product_id]
        if doc_type:
            out = [d for d in out if d.get("docType") == doc_type]
        return out

    def process_route_list(self, tenant_id: str, product_id: Optional[str] = None) -> List[dict]:
        out = self._by_tenant(self.process_routes, tenant_id)
        if product_id:
            out = [p for p in out if p.get("productId") == product_id]
        return out

    def process_route_create(self, tenant_id: str, product_id: str, name: str, version: int = 1, steps: str = "") -> dict:
        pid = _id()
        now = _ts()
        p = {"processRouteId": pid, "tenantId": tenant_id, "productId": product_id, "name": name, "version": version, "steps": steps or "", "status": 1, "createdAt": now}
        self.process_routes[pid] = p
        return p

    def process_route_get(self, tenant_id: str, process_route_id: str) -> Optional[dict]:
        p = self.process_routes.get(process_route_id)
        return p if p and p.get("tenantId") == tenant_id else None

    def audit_append(self, tenant_id: str, user_id: str, action: str, resource_type: str, resource_id: str, trace_id: str = "") -> None:
        self._audit_log.append({
            "tenantId": tenant_id, "userId": user_id, "action": action,
            "resourceType": resource_type, "resourceId": resource_id,
            "traceId": trace_id, "occurredAt": _ts(),
        })

    def audit_list(self, tenant_id: str, page: int = 1, page_size: int = 50, resource_type: Optional[str] = None) -> Tuple[List[dict], int]:
        out = [a for a in self._audit_log if a.get("tenantId") == tenant_id]
        if resource_type:
            out = [a for a in out if a.get("resourceType") == resource_type]
        out.sort(key=lambda x: x.get("occurredAt", ""), reverse=True)
        total = len(out)
        start = (page - 1) * page_size
        return out[start : start + page_size], total

    def product_batch_import(self, tenant_id: str, owner_id: str, items: List[dict]) -> List[dict]:
        created = []
        for it in items:
            code = (it.get("productCode") or "").strip()
            name = (it.get("name") or "").strip()
            if not code or not name:
                continue
            p = self.product_create(tenant_id, code, name, it.get("version", "1.0"), owner_id)
            created.append(p)
        return created


_store: Optional[PLMStore] = None


def get_store() -> PLMStore:
    global _store
    if _store is None:
        _store = PLMStore()
    return _store
