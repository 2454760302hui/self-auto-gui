"""
NexusAgent 统一服务入口
整合 AutoGLM、Browser-Use、API测试、安全测试四大模块

启动方式:
  python unified_server.py                    # 启动所有服务
  python unified_server.py --only autoglm     # 仅启动 AutoGLM
  python unified_server.py --only browser     # 仅启动 Browser-Use
  python unified_server.py --port 8080        # 指定主服务端口
"""
import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional

# 添加项目路径
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "browser-use-main-debug" / "browser-use-main"))

from dotenv import load_dotenv
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("nexus")

# ─────────────────────────────────────────────────────────────────────────────
# 服务配置
# ─────────────────────────────────────────────────────────────────────────────

SERVICE_CONFIGS = {
    "autoglm": {
        "name": "AutoGLM GUI",
        "port": 8000,
        "description": "AI 驱动的移动设备自动化",
        "module": "AutoGLM_GUI.server",
        "app_factory": "app",
    },
    "browser": {
        "name": "Browser-Use",
        "port": 9242,
        "description": "NLP/DSL 浏览器自动化",
        "module": "run",
        "app_factory": "app",
        "path": "browser-use-main-debug/browser-use-main",
    },
    "api_test": {
        "name": "API Testing",
        "port": 9243,
        "description": "YAML 驱动接口测试",
        "module": "nexus_api.api_test",
        "app_factory": "create_app",
    },
    "security": {
        "name": "Security Scan",
        "port": 9244,
        "description": "漏洞扫描服务",
        "module": "nexus_api.security_api",
        "app_factory": "create_app",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# 主服务：聚合 API 网关
# ─────────────────────────────────────────────────────────────────────────────

def create_unified_app() -> "FastAPI":
    """创建聚合 API 网关"""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    import httpx

    app = FastAPI(
        title="NexusAgent API Gateway",
        description="AI 驱动的自动化测试与控制平台",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def root():
        """服务状态"""
        return {
            "name": "NexusAgent",
            "version": "1.0.0",
            "status": "running",
            "services": {
                "autoglm": {"url": "http://127.0.0.1:8000", "description": "移动设备自动化"},
                "browser": {"url": "http://127.0.0.1:9242", "description": "浏览器自动化"},
                "api_test": {"url": "http://127.0.0.1:9243", "description": "API 接口测试"},
                "security": {"url": "http://127.0.0.1:9244", "description": "安全扫描"},
            },
        }

    @app.get("/health")
    async def health():
        """健康检查"""
        return {"status": "ok"}

    # 代理路由 - 将请求转发到各子服务
    @app.api_route("/api/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    async def proxy_request(service: str, path: str, request):
        """代理请求到子服务"""
        if service not in SERVICE_CONFIGS:
            return JSONResponse({"error": f"Unknown service: {service}"}, status_code=404)

        config = SERVICE_CONFIGS[service]
        target_url = f"http://127.0.0.1:{config['port']}/{path}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method=request.method,
                    url=target_url,
                    content=await request.body(),
                    headers=dict(request.headers),
                    timeout=60.0,
                )
                return JSONResponse(
                    content=response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                    status_code=response.status_code,
                )
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)

    return app


# ─────────────────────────────────────────────────────────────────────────────
# 服务启动函数
# ─────────────────────────────────────────────────────────────────────────────

def run_service(config: dict, port: Optional[int] = None):
    """运行单个服务"""
    import uvicorn
    import importlib

    port = port or config["port"]

    # 添加服务路径
    if "path" in config:
        service_path = BASE_DIR / config["path"]
        if str(service_path) not in sys.path:
            sys.path.insert(0, str(service_path))

    try:
        module = importlib.import_module(config["module"])
        if config["app_factory"] == "app":
            app = getattr(module, "app")
        else:
            factory = getattr(module, config["app_factory"])
            app = factory()

        logger.info(f"✓ {config['name']} 服务启动在端口 {port}")
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
    except Exception as e:
        logger.error(f"✗ {config['name']} 启动失败: {e}")
        raise


def run_all_services(main_port: int = 8000):
    """运行所有服务（主进程模式 - 仅启动 AutoGLM）"""
    import uvicorn

    # 默认启动 AutoGLM 作为主服务（包含前端静态文件）
    # 其他服务需要单独启动或在后台运行

    logger.info("=" * 60)
    logger.info("  NexusAgent 统一服务平台")
    logger.info("=" * 60)
    logger.info(f"  主服务端口: {main_port}")
    logger.info("  可用服务:")
    for key, cfg in SERVICE_CONFIGS.items():
        port = main_port if key == "autoglm" else cfg["port"]
        logger.info(f"    • {cfg['name']} (:{port}) - {cfg['description']}")
    logger.info("=" * 60)

    run_service(SERVICE_CONFIGS["autoglm"], main_port)


def run_with_multiprocessing(main_port: int = 8000):
    """使用多进程启动所有服务"""
    import multiprocessing
    import uvicorn

    logger.info("=" * 60)
    logger.info("  NexusAgent 多进程模式启动")
    logger.info("=" * 60)

    # 每个服务独立进程，共享主端口
    def start_main():
        run_service(SERVICE_CONFIGS["autoglm"], main_port)

    def start_browser():
        run_service(SERVICE_CONFIGS["browser"])

    def start_api_test():
        try:
            module = importlib.import_module(SERVICE_CONFIGS["api_test"]["module"])
            factory = getattr(module, SERVICE_CONFIGS["api_test"]["app_factory"])
            app = factory()
            logger.info(f"✓ API Testing 服务启动在端口 {SERVICE_CONFIGS['api_test']['port']}")
            uvicorn.run(app, host="0.0.0.0", port=SERVICE_CONFIGS["api_test"]["port"], log_level="warning")
        except Exception as e:
            logger.error(f"✗ API Testing 启动失败: {e}")

    def start_security():
        try:
            module = importlib.import_module(SERVICE_CONFIGS["security"]["module"])
            factory = getattr(module, SERVICE_CONFIGS["security"]["app_factory"])
            app = factory()
            logger.info(f"✓ Security Scan 服务启动在端口 {SERVICE_CONFIGS['security']['port']}")
            uvicorn.run(app, host="0.0.0.0", port=SERVICE_CONFIGS["security"]["port"], log_level="warning")
        except Exception as e:
            logger.error(f"✗ Security Scan 启动失败: {e}")

    processes = [
        multiprocessing.Process(target=start_main, name="autoglm"),
        multiprocessing.Process(target=start_browser, name="browser", daemon=True),
        multiprocessing.Process(target=start_api_test, name="api_test", daemon=True),
        multiprocessing.Process(target=start_security, name="security", daemon=True),
    ]

    for p in processes:
        p.start()
        logger.info(f"  已启动进程: {p.name} (pid={p.pid})")

    logger.info("-" * 60)
    logger.info("  所有服务已启动:")
    logger.info(f"    • AutoGLM GUI   → http://127.0.0.1:{main_port}  (主服务/前端)")
    logger.info(f"    • Browser-Use  → http://127.0.0.1:9242  (浏览器自动化)")
    logger.info(f"    • API Testing   → http://127.0.0.1:9243  (接口测试)")
    logger.info(f"    • Security Scan → http://127.0.0.1:9244  (安全扫描)")
    logger.info("-" * 60)
    logger.info("  按 Ctrl+C 停止所有服务\n")

    try:
        for p in processes:
            p.join()
    except KeyboardInterrupt:
        logger.info("正在停止所有服务...")
        for p in processes:
            p.terminate()
        for p in processes:
            p.join(timeout=5)


# ─────────────────────────────────────────────────────────────────────────────
# CLI 入口
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="NexusAgent 统一服务入口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python unified_server.py                    # 启动主服务 (AutoGLM)
  python unified_server.py --only browser     # 仅启动 Browser-Use
  python unified_server.py --all              # 多进程启动所有服务
  python unified_server.py --port 9000        # 指定主服务端口
        """,
    )

    parser.add_argument(
        "--only",
        choices=list(SERVICE_CONFIGS.keys()),
        help="仅启动指定服务",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="多进程启动所有服务",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="主服务端口 (默认: 8000)",
    )

    args = parser.parse_args()

    if args.only:
        config = SERVICE_CONFIGS[args.only]
        port = args.port if args.only == "autoglm" else config["port"]
        run_service(config, port)
    elif args.all:
        run_with_multiprocessing(args.port)
    else:
        run_all_services(args.port)


if __name__ == "__main__":
    main()
