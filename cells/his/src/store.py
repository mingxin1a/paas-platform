"""HIS 内存存储：患者、挂号、就诊、处方、收费、住院、病历。多租户；患者信息脱敏；医生仅看本人患者。"""
from __future__ import annotations

import hashlib
import time
import uuid
from typing import Dict, List, Optional, Tuple

def _ts(): return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
def _id(): return str(uuid.uuid4()).replace("-", "")[:16]


def _mask_name(name: str) -> str:
    if not name or len(name) < 2:
        return name or "***"
    return name[0] + "*" * (len(name) - 2) + (name[-1] if len(name) > 1 else "")


def _mask_id_no(id_no: str) -> str:
    if not id_no or len(id_no) < 8:
        return "***"
    return id_no[:4] + "**********" + id_no[-2:]


class HISStore:
    def __init__(self) -> None:
        self.patients: Dict[str, dict] = {}
        self.visits: Dict[str, dict] = {}
        self.orders: Dict[str, dict] = {}
        self.registrations: Dict[str, dict] = {}
        self.prescriptions: Dict[str, dict] = {}
        self.charges: Dict[str, dict] = {}
        self.inpatients: Dict[str, dict] = {}
        self.medical_records: List[dict] = []
        self._idem: Dict[str, str] = {}
        self._audit_log: List[dict] = []  # 医疗合规：不可篡改操作日志

    def idem_get(self, k: str) -> Optional[str]:
        return self._idem.get(k)

    def idem_set(self, k: str, v: str) -> None:
        self._idem[k] = v

    def _by_tenant(self, d: Dict[str, dict], tenant_id: str) -> List[dict]:
        return [v for v in d.values() if v.get("tenantId") == tenant_id]

    def patient_list(self, tenant_id: str, doctor_id: Optional[str] = None) -> List[dict]:
        out = self._by_tenant(self.patients, tenant_id)
        if doctor_id:
            out = [p for p in out if p.get("doctorId") == doctor_id]
        return out

    def patient_create(self, tenant_id: str, patient_no: str, name: str, gender: str = "", id_no: str = "", doctor_id: str = "") -> dict:
        pid = _id()
        now = _ts()
        p = {"patientId": pid, "tenantId": tenant_id, "patientNo": patient_no, "name": name, "gender": gender, "idNo": id_no or "", "doctorId": doctor_id or "", "status": 1, "createdAt": now, "updatedAt": now}
        self.patients[pid] = p
        return p

    def patient_get(self, tenant_id: str, patient_id: str) -> Optional[dict]:
        p = self.patients.get(patient_id)
        return p if p and p.get("tenantId") == tenant_id else None

    def visit_list(self, tenant_id: str, doctor_id: Optional[str] = None) -> List[dict]:
        out = self._by_tenant(self.visits, tenant_id)
        if doctor_id:
            out = [v for v in out if v.get("doctorId") == doctor_id]
        return out

    def visit_create(self, tenant_id: str, patient_id: str, department_id: str = "", doctor_id: str = "") -> dict:
        vid = _id()
        now = _ts()
        v = {"visitId": vid, "tenantId": tenant_id, "patientId": patient_id, "departmentId": department_id, "doctorId": doctor_id or "", "status": 1, "createdAt": now, "updatedAt": now}
        self.visits[vid] = v
        return v

    def visit_get(self, tenant_id: str, visit_id: str) -> Optional[dict]:
        v = self.visits.get(visit_id)
        return v if v and v.get("tenantId") == tenant_id else None

    def order_list(self, tenant_id: str) -> List[dict]:
        return self._by_tenant(self.orders, tenant_id)

    def order_create(self, tenant_id: str, visit_id: str, order_type: str, content: str) -> dict:
        oid = _id()
        now = _ts()
        o = {"orderId": oid, "tenantId": tenant_id, "visitId": visit_id, "orderType": order_type, "content": content, "status": 1, "createdAt": now, "updatedAt": now}
        self.orders[oid] = o
        return o

    def order_get(self, tenant_id: str, order_id: str) -> Optional[dict]:
        o = self.orders.get(order_id)
        return o if o and o.get("tenantId") == tenant_id else None

    def registration_create(self, tenant_id: str, patient_id: str, department_id: str = "", schedule_date: str = "", idempotent_key: str = "") -> Tuple[dict, bool]:
        if idempotent_key:
            for r in self.registrations.values():
                if r.get("tenantId") == tenant_id and r.get("idempotentKey") == idempotent_key:
                    return r, False
        rid = _id()
        now = _ts()
        r = {"registrationId": rid, "tenantId": tenant_id, "patientId": patient_id, "departmentId": department_id or "", "scheduleDate": schedule_date or now[:10], "status": 1, "createdAt": now, "idempotentKey": idempotent_key or ""}
        self.registrations[rid] = r
        return r, True

    def prescription_create(self, tenant_id: str, visit_id: str, drug_list: str = "", content_hash: str = "") -> Tuple[dict, bool]:
        h = content_hash or (hashlib.sha256((visit_id + "|" + drug_list).encode()).hexdigest()[:32])
        for p in self.prescriptions.values():
            if p.get("tenantId") == tenant_id and p.get("visitId") == visit_id and p.get("contentHash") == h:
                return p, False
        pid = _id()
        now = _ts()
        p = {"prescriptionId": pid, "tenantId": tenant_id, "visitId": visit_id, "drugList": drug_list, "contentHash": h, "status": 1, "createdAt": now}
        self.prescriptions[pid] = p
        return p, True

    def charge_create(self, tenant_id: str, visit_id: str, amount_cents: int, idempotent_key: str = "") -> Tuple[dict, bool]:
        if idempotent_key:
            for c in self.charges.values():
                if c.get("tenantId") == tenant_id and c.get("idempotentKey") == idempotent_key:
                    return c, False
        cid = _id()
        now = _ts()
        c = {"chargeId": cid, "tenantId": tenant_id, "visitId": visit_id, "amountCents": amount_cents, "paidCents": 0, "status": 1, "createdAt": now, "idempotentKey": idempotent_key or ""}
        self.charges[cid] = c
        return c, True

    def charge_pay(self, tenant_id: str, charge_id: str, pay_cents: int) -> Optional[dict]:
        c = self.charges.get(charge_id)
        if not c or c.get("tenantId") != tenant_id:
            return None
        paid = c.get("paidCents", 0) + pay_cents
        c["paidCents"] = paid
        c["status"] = 2 if paid >= c.get("amountCents", 0) else 1
        return c

    def charge_get(self, tenant_id: str, charge_id: str) -> Optional[dict]:
        c = self.charges.get(charge_id)
        return c if c and c.get("tenantId") == tenant_id else None

    def charge_list_by_visit(self, tenant_id: str, visit_id: str) -> List[dict]:
        return [c for c in self.charges.values() if c.get("tenantId") == tenant_id and c.get("visitId") == visit_id]

    def inpatient_create(self, tenant_id: str, patient_id: str, bed_no: str = "") -> dict:
        iid = _id()
        now = _ts()
        i = {"inpatientId": iid, "tenantId": tenant_id, "patientId": patient_id, "bedNo": bed_no or "", "admittedAt": now, "status": 1, "createdAt": now}
        self.inpatients[iid] = i
        return i

    def medical_record_append(self, tenant_id: str, patient_id: str, visit_id: str, content: str) -> dict:
        rid = _id()
        now = _ts()
        r = {"recordId": rid, "tenantId": tenant_id, "patientId": patient_id, "visitId": visit_id or "", "content": content, "createdAt": now}
        self.medical_records.append(r)
        return r

    def medical_record_list(self, tenant_id: str, patient_id: Optional[str] = None) -> List[dict]:
        out = [r for r in self.medical_records if r.get("tenantId") == tenant_id]
        if patient_id:
            out = [r for r in out if r.get("patientId") == patient_id]
        return out

    def registration_list(self, tenant_id: str, patient_id: Optional[str] = None) -> List[dict]:
        out = self._by_tenant(self.registrations, tenant_id)
        if patient_id:
            out = [r for r in out if r.get("patientId") == patient_id]
        return out

    def charge_list(self, tenant_id: str, visit_id: Optional[str] = None) -> List[dict]:
        out = self._by_tenant(self.charges, tenant_id)
        if visit_id:
            out = [c for c in out if c.get("visitId") == visit_id]
        return out

    def inpatient_list(self, tenant_id: str, patient_id: Optional[str] = None) -> List[dict]:
        out = self._by_tenant(self.inpatients, tenant_id)
        if patient_id:
            out = [i for i in out if i.get("patientId") == patient_id]
        return out

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

    @staticmethod
    def apply_patient_masking(row: dict) -> dict:
        out = dict(row)
        if out.get("name"):
            out["name"] = _mask_name(out["name"])
        if out.get("idNo"):
            out["idNo"] = _mask_id_no(out["idNo"])
        return out


_store: Optional[HISStore] = None


def get_store() -> HISStore:
    global _store
    if _store is None:
        _store = HISStore()
    return _store
