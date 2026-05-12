FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# uiautomator2 需要额外依赖
RUN pip install --no-cache-dir uiautomator2 wda hmdriver2 2>/dev/null || true
COPY . .
CMD ["python", "run.py", "--help"]
