"""LIMS 内存存储：样品、实验任务、实验数据、实验报告、数据溯源。多租户；实验数据留存≥5年（配置）；人员权限。"""
from __future__ import annotations

import time
import uuid
from typing import Dict, List, Optional

def _ts(): return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
def _id(): return str(uuid.uuid4()).replace("-", "")[:16]


class LIMSStore:
    def __init__(self) -> None:
        self.samples: Dict[str, dict] = {}
        self.results: Dict[str, dict] = {}
        self.tasks: Dict[str, dict] = {}
        self.experiment_data: List[dict] = []
        self.reports: Dict[str, dict] = {}
        self.traces: List[dict] = []
        self._audit_log: List[dict] = []
        self._idem: Dict[str, str] = {}

    def idem_get(self, k: str) -> Optional[str]:
        return self._idem.get(k)

    def idem_set(self, k: str, v: str) -> None:
        self._idem[k] = v

    def _by_tenant(self, d: Dict[str, dict], tenant_id: str) -> List[dict]:
        return [v for v in d.values() if v.get("tenantId") == tenant_id]

    def sample_list(self, tenant_id: str, operator_id: Optional[str] = None) -> List[dict]:
        out = self._by_tenant(self.samples, tenant_id)
        if operator_id:
            out = [s for s in out if s.get("operatorId") == operator_id]
        return out

    def sample_create(self, tenant_id: str, sample_no: str, batch_id: str = "", test_type: str = "", operator_id: str = "") -> dict:
        sid = _id()
        now = _ts()
        s = {"sampleId": sid, "tenantId": tenant_id, "sampleNo": sample_no, "batchId": batch_id or "", "testType": test_type or "", "operatorId": operator_id or "", "status": 0, "createdAt": now, "updatedAt": now, "receivedAt": ""}
        self.samples[sid] = s
        return s

    def sample_receive(self, tenant_id: str, sample_id: str) -> Optional[dict]:
        """样品接收：实验室合规要求记录接收时间。"""
        s = self.samples.get(sample_id)
        if not s or s.get("tenantId") != tenant_id:
            return None
        now = _ts()
        s["status"] = 1
        s["receivedAt"] = now
        s["updatedAt"] = now
        return s

    def sample_get(self, tenant_id: str, sample_id: str) -> Optional[dict]:
        s = self.samples.get(sample_id)
        return s if s and s.get("tenantId") == tenant_id else None

    def result_list(self, tenant_id: str, sample_id: Optional[str] = None) -> List[dict]:
        out = self._by_tenant(self.results, tenant_id)
        if sample_id:
            out = [r for r in out if r.get("sampleId") == sample_id]
        return out

    def result_create(self, tenant_id: str, sample_id: str, test_item: str, value: str, unit: str = "") -> dict:
        rid = _id()
        now = _ts()
        r = {"resultId": rid, "tenantId": tenant_id, "sampleId": sample_id, "testItem": test_item, "value": value, "unit": unit, "createdAt": now}
        self.results[rid] = r
        return r

    def result_get(self, tenant_id: str, result_id: str) -> Optional[dict]:
        r = self.results.get(result_id)
        return r if r and r.get("tenantId") == tenant_id else None

    def task_list(self, tenant_id: str, sample_id: Optional[str] = None, operator_id: Optional[str] = None) -> List[dict]:
        out = [t for t in self.tasks.values() if t.get("tenantId") == tenant_id]
        if sample_id:
            out = [t for t in out if t.get("sampleId") == sample_id]
        if operator_id:
            out = [t for t in out if t.get("operatorId") == operator_id]
        return out

    def task_create(self, tenant_id: str, sample_id: str, task_type: str = "", operator_id: str = "") -> dict:
        tid = _id()
        now = _ts()
        t = {"taskId": tid, "tenantId": tenant_id, "sampleId": sample_id, "taskType": task_type or "", "status": 0, "operatorId": operator_id or "", "createdAt": now, "completedAt": ""}
        self.tasks[tid] = t
        return t

    def task_get(self, tenant_id: str, task_id: str) -> Optional[dict]:
        t = self.tasks.get(task_id)
        return t if t and t.get("tenantId") == tenant_id else None

    def experiment_data_add(self, tenant_id: str, task_id: str, sample_id: str, data_value: str) -> dict:
        did = _id()
        now = _ts()
        d = {"dataId": did, "tenantId": tenant_id, "taskId": task_id, "sampleId": sample_id, "dataValue": data_value, "createdAt": now}
        self.experiment_data.append(d)
        return d

    def experiment_data_list(self, tenant_id: str, task_id: Optional[str] = None, sample_id: Optional[str] = None) -> List[dict]:
        out = [d for d in self.experiment_data if d.get("tenantId") == tenant_id]
        if task_id:
            out = [d for d in out if d.get("taskId") == task_id]
        if sample_id:
            out = [d for d in out if d.get("sampleId") == sample_id]
        return out

    def report_create(self, tenant_id: str, sample_id: str, task_id: str = "", content: str = "") -> dict:
        rid = _id()
        now = _ts()
        r = {"reportId": rid, "tenantId": tenant_id, "sampleId": sample_id, "taskId": task_id or "", "content": content or "", "status": 0, "createdAt": now, "reviewedAt": "", "reviewedBy": "", "archivedAt": ""}
        self.reports[rid] = r
        return r

    def report_review(self, tenant_id: str, report_id: str, reviewer_id: str) -> Optional[dict]:
        """报告审核：实验室合规要求审核后可归档。"""
        r = self.reports.get(report_id)
        if not r or r.get("tenantId") != tenant_id:
            return None
        now = _ts()
        r["status"] = 1
        r["reviewedAt"] = now
        r["reviewedBy"] = reviewer_id
        return r

    def report_archive(self, tenant_id: str, report_id: str) -> Optional[dict]:
        """报告归档：实验室合规要求审核后可归档。"""
        r = self.reports.get(report_id)
        if not r or r.get("tenantId") != tenant_id:
            return None
        if r.get("status") != 1:
            return None  # 需先审核
        now = _ts()
        r["status"] = 2
        r["archivedAt"] = now
        return r

    def report_list(self, tenant_id: str, sample_id: Optional[str] = None) -> List[dict]:
        out = self._by_tenant(self.reports, tenant_id)
        if sample_id:
            out = [r for r in out if r.get("sampleId") == sample_id]
        return out

    def report_get(self, tenant_id: str, report_id: str) -> Optional[dict]:
        r = self.reports.get(report_id)
        return r if r and r.get("tenantId") == tenant_id else None

    def trace_add(self, tenant_id: str, entity_type: str, entity_id: str, action: str, operator_id: str = "") -> dict:
        tid = _id()
        now = _ts()
        t = {"traceId": tid, "tenantId": tenant_id, "entityType": entity_type, "entityId": entity_id, "action": action, "operatorId": operator_id, "occurredAt": now}
        self.traces.append(t)
        return t

    def trace_list(self, tenant_id: str, entity_type: Optional[str] = None, entity_id: Optional[str] = None) -> List[dict]:
        out = [t for t in self.traces if t.get("tenantId") == tenant_id]
        if entity_type:
            out = [t for t in out if t.get("entityType") == entity_type]
        if entity_id:
            out = [t for t in out if t.get("entityId") == entity_id]
        out.sort(key=lambda x: x.get("occurredAt", ""), reverse=True)
        return out

    def audit_append(self, tenant_id: str, user_id: str, action: str, resource_type: str, resource_id: str, trace_id: str = "") -> None:
        self._audit_log.append({"tenantId": tenant_id, "userId": user_id, "action": action, "resourceType": resource_type, "resourceId": resource_id, "traceId": trace_id, "occurredAt": _ts()})

    def audit_list(self, tenant_id: str, page: int = 1, page_size: int = 50, resource_type: Optional[str] = None) -> tuple:
        out = [a for a in self._audit_log if a.get("tenantId") == tenant_id]
        if resource_type:
            out = [a for a in out if a.get("resourceType") == resource_type]
        out.sort(key=lambda x: x.get("occurredAt", ""), reverse=True)
        total = len(out)
        start = (page - 1) * page_size
        return out[start:start + page_size], total


_store: Optional[LIMSStore] = None


def get_store() -> LIMSStore:
    global _store
    if _store is None:
        _store = LIMSStore()
    return _store
