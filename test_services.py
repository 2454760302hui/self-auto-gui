"""
NexusAgent 服务联调测试脚本
测试各模块 API 是否正常工作
"""
import subprocess
import sys
import time
from pathlib import Path

# 颜色输出
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def log(msg, color=BLUE):
    print(f"{color}{msg}{RESET}")

def test_imports():
    """测试模块导入"""
    log("\n[1/4] 测试模块导入...", YELLOW)
    
    errors = []
    
    # 测试 AutoGLM
    try:
        from AutoGLM_GUI.server import app as autoglm_app
        log("  ✓ AutoGLM_GUI 模块导入成功", GREEN)
    except Exception as e:
        errors.append(f"AutoGLM_GUI: {e}")
        log(f"  ✗ AutoGLM_GUI 导入失败: {e}", RED)
    
    # 测试 Browser-Use
    try:
        sys.path.insert(0, str(Path(__file__).parent / "browser-use-main-debug" / "browser-use-main"))
        from run import app as browser_app
        log("  ✓ Browser-Use 模块导入成功", GREEN)
    except Exception as e:
        errors.append(f"Browser-Use: {e}")
        log(f"  ✗ Browser-Use 导入失败: {e}", RED)
    
    # 测试 API Test
    try:
        from nexus_api.api_test import create_app as create_api_test_app
        app = create_api_test_app()
        log("  ✓ API Test 模块导入成功", GREEN)
    except Exception as e:
        errors.append(f"API Test: {e}")
        log(f"  ✗ API Test 导入失败: {e}", RED)
    
    # 测试 Security
    try:
        from nexus_api.security_api import create_app as create_security_app
        app = create_security_app()
        log("  ✓ Security 模块导入成功", GREEN)
    except Exception as e:
        errors.append(f"Security: {e}")
        log(f"  ✗ Security 导入失败: {e}", RED)
    
    return len(errors) == 0, errors


def test_static_files():
    """测试静态文件"""
    log("\n[2/4] 测试静态文件...", YELLOW)
    
    static_dir = Path(__file__).parent / "AutoGLM_GUI" / "static"
    
    if not static_dir.exists():
        log(f"  ✗ 静态目录不存在: {static_dir}", RED)
        return False, ["静态目录不存在"]
    
    index_html = static_dir / "index.html"
    assets_dir = static_dir / "assets"
    
    errors = []
    
    if index_html.exists():
        log(f"  ✓ index.html 存在", GREEN)
    else:
        errors.append("index.html 不存在")
        log(f"  ✗ index.html 不存在", RED)
    
    if assets_dir.exists() and list(assets_dir.glob("*.js")):
        log(f"  ✓ assets 目录存在且包含 JS 文件", GREEN)
    else:
        errors.append("assets 目录不完整")
        log(f"  ✗ assets 目录不完整", RED)
    
    return len(errors) == 0, errors


def test_dependencies():
    """测试依赖"""
    log("\n[3/4] 测试依赖...", YELLOW)
    
    required = [
        "fastapi",
        "uvicorn",
        "httpx",
        "pydantic",
        "yaml",
    ]
    
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
            log(f"  ✓ {pkg}", GREEN)
        except ImportError:
            missing.append(pkg)
            log(f"  ✗ {pkg} 未安装", RED)
    
    return len(missing) == 0, missing


def test_config_files():
    """测试配置文件"""
    log("\n[4/4] 测试配置文件...", YELLOW)
    
    base_dir = Path(__file__).parent
    configs = [
        "pyproject.toml",
        "unified_server.py",
        "start.bat",
        "start.sh",
    ]
    
    missing = []
    for cfg in configs:
        path = base_dir / cfg
        if path.exists():
            log(f"  ✓ {cfg}", GREEN)
        else:
            missing.append(cfg)
            log(f"  ✗ {cfg} 不存在", RED)
    
    return len(missing) == 0, missing


def main():
    log("=" * 60, BLUE)
    log("  NexusAgent 服务联调测试", BLUE)
    log("=" * 60, BLUE)
    
    all_passed = True
    
    # 运行所有测试
    passed, errors = test_imports()
    if not passed:
        all_passed = False
    
    passed, errors = test_static_files()
    if not passed:
        all_passed = False
    
    passed, errors = test_dependencies()
    if not passed:
        all_passed = False
    
    passed, errors = test_config_files()
    if not passed:
        all_passed = False
    
    # 总结
    log("\n" + "=" * 60, BLUE)
    if all_passed:
        log("  ✓ 所有测试通过！", GREEN)
        log("\n启动方式:", YELLOW)
        log("  1. 启动主服务: python unified_server.py")
        log("  2. 启动所有服务: start-all.bat (Windows)")
        log("  3. 访问: http://127.0.0.1:8000")
    else:
        log("  ✗ 部分测试失败，请检查上述错误", RED)
    log("=" * 60, BLUE)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
