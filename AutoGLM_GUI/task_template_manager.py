"""Task template manager for XNext."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel


class TaskTemplate(BaseModel):
    id: str
    name: str
    description: str = ""
    message: str
    category: str = "general"
    is_builtin: bool = False
    created_at: str = ""
    updated_at: str = ""


class TaskTemplateCreate(BaseModel):
    name: str
    description: str = ""
    message: str
    category: str = "general"


class TaskTemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    message: str | None = None
    category: str | None = None


BUILTIN_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "builtin-open-wechat",
        "name": "打开微信",
        "description": "打开微信应用",
        "message": "打开微信",
        "category": "应用",
        "is_builtin": True,
    },
    {
        "id": "builtin-screenshot",
        "name": "截图",
        "description": "截取当前屏幕并保存",
        "message": "截取当前屏幕并保存到相册",
        "category": "工具",
        "is_builtin": True,
    },
    {
        "id": "builtin-check-messages",
        "name": "检查消息",
        "description": "检查未读消息通知",
        "message": "打开通知中心查看未读消息",
        "category": "工具",
        "is_builtin": True,
    },
    {
        "id": "builtin-open-settings",
        "name": "打开设置",
        "description": "打开系统设置应用",
        "message": "打开设置",
        "category": "系统",
        "is_builtin": True,
    },
    {
        "id": "builtin-check-battery",
        "name": "检查电量",
        "description": "查看当前电池电量和状态",
        "message": "查看当前电池电量是多少",
        "category": "系统",
        "is_builtin": True,
    },
    {
        "id": "builtin-open-camera",
        "name": "打开相机",
        "description": "打开相机拍照",
        "message": "打开相机",
        "category": "应用",
        "is_builtin": True,
    },
]


def _get_storage_path() -> str:
    config_dir = os.path.join(os.path.expanduser("~"), ".config", "autoglm")
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, "task_templates.json")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaskTemplateManager:
    def __init__(self) -> None:
        self._templates: dict[str, TaskTemplate] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True

        # Load built-in templates
        for t in BUILTIN_TEMPLATES:
            tpl = TaskTemplate(
                **t,
                created_at=_now_iso(),
                updated_at=_now_iso(),
            )
            self._templates[tpl.id] = tpl

        # Load user templates from file
        path = _get_storage_path()
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                for item in data:
                    tpl = TaskTemplate(**item)
                    self._templates[tpl.id] = tpl
            except (json.JSONDecodeError, Exception):
                pass

    def _save_user_templates(self) -> None:
        user_templates = [
            t.model_dump()
            for t in self._templates.values()
            if not t.is_builtin
        ]
        path = _get_storage_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(user_templates, f, ensure_ascii=False, indent=2)

    def list_templates(self, category: str | None = None) -> list[TaskTemplate]:
        self._ensure_loaded()
        templates = list(self._templates.values())
        if category:
            templates = [t for t in templates if t.category == category]
        return sorted(templates, key=lambda t: (not t.is_builtin, t.name))

    def get_template(self, template_id: str) -> TaskTemplate | None:
        self._ensure_loaded()
        return self._templates.get(template_id)

    def create_template(self, data: TaskTemplateCreate) -> TaskTemplate:
        self._ensure_loaded()
        tpl = TaskTemplate(
            id=f"user-{uuid.uuid4().hex[:12]}",
            name=data.name,
            description=data.description,
            message=data.message,
            category=data.category,
            is_builtin=False,
            created_at=_now_iso(),
            updated_at=_now_iso(),
        )
        self._templates[tpl.id] = tpl
        self._save_user_templates()
        return tpl

    def update_template(
        self, template_id: str, data: TaskTemplateUpdate
    ) -> TaskTemplate | None:
        self._ensure_loaded()
        tpl = self._templates.get(template_id)
        if not tpl:
            return None
        if tpl.is_builtin:
            return None
        if data.name is not None:
            tpl.name = data.name
        if data.description is not None:
            tpl.description = data.description
        if data.message is not None:
            tpl.message = data.message
        if data.category is not None:
            tpl.category = data.category
        tpl.updated_at = _now_iso()
        self._save_user_templates()
        return tpl

    def delete_template(self, template_id: str) -> bool:
        self._ensure_loaded()
        tpl = self._templates.get(template_id)
        if not tpl or tpl.is_builtin:
            return False
        del self._templates[template_id]
        self._save_user_templates()
        return True

    def list_categories(self) -> list[str]:
        self._ensure_loaded()
        categories = sorted({t.category for t in self._templates.values()})
        return categories


task_template_manager = TaskTemplateManager()
