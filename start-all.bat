@echo off
chcp 65001 >nul
echo ============================================================
echo   NexusAgent 多服务启动
echo ============================================================
echo.

cd /d "%~dp0"

:: 启动 Browser-Use 服务
echo [1/4] 启动 Browser-Use 服务 (端口 9242)...
start "Browser-Use" cmd /c "cd browser-use-main-debug\browser-use-main && python run.py"
timeout /t 2 >nul

:: 启动 API 测试服务
echo [2/4] 启动 API 测试服务 (端口 9243)...
start "API-Testing" cmd /c "python -m nexus_api.api_test"
timeout /t 2 >nul

:: 启动安全测试服务
echo [3/4] 启动安全测试服务 (端口 9244)...
start "Security" cmd /c "python -m nexus_api.security_api"
timeout /t 2 >nul

:: 启动主服务
echo [4/4] 启动主服务 AutoGLM (端口 8000)...
echo.
echo ============================================================
echo   所有服务已启动
echo ============================================================
echo   主界面: http://127.0.0.1:8000
echo   Browser-Use: http://127.0.0.1:9242
echo   API Testing: http://127.0.0.1:9243
echo   Security: http://127.0.0.1:9244
echo ============================================================
echo.

python unified_server.py --port 8000
