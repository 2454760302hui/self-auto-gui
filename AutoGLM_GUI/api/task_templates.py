"""Task template API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from AutoGLM_GUI.task_template_manager import (
    TaskTemplateCreate,
    TaskTemplateUpdate,
    task_template_manager,
)

router = APIRouter(prefix="/task-templates", tags=["task-templates"])


@router.get("")
async def list_templates(category: str | None = None):
    templates = task_template_manager.list_templates(category)
    return {"templates": [t.model_dump() for t in templates]}


@router.get("/categories")
async def list_categories():
    categories = task_template_manager.list_categories()
    return {"categories": categories}


@router.get("/{template_id}")
async def get_template(template_id: str):
    tpl = task_template_manager.get_template(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return tpl.model_dump()


@router.post("")
async def create_template(data: TaskTemplateCreate):
    tpl = task_template_manager.create_template(data)
    return tpl.model_dump()


@router.put("/{template_id}")
async def update_template(template_id: str, data: TaskTemplateUpdate):
    tpl = task_template_manager.update_template(template_id, data)
    if not tpl:
        raise HTTPException(
            status_code=404, detail="Template not found or is built-in"
        )
    return tpl.model_dump()


@router.delete("/{template_id}")
async def delete_template(template_id: str):
    success = task_template_manager.delete_template(template_id)
    if not success:
        raise HTTPException(
            status_code=404, detail="Template not found or is built-in"
        )
    return {"success": True}
