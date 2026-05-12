"""Notification manager for XNext."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
from pydantic import BaseModel


class NotificationConfig(BaseModel):
    enabled: bool = False
    webhook_url: str = ""
    notify_on_success: bool = True
    notify_on_failure: bool = True
    timeout_seconds: int = 10


def _get_config_path() -> str:
    config_dir = os.path.join(os.path.expanduser("~"), ".config", "autoglm")
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, "notification_config.json")


class NotificationManager:
    def __init__(self) -> None:
        self._config: NotificationConfig | None = None

    def _load_config(self) -> NotificationConfig:
        if self._config is not None:
            return self._config
        path = _get_config_path()
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                self._config = NotificationConfig(**data)
            except Exception:
                self._config = NotificationConfig()
        else:
            self._config = NotificationConfig()
        return self._config

    def _save_config(self) -> None:
        if self._config is None:
            return
        path = _get_config_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._config.model_dump(), f, ensure_ascii=False, indent=2)

    def get_config(self) -> NotificationConfig:
        return self._load_config()

    def update_config(self, data: dict[str, Any]) -> NotificationConfig:
        config = self._load_config()
        for key, value in data.items():
            if hasattr(config, key):
                setattr(config, key, value)
        self._save_config()
        return config

    async def send_notification(
        self,
        event_type: str,
        task_id: str,
        device_id: str,
        status: str,
        message: str | None = None,
    ) -> bool:
        config = self._load_config()
        if not config.enabled or not config.webhook_url:
            return False

        if status == "completed" and not config.notify_on_success:
            return False
        if status in ("failed", "error") and not config.notify_on_failure:
            return False

        payload = {
            "event": event_type,
            "task_id": task_id,
            "device_id": device_id,
            "status": status,
            "message": message,
        }

        try:
            async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
                resp = await client.post(
                    config.webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                return resp.status_code < 400
        except Exception:
            return False

    async def test_notification(self) -> tuple[bool, str]:
        config = self._load_config()
        if not config.webhook_url:
            return False, "Webhook URL not configured"

        test_payload = {
            "event": "test",
            "task_id": "test-task",
            "device_id": "test-device",
            "status": "test",
            "message": "This is a test notification from XNext",
        }

        try:
            async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
                resp = await client.post(
                    config.webhook_url,
                    json=test_payload,
                    headers={"Content-Type": "application/json"},
                )
                if resp.status_code < 400:
                    return True, f"Success (HTTP {resp.status_code})"
                return False, f"HTTP {resp.status_code}: {resp.text[:200]}"
        except Exception as e:
            return False, str(e)


notification_manager = NotificationManager()
