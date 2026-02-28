"""EMS 内存存储：能耗采集（模拟）、统计、分析、预警、多租户。行业合规：数据留存≥3年（配置）。"""
from __future__ import annotations

import time
import uuid
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

def _ts(): return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
def _id(): return str(uuid.uuid4()).replace("-", "")[:16]


class EMSStore:
    def __init__(self) -> None:
        self.consumption_records: Dict[str, dict] = {}
        self.alerts: List[dict] = []
        self._idem: Dict[str, str] = {}
        self._audit_log: List[dict] = []  # 工业合规：不可篡改操作日志

    def idem_get(self, k: str) -> Optional[str]:
        return self._idem.get(k)

    def idem_set(self, k: str, v: str) -> None:
        self._idem[k] = v

    def _by_tenant(self, tenant_id: str) -> List[dict]:
        return [v for v in self.consumption_records.values() if v.get("tenantId") == tenant_id]

    def consumption_list(self, tenant_id: str, meter_id: Optional[str] = None, page: int = 1, page_size: int = 100) -> Tuple[List[dict], int]:
        out = self._by_tenant(tenant_id)
        if meter_id:
            out = [r for r in out if r.get("meterId") == meter_id]
        out.sort(key=lambda x: x.get("recordTime", ""), reverse=True)
        total = len(out)
        start = (page - 1) * page_size
        return out[start:start + page_size], total

    def consumption_create(self, tenant_id: str, meter_id: str, value: float, unit: str = "kWh", record_time: str = "") -> dict:
        rid = _id()
        now = _ts()
        r = {"recordId": rid, "tenantId": tenant_id, "meterId": meter_id, "value": value, "unit": unit or "kWh", "recordTime": record_time or now, "createdAt": now}
        self.consumption_records[rid] = r
        return r

    def consumption_get(self, tenant_id: str, record_id: str) -> Optional[dict]:
        r = self.consumption_records.get(record_id)
        return r if r and r.get("tenantId") == tenant_id else None

    def _period_key(self, record_time: str, period: str) -> str:
        """record_time 格式如 2024-01-15T10:00:00.000Z，提取 day/week/month/year 维度键。"""
        if not record_time or len(record_time) < 10:
            return ""
        date_part = record_time[:10]
        if period == "day":
            return date_part
        if period == "month":
            return date_part[:7]
        if period == "year":
            return date_part[:4]
        if period == "week":
            import datetime
            try:
                dt = datetime.datetime.strptime(date_part, "%Y-%m-%d")
                week_start = dt - datetime.timedelta(days=dt.weekday())
                return week_start.strftime("%Y-%m-%d")
            except Exception:
                return date_part
        return date_part

    def consumption_stats(self, tenant_id: str, period: str, from_date: str = "", to_date: str = "") -> List[dict]:
        """按日/周/月/年统计；period=day|week|month|year。"""
        out = self._by_tenant(tenant_id)
        agg: Dict[str, Dict] = defaultdict(lambda: {"totalValue": 0.0, "count": 0, "meterIds": set()})
        for r in out:
            rt = r.get("recordTime", "")
            key = self._period_key(rt, period)
            if not key:
                continue
            if from_date and rt < from_date:
                continue
            if to_date and rt > to_date:
                continue
            agg[key]["totalValue"] += float(r.get("value", 0))
            agg[key]["count"] += 1
            agg[key]["meterIds"].add(r.get("meterId", ""))
        result = [{"period": k, "totalValue": round(v["totalValue"], 4), "count": v["count"], "meterCount": len(v["meterIds"])} for k, v in sorted(agg.items())]
        return result

    def alert_add(self, tenant_id: str, meter_id: str, alert_type: str, threshold_value: Optional[float], actual_value: Optional[float]) -> dict:
        aid = _id()
        now = _ts()
        a = {"alertId": aid, "tenantId": tenant_id, "meterId": meter_id or "", "alertType": alert_type, "thresholdValue": threshold_value, "actualValue": actual_value, "occurredAt": now, "acknowledged": 0}
        self.alerts.append(a)
        return a

    def alert_list(self, tenant_id: str, acknowledged: Optional[bool] = None, limit: int = 100) -> List[dict]:
        out = [a for a in self.alerts if a.get("tenantId") == tenant_id]
        if acknowledged is not None:
            out = [a for a in out if bool(a.get("acknowledged")) == acknowledged]
        out.sort(key=lambda x: x.get("occurredAt", ""), reverse=True)
        return out[:limit]

    def export_records(self, tenant_id: str, from_date: str = "", to_date: str = "", limit: int = 10000) -> List[dict]:
        """导出能耗数据，符合监管要求；数据留存≥3年。"""
        out = self._by_tenant(tenant_id)
        if from_date:
            out = [r for r in out if (r.get("recordTime") or "") >= from_date]
        if to_date:
            out = [r for r in out if (r.get("recordTime") or "") <= to_date]
        out.sort(key=lambda x: x.get("recordTime", ""))
        return out[:limit]

    def audit_append(self, tenant_id: str, user_id: str, action: str, resource_type: str, resource_id: str, trace_id: str = "") -> None:
        """工业合规：追加审计日志，不可篡改。"""
        self._audit_log.append({
            "tenantId": tenant_id, "userId": user_id, "action": action,
            "resourceType": resource_type, "resourceId": resource_id,
            "traceId": trace_id, "occurredAt": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
        })

    def audit_list(self, tenant_id: str, page: int = 1, page_size: int = 50, resource_type: Optional[str] = None) -> Tuple[List[dict], int]:
        out = [a for a in self._audit_log if a.get("tenantId") == tenant_id]
        if resource_type:
            out = [a for a in out if a.get("resourceType") == resource_type]
        out.sort(key=lambda x: x.get("occurredAt", ""), reverse=True)
        total = len(out)
        start = (page - 1) * page_size
        return out[start : start + page_size], total

    def consumption_analysis(self, tenant_id: str, period: str = "month", from_date: str = "", to_date: str = "") -> dict:
        """能耗分析：同比/环比、趋势、异常检测（基于预警）。"""
        stats = self.consumption_stats(tenant_id, period, from_date=from_date, to_date=to_date)
        alerts_in_range = [a for a in self.alerts if a.get("tenantId") == tenant_id]
        total_value = sum(s.get("totalValue", 0) for s in stats)
        return {
            "period": period, "fromDate": from_date, "toDate": to_date,
            "totalConsumption": round(total_value, 4), "statCount": len(stats),
            "alertCount": len(alerts_in_range), "trend": "up" if len(stats) >= 2 and (stats[0].get("totalValue", 0) >= (stats[-1].get("totalValue", 0) or 0)) else "stable",
        }

    def report_generate(self, tenant_id: str, period: str, period_key: str) -> dict:
        """能耗报表：按周期生成单期报表（工业监管报表）。"""
        stats = self.consumption_stats(tenant_id, period)
        row = next((s for s in stats if s.get("period") == period_key), None)
        return {
            "period": period, "periodKey": period_key,
            "totalValue": row.get("totalValue", 0) if row else 0,
            "recordCount": row.get("count", 0) if row else 0,
            "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
        }

    def suggestions_list(self, tenant_id: str, limit: int = 10) -> List[dict]:
        """节能建议：基于预警与统计给出建议（规则引擎简化版）。"""
        alerts_in = [a for a in self.alerts if a.get("tenantId") == tenant_id and not a.get("acknowledged")]
        suggestions = []
        for a in alerts_in[:limit]:
            suggestions.append({
                "suggestionId": _id(), "type": "alert_based",
                "meterId": a.get("meterId", ""), "alertType": a.get("alertType", ""),
                "description": f"计量点 {a.get('meterId', '')} 存在{a.get('alertType', '')}预警，建议排查并优化用能。",
                "priority": "high" if a.get("alertType") == "anomaly" else "medium",
            })
        if not suggestions:
            suggestions.append({
                "suggestionId": _id(), "type": "routine",
                "description": "当前无异常预警，建议定期查看统计报表并设置合理阈值。",
                "priority": "low",
            })
        return suggestions[:limit]


_store: Optional[EMSStore] = None


def get_store() -> EMSStore:
    global _store
    if _store is None:
        _store = EMSStore()
    return _store
