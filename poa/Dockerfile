FROM python:3.12-slim
WORKDIR /app

# Backend
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Frontend (pre-built)
COPY frontend/dist/ ./frontend/dist/

# Env defaults
ENV POA_SECRET=change-me-in-production
ENV POA_CORS_ORIGINS=http://localhost:3000,http://localhost:5173

COPY backend/ ./backend/

EXPOSE 9997
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "9997"]
