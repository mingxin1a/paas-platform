"""
CRM 细胞 FastAPI 应用 - 《接口设计说明书_V2.0》合规。
客户管理、联系人管理、商机管理、跟进记录；完全独立，不依赖 platform_core。
"""
from __future__ import annotations

import time
import uuid

from fastapi import Depends, FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from . import config
from .dependencies import request_id_ctx, tenant_id_ctx, get_request_id, require_auth
from .routers import customers, contacts, opportunities, follow_ups, contracts, payments

app = FastAPI(
    title="CRM Cell API",
    description="客户关系管理细胞，经 PaaS 网关暴露；遵循《接口设计说明书》",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(customers.router, prefix="/customers", tags=["customers"])
app.include_router(contacts.router, prefix="/contacts", tags=["contacts"])
app.include_router(opportunities.router, prefix="/opportunities", tags=["opportunities"])
app.include_router(follow_ups.router, prefix="/follow-ups", tags=["follow-ups"])
app.include_router(contracts.router, prefix="/contracts", tags=["contracts"])
app.include_router(payments.router, prefix="/payments", tags=["payments"])


@app.middleware("http")
async def add_request_id_and_timing(request: Request, call_next):
    rid = request.headers.get("X-Request-ID") or request.headers.get("X-Trace-Id") or str(uuid.uuid4()).replace("-", "")[:32]
    tid = (request.headers.get("X-Tenant-Id") or "").strip() or config.DEFAULT_TENANT_ID
    request_id_ctx.set(rid)
    tenant_id_ctx.set(tid)
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    response.headers["X-Response-Time"] = str(elapsed_ms)
    return response


@app.get("/health")
def health():
    """健康检查，符合网关自动注册与健康巡检规范。"""
    return {"status": "up", "cell": "crm"}


@app.get("/metrics")
def metrics():
    """CRM 专属监控指标：客户新增量、商机转化率等，供 PaaS 监控采集。"""
    from . import database as db
    tenant_id = tenant_id_ctx.get()
    funnel = db.opportunity_funnel(tenant_id)
    total_opp = sum(x["count"] for x in funnel)
    win_opp = sum(x["count"] for x in funnel if x.get("status") == 2)
    # 客户总数（用于计算新增量需配合时序存储，此处仅提供当日/总量示意）
    conn = db.get_conn()
    customer_count = conn.execute("SELECT COUNT(*) FROM customers WHERE tenant_id = ?", (tenant_id,)).fetchone()[0]
    return {
        "cell": "crm",
        "metrics": {
            "customer_total": customer_count,
            "opportunity_total": total_opp,
            "opportunity_win_count": win_opp,
            "conversion_rate_pct": round(100 * win_opp / total_opp, 2) if total_opp else 0,
            "funnel_by_stage": funnel,
        },
    }


@app.get("/reports/funnel")
def report_funnel(_auth=Depends(require_auth)):
    """销售漏斗报表：按商机阶段/状态汇总。"""
    from . import database as db
    tenant_id = tenant_id_ctx.get()
    return {"data": db.opportunity_funnel(tenant_id)}


@app.get("/reports/sales-forecast")
def sales_forecast(_auth=Depends(require_auth)):
    """销售预测：按阶段加权金额汇总，商用验收 CRM-01。"""
    from . import database as db
    tenant_id = tenant_id_ctx.get()
    funnel = db.opportunity_funnel(tenant_id)
    by_stage = [{"stage": x.get("stage"), "count": x.get("count", 0), "weightedCents": x.get("totalAmountCents", 0) or 0} for x in funnel]
    total_weighted_cents = sum(x["weightedCents"] for x in by_stage)
    return {"byStage": by_stage, "totalWeightedCents": total_weighted_cents}


@app.get("/audit-logs")
def audit_logs(
    page: int = 1,
    pageSize: int = 50,
    resourceType: str | None = None,
    _auth=Depends(require_auth),
):
    """操作审计日志：分页查询，可按 resourceType 筛选（如 customer、opportunity）。"""
    from . import database as db
    tenant_id = tenant_id_ctx.get()
    data, total = db.audit_list(tenant_id, page=page, page_size=min(pageSize, 200), resource_type=resourceType)
    return {"data": data, "total": total, "page": page, "pageSize": pageSize}


@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, exc: HTTPException):
    """统一错误响应格式：code, message, details, requestId。"""
    body = exc.detail if isinstance(exc.detail, dict) else {"code": "ERROR", "message": str(exc.detail), "details": "", "requestId": get_request_id()}
    return JSONResponse(status_code=exc.status_code, content=body)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=config.PORT, reload=False)
