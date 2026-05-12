@echo off
chcp 65001 >nul
echo ============================================================
echo   NexusAgent 统一启动脚本
echo ============================================================
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.11+
    pause
    exit /b 1
)

:: 检查依赖
echo [1/3] 检查依赖...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo [安装] 正在安装依赖...
    pip install fastapi uvicorn httpx pydantic pyyaml python-dotenv loguru
)

:: 进入项目目录
cd /d "%~dp0"

:: 启动服务
echo.
echo [2/3] 启动服务...
echo   - AutoGLM GUI    : http://127.0.0.1:8000
echo   - Browser-Use    : http://127.0.0.1:9242 (需单独启动)
echo   - API Testing    : http://127.0.0.1:9243 (需单独启动)
echo   - Security Scan  : http://127.0.0.1:9244 (需单独启动)
echo.
echo [3/3] 启动主服务 (AutoGLM)...
echo.

python unified_server.py --port 8000

pause
