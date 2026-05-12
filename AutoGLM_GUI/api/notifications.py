"""Notification webhook API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from AutoGLM_GUI.notification_manager import notification_manager

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationConfigUpdate(BaseModel):
    enabled: bool | None = None
    webhook_url: str | None = None
    notify_on_success: bool | None = None
    notify_on_failure: bool | None = None
    timeout_seconds: int | None = None


@router.get("/config")
async def get_notification_config():
    config = notification_manager.get_config()
    return config.model_dump()


@router.post("/config")
async def update_notification_config(data: NotificationConfigUpdate):
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    config = notification_manager.update_config(updates)
    return config.model_dump()


@router.post("/test")
async def test_notification():
    success, message = await notification_manager.test_notification()
    return {"success": success, "message": message}
