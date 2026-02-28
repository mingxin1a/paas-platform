"""OA 内存存储：任务、审批、公告。多租户，商用级闭环基础。"""
from __future__ import annotations
import time
import uuid
from typing import Dict, List, Optional, Tuple

def _ts(): return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
def _id(): return str(uuid.uuid4()).replace("-", "")[:16]

class OAStore:
    def __init__(self) -> None:
        self.tasks: Dict[str, dict] = {}
        self.approvals: Dict[str, dict] = {}
        self.announcements: Dict[str, dict] = {}
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

    def audit_list(self, tenant_id: str, page: int = 1, page_size: int = 50, resource_type: Optional[str] = None) -> Tuple[List[dict], int]:
        out = [e for e in self._audit_log if e.get("tenantId") == tenant_id]
        if resource_type:
            out = [e for e in out if (e.get("resourceType") or "") == resource_type]
        total = len(out)
        out = sorted(out, key=lambda x: x.get("occurredAt", ""), reverse=True)
        start = (page - 1) * page_size
        return out[start : start + page_size], total

    def _by_tenant(self, tenant_id: str) -> List[dict]:
        return [v for v in self.tasks.values() if v.get("tenantId") == tenant_id]

    def task_list(self, tenant_id: str) -> List[dict]:
        return self._by_tenant(tenant_id)

    def task_create(self, tenant_id: str, title: str, assignee_id: str = "", priority: int = 0) -> dict:
        tid = _id()
        now = _ts()
        t = {
            "taskId": tid,
            "tenantId": tenant_id,
            "title": title,
            "assigneeId": assignee_id,
            "priority": priority,
            "status": 1,
            "createdAt": now,
            "updatedAt": now,
        }
        self.tasks[tid] = t
        return t

    def task_get(self, tenant_id: str, task_id: str) -> Optional[dict]:
        t = self.tasks.get(task_id)
        return t if t and t.get("tenantId") == tenant_id else None

    def task_update_status(self, tenant_id: str, task_id: str, status: int) -> Optional[dict]:
        t = self.task_get(tenant_id, task_id)
        if not t:
            return None
        t["status"] = status
        t["updatedAt"] = _ts()
        return t

    def task_batch_complete(self, tenant_id: str, task_ids: List[str]) -> tuple[int, List[str]]:
        """批量办结任务，返回成功数量与未找到的 id 列表。"""
        done, not_found = 0, []
        for tid in task_ids:
            t = self.task_get(tenant_id, tid)
            if not t:
                not_found.append(tid)
                continue
            t["status"] = 2
            t["updatedAt"] = _ts()
            done += 1
        return done, not_found

    def task_reminders(self, tenant_id: str, assignee_id: Optional[str] = None, limit: int = 50) -> dict:
        """待办提醒：未完成任务；若 assignee_id 则仅该负责人。同时返回待审批数量（pending）。"""
        items = [t for t in self.tasks.values() if t.get("tenantId") == tenant_id and t.get("status") == 1]
        if assignee_id:
            items = [t for t in items if (t.get("assigneeId") or "") == assignee_id]
        items = sorted(items, key=lambda x: x.get("updatedAt") or "")[:limit]
        pending_approvals = len([a for a in self.approvals.values() if a.get("tenantId") == tenant_id and a.get("status") == "pending"])
        return {"tasks": items, "pendingApprovals": pending_approvals}

    # ---------- 审批（数据权限：仅本人发起/待审批） ----------
    def approval_list(self, tenant_id: str, applicant_id: Optional[str] = None, status: Optional[str] = None, page: int = 1, page_size: int = 20) -> tuple[List[dict], int]:
        items = [v for v in self.approvals.values() if v.get("tenantId") == tenant_id]
        if applicant_id:
            items = [x for x in items if x.get("applicantId") == applicant_id]
        if status:
            items = [x for x in items if x.get("status") == status]
        total = len(items)
        start = (page - 1) * page_size
        return items[start:start + page_size], total

    def approval_get(self, tenant_id: str, instance_id: str) -> Optional[dict]:
        a = self.approvals.get(instance_id)
        return a if a and a.get("tenantId") == tenant_id else None

    def approval_create(self, tenant_id: str, applicant_id: str, type_code: str, form_data: dict) -> dict:
        iid = _id()
        now = _ts()
        a = {"instanceId": iid, "tenantId": tenant_id, "applicantId": applicant_id, "typeCode": type_code, "status": "draft", "formData": form_data, "sealedAt": "", "sealedBy": "", "createdAt": now, "updatedAt": now}
        self.approvals[iid] = a
        return a

    def approval_submit(self, tenant_id: str, instance_id: str, request_id: str) -> Optional[dict]:
        existing = self._idem.get(request_id)
        if existing == instance_id:
            return self.approval_get(tenant_id, instance_id)
        a = self.approval_get(tenant_id, instance_id)
        if not a or a.get("status") != "draft":
            return None
        a["status"] = "pending"
        a["updatedAt"] = _ts()
        self._idem[request_id] = instance_id
        return a

    # ---------- 公告 ----------
    def announcement_list(self, tenant_id: str, page: int = 1, page_size: int = 20) -> tuple[List[dict], int]:
        items = [v for v in self.announcements.values() if v.get("tenantId") == tenant_id]
        items.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
        total = len(items)
        start = (page - 1) * page_size
        return items[start:start + page_size], total

    def approval_seal(self, tenant_id: str, instance_id: str, user_id: str) -> Optional[dict]:
        """电子签章：记录签章时间与操作人。"""
        a = self.approval_get(tenant_id, instance_id)
        if not a:
            return None
        now = _ts()
        a["sealedAt"] = now
        a["sealedBy"] = user_id
        a["updatedAt"] = now
        return a

    def approval_complete(self, tenant_id: str, instance_id: str, approved: bool, processor_id: str = "") -> Optional[dict]:
        """审批完成：approved=True 通过，False 驳回；状态变为 approved/rejected。"""
        a = self.approval_get(tenant_id, instance_id)
        if not a or a.get("status") not in ("draft", "pending"):
            return None
        now = _ts()
        a["status"] = "approved" if approved else "rejected"
        a["processedBy"] = processor_id
        a["processedAt"] = now
        a["updatedAt"] = now
        return a

    def announcement_get(self, tenant_id: str, announcement_id: str) -> Optional[dict]:
        a = self.announcements.get(announcement_id)
        return a if a and a.get("tenantId") == tenant_id else None

    def announcement_create(self, tenant_id: str, title: str, content: str, publisher_id: str = "") -> dict:
        aid = _id()
        now = _ts()
        a = {"announcementId": aid, "tenantId": tenant_id, "title": title, "content": content, "publisherId": publisher_id, "status": 1, "createdAt": now}
        self.announcements[aid] = a
        return a

_store: Optional[OAStore] = None

def get_store() -> OAStore:
    global _store
    if _store is None:
        _store = OAStore()
    return _store
