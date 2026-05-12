#!/bin/bash
# NexusAgent 统一启动脚本

echo "============================================================"
echo "  NexusAgent 统一启动脚本"
echo "============================================================"
echo

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到 Python，请先安装 Python 3.11+"
    exit 1
fi

# 进入项目目录
cd "$(dirname "$0")"

# 检查依赖
echo "[1/3] 检查依赖..."
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "[安装] 正在安装依赖..."
    pip install fastapi uvicorn httpx pydantic pyyaml python-dotenv loguru
fi

# 启动服务
echo
echo "[2/3] 启动服务..."
echo "  - AutoGLM GUI    : http://127.0.0.1:8000"
echo "  - Browser-Use    : http://127.0.0.1:9242 (需单独启动)"
echo "  - API Testing    : http://127.0.0.1:9243 (需单独启动)"
echo "  - Security Scan  : http://127.0.0.1:9244 (需单独启动)"
echo
echo "[3/3] 启动主服务 (AutoGLM)..."
echo

python3 unified_server.py --port 8000
