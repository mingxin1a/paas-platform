"""LIS 内存存储：检验申请、样本、检验结果、报告。多租户；检验师仅看本人负责样本；报告修改可审计。"""
from __future__ import annotations

import time
import uuid
from typing import Dict, List, Optional, Tuple

def _ts(): return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
def _id(): return str(uuid.uuid4()).replace("-", "")[:16]


class LISStore:
    # 样本状态：0=待接收 1=已接收 2=检验中 3=已完成
    # 报告状态：0=待审核 1=已审核 2=已发布
    def __init__(self) -> None:
        self.test_requests: Dict[str, dict] = {}
        self.samples: Dict[str, dict] = {}
        self.results: Dict[str, dict] = {}
        self.reports: Dict[str, dict] = {}
        self.report_audits: List[dict] = []
        self._audit_log: List[dict] = []  # 检验规范：不可篡改操作日志
        self._idem: Dict[str, str] = {}

    def idem_get(self, k: str) -> Optional[str]:
        return self._idem.get(k)

    def idem_set(self, k: str, v: str) -> None:
        self._idem[k] = v

    def _by_tenant(self, d: Dict[str, dict], tenant_id: str) -> List[dict]:
        return [v for v in d.values() if v.get("tenantId") == tenant_id]

    def test_request_list(self, tenant_id: str, patient_id: Optional[str] = None) -> List[dict]:
        out = self._by_tenant(self.test_requests, tenant_id)
        if patient_id:
            out = [r for r in out if r.get("patientId") == patient_id]
        return out

    def test_request_create(self, tenant_id: str, patient_id: str = "", visit_id: str = "", items: str = "") -> dict:
        rid = _id()
        now = _ts()
        r = {"requestId": rid, "tenantId": tenant_id, "patientId": patient_id, "visitId": visit_id, "items": items or "", "status": 1, "createdAt": now}
        self.test_requests[rid] = r
        return r

    def sample_list(self, tenant_id: str, technician_id: Optional[str] = None, request_id: Optional[str] = None) -> List[dict]:
        out = self._by_tenant(self.samples, tenant_id)
        if technician_id:
            out = [s for s in out if s.get("technicianId") == technician_id]
        if request_id:
            out = [s for s in out if s.get("requestId") == request_id]
        return out

    def sample_create(self, tenant_id: str, sample_no: str, patient_id: str = "", request_id: str = "", specimen_type: str = "", technician_id: str = "") -> dict:
        sid = _id()
        now = _ts()
        s = {"sampleId": sid, "tenantId": tenant_id, "sampleNo": sample_no, "patientId": patient_id, "requestId": request_id, "specimenType": specimen_type, "technicianId": technician_id or "", "status": 0, "createdAt": now, "updatedAt": now, "receivedAt": ""}
        self.samples[sid] = s
        return s

    def sample_receive(self, tenant_id: str, sample_id: str) -> Optional[dict]:
        """样本接收：检验规范要求记录接收时间与操作。"""
        s = self.samples.get(sample_id)
        if not s or s.get("tenantId") != tenant_id:
            return None
        now = _ts()
        s["status"] = 1
        s["receivedAt"] = now
        s["updatedAt"] = now
        return s

    def audit_append(self, tenant_id: str, user_id: str, action: str, resource_type: str, resource_id: str, trace_id: str = "") -> None:
        self._audit_log.append({
            "tenantId": tenant_id, "userId": user_id, "action": action,
            "resourceType": resource_type, "resourceId": resource_id,
            "traceId": trace_id, "occurredAt": _ts(),
        })

    def audit_list(self, tenant_id: str, page: int = 1, page_size: int = 50) -> Tuple[List[dict], int]:
        out = [a for a in self._audit_log if a.get("tenantId") == tenant_id]
        out.sort(key=lambda x: x.get("occurredAt", ""), reverse=True)
        total = len(out)
        start = (page - 1) * page_size
        return out[start : start + page_size], total

    def sample_get(self, tenant_id: str, sample_id: str) -> Optional[dict]:
        s = self.samples.get(sample_id)
        return s if s and s.get("tenantId") == tenant_id else None

    def result_list(self, tenant_id: str, sample_id: Optional[str] = None, technician_id: Optional[str] = None) -> List[dict]:
        out = self._by_tenant(self.results, tenant_id)
        if sample_id:
            out = [r for r in out if r.get("sampleId") == sample_id]
        if technician_id:
            sample_ids = {s["sampleId"] for s in self.samples.values() if s.get("tenantId") == tenant_id and s.get("technicianId") == technician_id}
            out = [r for r in out if r.get("sampleId") in sample_ids]
        return out

    def result_create(self, tenant_id: str, sample_id: str, item_code: str, value: str, unit: str = "") -> dict:
        rid = _id()
        now = _ts()
        r = {"resultId": rid, "tenantId": tenant_id, "sampleId": sample_id, "itemCode": item_code, "value": value, "unit": unit, "status": 1, "createdAt": now, "updatedAt": now}
        self.results[rid] = r
        return r

    def result_get(self, tenant_id: str, result_id: str) -> Optional[dict]:
        r = self.results.get(result_id)
        return r if r and r.get("tenantId") == tenant_id else None

    def report_create(self, tenant_id: str, sample_id: str, request_id: str = "", content: str = "") -> dict:
        rid = _id()
        now = _ts()
        r = {"reportId": rid, "tenantId": tenant_id, "sampleId": sample_id, "requestId": request_id, "content": content or "", "status": 0, "createdAt": now, "reviewedAt": "", "reviewedBy": "", "publishedAt": ""}
        self.reports[rid] = r
        return r

    def report_publish(self, tenant_id: str, report_id: str) -> Optional[dict]:
        """报告发布：检验规范要求报告审核后可发布。"""
        r = self.reports.get(report_id)
        if not r or r.get("tenantId") != tenant_id:
            return None
        if r.get("status") != 1:
            return None  # 需先审核
        now = _ts()
        r["status"] = 2
        r["publishedAt"] = now
        aid = _id()
        self.report_audits.append({"auditId": aid, "tenantId": tenant_id, "reportId": report_id, "operation": "publish", "occurredAt": now})
        return r

    def report_get(self, tenant_id: str, report_id: str) -> Optional[dict]:
        return self.reports.get(report_id) if self.reports.get(report_id, {}).get("tenantId") == tenant_id else None

    def report_list(self, tenant_id: str, sample_id: Optional[str] = None, status: Optional[int] = None) -> List[dict]:
        out = self._by_tenant(self.reports, tenant_id)
        if sample_id:
            out = [r for r in out if r.get("sampleId") == sample_id]
        if status is not None:
            out = [r for r in out if r.get("status") == status]
        return out

    def report_review(self, tenant_id: str, report_id: str, reviewer_id: str) -> Optional[dict]:
        r = self.reports.get(report_id)
        if not r or r.get("tenantId") != tenant_id:
            return None
        now = _ts()
        r["status"] = 1
        r["reviewedAt"] = now
        r["reviewedBy"] = reviewer_id
        aid = _id()
        self.report_audits.append({"auditId": aid, "tenantId": tenant_id, "reportId": report_id, "operation": "review", "operatorId": reviewer_id, "occurredAt": now})
        return r

    def report_audit_list(self, tenant_id: str, report_id: Optional[str] = None) -> List[dict]:
        out = [a for a in self.report_audits if a.get("tenantId") == tenant_id]
        if report_id:
            out = [a for a in out if a.get("reportId") == report_id]
        out.sort(key=lambda x: x.get("occurredAt", ""), reverse=True)
        return out


_store: Optional[LISStore] = None


def get_store() -> LISStore:
    global _store
    if _store is None:
        _store = LISStore()
    return _store
