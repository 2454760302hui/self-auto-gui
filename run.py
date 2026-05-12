# -*- coding: utf-8 -*-
"""
NexusAgent 统一启动脚本
一键启动全部 4 个后端服务 + 展示完整功能说明

用法:
  python run.py              # 启动全部服务
  python run.py --frontend   # 仅启动前端开发服务器
  python run.py --services   # 仅启动后端服务（不打开浏览器）
  python run.py --port 9000  # 指定主端口
  python run.py --no-browser # 不自动打开浏览器
"""
from __future__ import annotations

import argparse
import multiprocessing
import os
import sys
import threading
import webbrowser
from pathlib import Path

# ── 项目根目录 ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT))

# ── 修复 Windows PowerShell UTF-8 输出 ────────────────────────────────────
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# ── 颜色输出 ────────────────────────────────────────────────────────────────
C_RESET  = "\033[0m"
C_RED    = "\033[91m"
C_GREEN  = "\033[92m"
C_YELLOW = "\033[93m"
C_CYAN   = "\033[96m"
C_BOLD   = "\033[1m"


def c(text: str, color: str) -> str:
    return f"{color}{text}{C_RESET}"


# ─────────────────────────────────────────────────────────────────────────────
# 功能清单
# ─────────────────────────────────────────────────────────────────────────────

SERVICES = [
    {
        "name": "AutoGLM",
        "port": 8000,
        "color": C_GREEN,
        "badge": "[CORE]",
        "description": "AI 驱动的移动设备自动化控制平台",
        "url": "http://127.0.0.1:8000",
        "features": [
            ("AI 对话控制",        "LLM 驱动的 Agent，自然语言指令驱动 Android/HarmonyOS 设备"),
            ("多 Agent 引擎",      "支持 GLM / Gemini / Mai / Midscene / DroidRun / Layered 等多种 Agent"),
            ("设备连接管理",       "ADB USB/WiFi / mDNS / QR 二维码 / 远程设备代理 / 设备分组"),
            ("设备控制 API",      "tap / swipe / scroll / launch / text / clipboard / 截图 / UI Dump"),
            ("截图 & GIF",        "实时设备截图，支持多帧合成动画 GIF"),
            ("应用管理",          "列出设备已安装应用，支持按类型筛选系统/第三方应用"),
            ("通知监控",          "实时监听设备通知栏消息"),
            ("健康监控",          "设备电量、存储、内存等健康指标"),
            ("任务管理",          "AI 任务下发、状态追踪、中止、历史记录"),
            ("批处理执行",        "向多台设备同时下发同一 AI 指令"),
            ("定时任务",          "CRON 表达式定时触发 AI 任务"),
            ("工作流编排",        "创建、编辑、删除 AI 工作流模板"),
            ("任务模板",          "预设任务模板，批量执行"),
            ("模型配置",         "在线配置 LLM Base URL / API Key / 模型，支持连接测试"),
            ("SSE 流式响应",      "实时流式输出 AI 执行过程"),
            ("MCP 协议",         "Model Context Protocol 支持，扩展 AI 工具集"),
            ("终端命令",          "直接在设备上执行 ADB Shell 命令"),
            ("视觉理解模式",      "支持视觉多模态 AI 模型，实时分析屏幕内容"),
        ],
    },
    {
        "name": "Browser-Use",
        "port": 9242,
        "color": C_CYAN,
        "badge": "[WEB]",
        "description": "NLP/DSL 驱动的浏览器自动化引擎",
        "url": "http://127.0.0.1:9242",
        "features": [
            ("NLP 自然语言模式",  "用自然语言描述任务，AI 自动解析并执行"),
            ("DSL 脚本模式",      "结构化 DSL 指令，30+ 种操作覆盖所有浏览器场景"),
            ("LLM 直接模式",     "AI 自主决策每一步操作，适合复杂开放任务"),
            ("导航控制",         "打开 / 返回 / 前进 / 刷新 / 多标签页管理"),
            ("元素交互",         "点击 / 双击 / 右键 / 悬停 / 拖拽"),
            ("表单自动化",       "输入 / 清空 / 勾选 / 选择 / 单选 / 多选 / 开关"),
            ("键盘操作",         "按键 / 输入文字 / Ctrl/Cmd 组合键"),
            ("滚动操作",         "滚动上/下/底部/顶部，滚动到指定元素"),
            ("iframe 操作",      "进入 iframe / iframe 输入/点击 / 退出 iframe"),
            ("弹窗处理",         "自动处理 Alert / Confirm / Prompt 等 JS 弹窗"),
            ("文件上传",         "自动填写文件路径并触发上传"),
            ("断言验证",         "断言元素可见 / 文本包含 / URL / 标题"),
            ("数据提取",         "获取元素文本 / 属性 / 页面标题 / 当前 URL"),
            ("JS 执行",          "在页面上下文中执行任意 JavaScript 代码"),
            ("录制 & 回放",     "记录操作序列并生成 GIF 动画回放"),
            ("任务历史",         "查看历史任务记录，支持重新加载"),
            ("导出 pytest",      "DSL 导出为 pytest 测试用例代码"),
        ],
    },
    {
        "name": "API Testing",
        "port": 9243,
        "color": C_YELLOW,
        "badge": "[API]",
        "description": "YAML 驱动的零代码接口测试平台",
        "url": None,
        "features": [
            ("YAML 测试模板",    "用 YAML 定义测试用例，无需编写代码"),
            ("多环境切换",        "支持阿里云 / 腾讯云 / 新加坡 / 美国等多套环境"),
            ("全 HTTP 方法",      "GET / POST / PUT / DELETE / PATCH"),
            ("JSON/表单数据",   "支持 JSON Body 和 Form 提交"),
            ("自定义请求头",     "自由设置 Authorization / Content-Type 等 Header"),
            ("变量提取",          "从响应中用 JSONPath 提取变量，供后续步骤引用"),
            ("断言验证",         "status_code / body 内容 / JSONPath 字段 / 响应时间"),
            ("连续请求",         "变量提取后自动注入到后续请求中"),
            ("执行计时",         "每个请求独立计时，统计总耗时"),
            ("实时日志",         "测试过程日志实时输出"),
            ("语法参考",         "内置 YAML 语法参考文档"),
        ],
    },
    {
        "name": "Security Scan",
        "port": 9244,
        "color": C_RED,
        "badge": "[SEC]",
        "description": "Xray + Rad 漏洞扫描引擎，自动检测 Web 安全漏洞",
        "url": None,
        "features": [
            ("被动扫描模式",      "无需发送大量探测请求，监听流量被动发现漏洞"),
            ("SQL 注入检测",     "自动检测 SQL 注入漏洞 (SQLi)"),
            ("XSS 跨站脚本",    "检测反射型/存储型 XSS 漏洞"),
            ("命令注入检测",      "检测 OS Command Injection 漏洞"),
            ("XXE 漏洞检测",   "XML 外部实体注入检测"),
            ("多种扫描策略",      "快速扫描(2-5min) / 全面扫描(10-30min) / 专项扫描"),
            ("进度实时跟踪",     "扫描过程百分比进度实时显示"),
            ("漏洞分级展示",      "严重/高危/中危/低危/信息五级分类"),
            ("Payload 展示",   "漏洞详情包含实际测试 Payload，方便复现"),
            ("扫描历史管理",     "记录每次扫描任务，支持随时查看"),
            ("报告导出",         "JSON / HTML 双格式导出扫描报告"),
            ("目标 URL 管理",   "自定义扫描目标，支持 https:// 站点"),
        ],
    },
]

FEATURE_SUMMARY = """
+-----------------------------------------------------------------------+
|                     NextAgent 功能总览                               |
+----------+----------+-----------------------------------------------+
|  模块     |  端口    |  核心能力                                      |
+----------+----------+-----------------------------------------------+
| AutoGLM  |  8000    | AI 对话 / 设备控制 / 批处理 / 定时任务        |
| Browser   |  9242    | 浏览器自动化 / NLP+DSL / 30+ 指令             |
| API Test |  9243    | YAML 接口测试 / 多环境 / 变量提取               |
| Security  |  9244    | Xray+Rad 安全扫描 / SQL/XSS 检测              |
+----------+----------+-----------------------------------------------+
"""


# ─────────────────────────────────────────────────────────────────────────────
# 依赖检查
# ─────────────────────────────────────────────────────────────────────────────

REQUIRED_PACKAGES = [
    ("fastapi",   "fastapi"),
    ("uvicorn",   "uvicorn[standard]"),
    ("httpx",     "httpx"),
    ("pydantic",  "pydantic>=2"),
    ("yaml",      "pyyaml"),
    ("socketio",   "python-socketio[asyncio-client]"),
    ("openai",    "openai>=1.0"),
]


def check_dependencies() -> list[str]:
    missing = []
    for pkg_name, install_cmd in REQUIRED_PACKAGES:
        try:
            __import__(pkg_name)
        except ImportError:
            missing.append(install_cmd)
    return missing


# ─────────────────────────────────────────────────────────────────────────────
# 服务启动函数
# ─────────────────────────────────────────────────────────────────────────────

def _run_autoglm(port: int, *, open_browser_flag: bool, log_level: str) -> None:
    os.environ["AUTOGLM_LOG_LEVEL"] = log_level
    os.environ["AUTOGLM_NO_LOG_FILE"] = "1"

    from AutoGLM_GUI import server
    from AutoGLM_GUI.config_manager import config_manager
    from dotenv import load_dotenv

    load_dotenv()
    config_manager.load_env_config()
    config_manager.load_file_config()
    config_manager.sync_to_env()

    import uvicorn
    if open_browser_flag:
        threading.Timer(1.5, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()

    uvicorn.run(server.app, host="127.0.0.1", port=port, log_level="warning")


def _run_browser(port: int) -> None:
    for _k in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
        os.environ.pop(_k, None)

    sys.path.insert(0, str(ROOT / "browser-use-main-debug" / "browser-use-main"))
    from dotenv import load_dotenv
    load_dotenv()

    import uvicorn
    from run import app as browser_app
    uvicorn.run(browser_app, host="127.0.0.1", port=port, log_level="warning")


def _run_api_test(port: int) -> None:
    from nexus_api.api_test import create_app
    import uvicorn
    uvicorn.run(create_app(), host="127.0.0.1", port=port, log_level="warning")


def _run_security(port: int) -> None:
    from nexus_api.security_api import create_app
    import uvicorn
    uvicorn.run(create_app(), host="127.0.0.1", port=port, log_level="warning")


# ─────────────────────────────────────────────────────────────────────────────
# 打印 Banner
# ─────────────────────────────────────────────────────────────────────────────

def print_banner(services_up: list[str]) -> None:
    print()
    print(c("  +========================================================+", C_BOLD))
    print(c("  |      NextAgent - AI 驱动的自动化平台                  |", C_BOLD))
    print(c("  +========================================================+", C_BOLD))
    print()

    for svc in SERVICES:
        badge  = svc["badge"]
        port   = svc["port"]
        color  = svc["color"]
        name   = svc["name"]
        desc   = svc["description"]
        url    = svc["url"] or f"http://127.0.0.1:{port}"

        icon = c("[OK]", C_GREEN) if name in services_up else c("[..]", C_YELLOW)
        status = c("已启动", C_GREEN) if name in services_up else c("启动中...", C_YELLOW)

        print(f"  {icon} {c(badge, color)}  {c(name, C_BOLD)}  (:{port})  {desc}")
        print(f"         {status}  ->  {url}")

        if name in services_up:
            for feat_name, feat_desc in svc["features"]:
                print(f"         {c('+--', color)} {c(feat_name, C_BOLD)}  {feat_desc}")
        print()

    print(c(FEATURE_SUMMARY, C_RESET))
    print(c("  Ctrl+C  ->  停止全部服务", C_YELLOW))
    print()


# ─────────────────────────────────────────────────────────────────────────────
# 主入口
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="NextAgent 统一启动脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--port",        type=int, default=8000, help="主服务端口 (默认 8000)")
    parser.add_argument("--no-browser",  action="store_true", help="启动后不自动打开浏览器")
    parser.add_argument("--log-level",    default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--frontend",    action="store_true", help="仅启动前端开发服务器")
    parser.add_argument("--services",    action="store_true", help="仅启动后端服务，不打开浏览器")
    parser.add_argument("--check-deps", action="store_true", help="仅检查依赖，不启动服务")
    args = parser.parse_args()

    # ── 依赖检查 ──────────────────────────────────────────────────────────────
    print(c("\n[1/3] 检查依赖...", C_YELLOW))
    missing = check_dependencies()
    if missing:
        print(c(f"\n  [FAIL] 缺少以下依赖包，请先安装:\n", C_RED))
        for pkg in missing:
            print(f"    pip install {c(pkg, C_CYAN)}")
        print()
        sys.exit(1)
    print(c("  [OK] 所有依赖已就绪\n", C_GREEN))

    if args.check_deps:
        print(c("  依赖检查通过，退出。", C_GREEN))
        return

    # ── 前端单独模式 ─────────────────────────────────────────────────────────
    if args.frontend:
        print(c("[2/3] 启动前端开发服务器...\n", C_YELLOW))
        os.chdir(ROOT / "frontend")
        import subprocess
        subprocess.run(["pnpm", "dev"], check=True)
        return

    # ── 多进程启动全部后端服务 ───────────────────────────────────────────────
    print(c("[2/3] 启动后端服务...\n", C_YELLOW))

    try:
        multiprocessing.set_start_method("spawn", force=True)
    except RuntimeError:
        pass

    processes: list[multiprocessing.Process] = []

    p_main = multiprocessing.Process(
        target=_run_autoglm,
        args=(args.port,),
        kwargs={
            "open_browser_flag": not args.no_browser and not args.services,
            "log_level": args.log_level,
        },
        name="AutoGLM",
    )
    processes.append(p_main)

    p_browser = multiprocessing.Process(
        target=_run_browser, args=(9242,), name="Browser-Use", daemon=True,
    )
    processes.append(p_browser)

    p_api = multiprocessing.Process(
        target=_run_api_test, args=(9243,), name="API-Testing", daemon=True,
    )
    processes.append(p_api)

    p_sec = multiprocessing.Process(
        target=_run_security, args=(9244,), name="Security-Scan", daemon=True,
    )
    processes.append(p_sec)

    for p in processes:
        p.start()
        print(c(f"  [OK] {p.name} 进程已启动 (pid={p.pid})", C_GREEN))

    print()

    # ── 等待主服务就绪后打印 Banner ──────────────────────────────────────────
    def _wait_and_show() -> None:
        import time, urllib.request
        for _ in range(60):
            time.sleep(0.5)
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{args.port}/api/health", timeout=1)
                break
            except Exception:
                continue
        print_banner(["AutoGLM", "Browser-Use", "API Testing", "Security Scan"])

    threading.Thread(target=_wait_and_show, daemon=True).start()

    # ── 等待所有进程 ────────────────────────────────────────────────────────
    print(c("[3/3] 等待服务就绪...\n", C_YELLOW))
    print(c("  提示: 如需查看详细日志，可加 --log-level DEBUG\n", C_RESET))

    try:
        for p in processes:
            p.join()
    except KeyboardInterrupt:
        print(c("\n\n  正在停止所有服务...", C_YELLOW))
        for p in processes:
            if p.is_alive():
                p.terminate()
        for p in processes:
            p.join(timeout=3)
        print(c("  已全部停止。再见！\n", C_GREEN))


if __name__ == "__main__":
    main()
