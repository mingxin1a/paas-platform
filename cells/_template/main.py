# 细胞入口：标准化健康检查、鉴权、统一响应与错误码（《接口设计说明书》）
from __future__ import annotations

import time
import uuid

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from config import settings
from api.middleware import request_id_ctx, tenant_id_ctx, get_request_id
from api.routes import router as items_router

app = FastAPI(
    title="Cell API (Template)",
    description="通用细胞模板，对齐《接口设计说明书》",
    version="1.0.0",
)

# 请求上下文与 X-Response-Time（3.1.3 响应头）
@app.middleware("http")
async def add_request_id_and_timing(request: Request, call_next):
    rid = request.headers.get("X-Request-ID") or request.headers.get("X-Trace-Id") or str(uuid.uuid4()).replace("-", "")[:32]
    tid = (request.headers.get("X-Tenant-Id") or "").strip() or settings.DEFAULT_TENANT_ID
    request_id_ctx.set(rid)
    tenant_id_ctx.set(tid)
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Response-Time"] = str(int((time.perf_counter() - start) * 1000))
    return response

# 示例资源路由（复制模板后改为 /orders、/work-orders 等）
app.include_router(items_router, prefix="/items", tags=["items"])


# 健康检查：符合网关注册与健康巡检规范
@app.get("/health")
def health():
    return {"status": "up", "cell": "template"}


# 统一错误响应格式：code, message, details, requestId
@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, exc: HTTPException):
    body = exc.detail if isinstance(exc.detail, dict) else {"code": "ERROR", "message": str(exc.detail), "details": "", "requestId": get_request_id()}
    return JSONResponse(status_code=exc.status_code, content=body)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=False)
