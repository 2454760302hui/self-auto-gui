"""Batch task execution API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from AutoGLM_GUI.task_manager import task_manager

router = APIRouter(prefix="/batch", tags=["batch"])


class BatchTaskRequest(BaseModel):
    device_ids: list[str]
    message: str


class BatchTaskResponse(BaseModel):
    results: list[dict]
    success_count: int
    fail_count: int


@router.post("/execute", response_model=BatchTaskResponse)
async def batch_execute(data: BatchTaskRequest):
    if not data.device_ids:
        raise HTTPException(status_code=400, detail="No device IDs provided")
    if not data.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    results = []
    success_count = 0
    fail_count = 0

    for device_id in data.device_ids:
        try:
            task = await task_manager.submit_task(
                device_id=device_id,
                message=data.message,
            )
            results.append({
                "device_id": device_id,
                "task_id": task.get("task_id", task.get("session_id", "")),
                "status": "submitted",
            })
            success_count += 1
        except Exception as e:
            results.append({
                "device_id": device_id,
                "error": str(e),
                "status": "failed",
            })
            fail_count += 1

    return BatchTaskResponse(
        results=results,
        success_count=success_count,
        fail_count=fail_count,
    )
