"""HRM 内存存储：员工、部门、请假。多租户。"""
from __future__ import annotations
import time
import uuid
from typing import Dict, List, Optional

def _ts(): return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
def _id(): return str(uuid.uuid4()).replace("-", "")[:16]

class HRMStore:
    def __init__(self) -> None:
        self.employees: Dict[str, dict] = {}
        self.departments: Dict[str, dict] = {}
        self.leave_requests: Dict[str, dict] = {}
        self._idem: Dict[str, str] = {}

    def idem_get(self, k: str) -> Optional[str]: return self._idem.get(k)
    def idem_set(self, k: str, v: str) -> None: self._idem[k] = v

    def _by_tenant(self, d: Dict[str, dict], tenant_id: str) -> List[dict]:
        return [v for v in d.values() if v.get("tenantId") == tenant_id]

    def employee_list(self, tenant_id: str) -> List[dict]:
        return self._by_tenant(self.employees, tenant_id)
    def employee_create(self, tenant_id: str, name: str, department_id: str = "", employee_no: str = "") -> dict:
        eid = _id()
        now = _ts()
        e = {"employeeId": eid, "tenantId": tenant_id, "departmentId": department_id, "name": name, "employeeNo": employee_no, "status": 1, "createdAt": now, "updatedAt": now}
        self.employees[eid] = e
        return e

    def department_list(self, tenant_id: str) -> List[dict]:
        return self._by_tenant(self.departments, tenant_id)
    def department_create(self, tenant_id: str, name: str, parent_id: str = "") -> dict:
        did = _id()
        now = _ts()
        d = {"departmentId": did, "tenantId": tenant_id, "name": name, "parentId": parent_id, "createdAt": now}
        self.departments[did] = d
        return d

    def leave_list(self, tenant_id: str) -> List[dict]:
        return self._by_tenant(self.leave_requests, tenant_id)
    def leave_create(self, tenant_id: str, employee_id: str, leave_type: str, start_date: str, end_date: str, days: float) -> dict:
        rid = _id()
        now = _ts()
        r = {"requestId": rid, "tenantId": tenant_id, "employeeId": employee_id, "leaveType": leave_type, "startDate": start_date, "endDate": end_date, "days": days, "status": 1, "createdAt": now}
        self.leave_requests[rid] = r
        return r

    def employee_get(self, tenant_id: str, employee_id: str) -> Optional[dict]:
        e = self.employees.get(employee_id)
        return e if e and e.get("tenantId") == tenant_id else None

    def department_get(self, tenant_id: str, department_id: str) -> Optional[dict]:
        d = self.departments.get(department_id)
        return d if d and d.get("tenantId") == tenant_id else None

    def leave_get(self, tenant_id: str, request_id: str) -> Optional[dict]:
        r = self.leave_requests.get(request_id)
        return r if r and r.get("tenantId") == tenant_id else None

    def leave_update_status(self, tenant_id: str, request_id: str, status: int) -> Optional[dict]:
        r = self.leave_get(tenant_id, request_id)
        if not r:
            return None
        r["status"] = status
        return r

_store: Optional[HRMStore] = None
def get_store() -> HRMStore:
    global _store
    if _store is None: _store = HRMStore()
    return _store
