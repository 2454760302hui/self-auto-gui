"""系统监控模块"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime, timedelta
import os
import logging

from ..models.base import (
    get_db, DB_PATH,
    Workspace, Project, Api, TestRun, RequestHistory, Collection,
)
from .auth import get_current_user

router = APIRouter(prefix="/api", tags=["monitor"], dependencies=[Depends(get_current_user)])

# ── 内存日志 Handler（由 main.py 注册） ───────────────────────
class MemoryLogHandler(logging.Handler):
    """将日志保存在内存列表中，供 /api/logs 读取"""
    def __init__(self, capacity: int = 500):
        super().__init__()
        self.capacity = capacity
        self.records: list = []

    def emit(self, record: logging.LogRecord):
        entry = {
            "time": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": self.format(record),
        }
        self.records.append(entry)
        if len(self.records) > self.capacity:
            self.records = self.records[-self.capacity:]


# 全局单例，main.py 会将其注册到 root logger
memory_handler = MemoryLogHandler(capacity=500)


@router.get("/metrics")
def get_metrics(db: Session = Depends(get_db)):
    """返回系统指标"""
    # 数据库文件大小
    try:
        db_size = os.path.getsize(DB_PATH)
    except Exception:
        db_size = 0

    # 各表记录数
    table_counts = {
        "workspaces":       db.query(Workspace).count(),
        "projects":         db.query(Project).count(),
        "apis":             db.query(Api).count(),
        "test_runs":        db.query(TestRun).count(),
        "request_history":  db.query(RequestHistory).count(),
    }

    # 最近24小时请求量
    since_24h = datetime.now() - timedelta(hours=24)
    requests_24h = db.query(RequestHistory).filter(
        RequestHistory.created_at >= since_24h
    ).count()

    # 平均响应时间（ms）
    avg_resp = db.query(func.avg(RequestHistory.response_time)).scalar()
    avg_response_ms = round(float(avg_resp), 2) if avg_resp else 0.0

    # 成功率（status_code < 400）
    total_hist = db.query(RequestHistory).count()
    success_hist = db.query(RequestHistory).filter(
        RequestHistory.response_status < 400,
        RequestHistory.response_status > 0,
    ).count()
    success_rate = round(success_hist / total_hist * 100, 2) if total_hist else 0.0

    return {
        "db_size_bytes":    db_size,
        "db_size_mb":       round(db_size / 1024 / 1024, 3),
        "table_counts":     table_counts,
        "requests_24h":     requests_24h,
        "avg_response_ms":  avg_response_ms,
        "success_rate":     success_rate,
        "total_requests":   total_hist,
    }


@router.get("/logs")
def get_logs(
    level: Optional[str] = None,
    limit: int = 100,
):
    """返回最近的系统日志（从内存 handler 读取）"""
    records = memory_handler.records[:]
    if level:
        level_upper = level.upper()
        records = [r for r in records if r["level"] == level_upper]
    # 返回最新的 limit 条
    return {
        "total": len(records),
        "items": records[-limit:][::-1],  # 最新在前
    }
