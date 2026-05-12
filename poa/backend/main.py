"""POA —— API 测试平台主入口"""
import time
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path

from .models.base import init_db
from .routers.projects     import router as projects_router
from .routers.environments import router as env_router
from .routers.runner       import router as runner_router
from .routers.importexport import router as ie_router
from .routers.extras       import router as extras_router
from .routers.auth         import router as auth_router
from .routers.backup       import router as backup_router
from .routers.monitor      import router as monitor_router, memory_handler
from .routers.environments import mock_router as mock_handler_router
from .routers.runner import ws_router as ws_handler_router

# ── 内存日志 Handler 注册 ─────────────────────────────────────
root_logger = logging.getLogger()
if not any(isinstance(h, type(memory_handler)) for h in root_logger.handlers):
    memory_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root_logger.addHandler(memory_handler)

logger = logging.getLogger("poa")

app = FastAPI(
    title="POA - API Testing Platform",
    description="集成 Postman + Apifox 优点的 API 测试平台",
    version="1.0.0",
    docs_url="/api/docs-ui",
    redoc_url="/api/redoc",
)

# ── CORS ──────────────────────────────────────────────────────
import os
_cors_origins = os.environ.get("POA_CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 请求日志中间件 ─────────────────────────────────────────────
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = round((time.time() - start) * 1000, 2)
    logger.info(
        "%s %s -> %d (%.2fms)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed,
    )
    return response


# ── 全局异常处理器 ────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    from fastapi import HTTPException as _HTTPException
    if isinstance(exc, _HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.status_code, "message": exc.detail, "data": None},
        )
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": "服务器内部错误", "data": None},
    )


# ── 路由注册 ──────────────────────────────────────────────────
app.include_router(projects_router)
app.include_router(env_router)
app.include_router(runner_router)
app.include_router(ie_router)
app.include_router(extras_router)
app.include_router(auth_router)
app.include_router(backup_router)
app.include_router(monitor_router)
app.include_router(mock_handler_router)
app.include_router(ws_handler_router)


# ── 启动时初始化数据库 ────────────────────────────────────────
@app.on_event("startup")
def startup():
    init_db()
    # 自动加载种子数据
    try:
        from .seed import seed
        seed()
    except Exception as e:
        logger.info(f"种子数据: {e}")
    logger.info("POA 启动完成，数据库已初始化")


@app.get("/health")
def health():
    return {"code": 200, "message": "ok", "data": {"version": "1.0.0"}}


# ── 前端静态文件（如果存在） ──────────────────────────────────
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str):
        # API 路由和 WebSocket 已被 router 处理，这里只处理前端路由
        index = frontend_dist / "index.html"
        return FileResponse(str(index))
