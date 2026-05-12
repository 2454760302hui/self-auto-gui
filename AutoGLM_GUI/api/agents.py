"""Agent lifecycle and chat routes."""

import asyncio
import json

from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from AutoGLM_GUI.schemas import (
    AbortRequest,
    ChatRequest,
    ChatResponse,
    ConfigResponse,
    ConfigSaveRequest,
    ConfigTestRequest,
    ConfigTestResponse,
    ResetRequest,
    StatusResponse,
)
from AutoGLM_GUI.version import APP_VERSION

router = APIRouter()


SSEPayload = dict[str, Any]


def _create_sse_event(
    event_type: str, data: SSEPayload, role: str = "assistant"
) -> SSEPayload:
    """Create an SSE event with standardized fields including role."""
    event_data = {"type": event_type, "role": role, **data}
    return event_data


def _resolve_device_serial(device_id: str) -> str:
    from AutoGLM_GUI.device_manager import DeviceManager

    device_manager = DeviceManager.get_instance()
    return device_manager.get_serial_by_device_id(device_id) or device_id


async def _create_legacy_chat_task(request: ChatRequest) -> dict[str, Any]:
    from AutoGLM_GUI.task_manager import task_manager

    session = await task_manager.get_or_create_legacy_chat_session(
        device_id=request.device_id,
        device_serial=_resolve_device_serial(request.device_id),
    )
    return await task_manager.submit_chat_task(
        session_id=str(session["id"]),
        device_id=request.device_id,
        device_serial=str(session["device_serial"]),
        message=request.message,
    )


@router.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Compatibility wrapper around the new task-backed chat flow."""
    from AutoGLM_GUI.task_manager import task_manager
    from AutoGLM_GUI.task_store import TaskStatus

    task = await _create_legacy_chat_task(request)
    final_task = await task_manager.wait_for_task(task["id"])
    if final_task is None:
        raise HTTPException(status_code=500, detail="Task disappeared unexpectedly")

    success = final_task["status"] == TaskStatus.SUCCEEDED.value
    message = (
        final_task.get("final_message")
        or final_task.get("error_message")
        or final_task["status"]
    )
    return ChatResponse(
        result=str(message),
        steps=int(final_task.get("step_count", 0)),
        success=success,
    )


@router.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """Compatibility SSE endpoint backed by the new task event stream."""
    from AutoGLM_GUI.task_store import TERMINAL_TASK_STATUSES, task_store

    task = await _create_legacy_chat_task(request)

    async def event_generator():
        last_seq = 0
        while True:
            events = await asyncio.to_thread(
                task_store.list_task_events,
                task["id"],
                after_seq=last_seq,
            )
            for event in events:
                last_seq = int(event["seq"])
                event_type = str(event["event_type"])
                if event_type == "status":
                    continue
                sse_event = _create_sse_event(
                    event_type,
                    dict(event["payload"]),
                    role=str(event["role"]),
                )
                yield f"event: {event_type}\n"
                yield f"data: {json.dumps(sse_event, ensure_ascii=False)}\n\n"

            current_task = await asyncio.to_thread(task_store.get_task, task["id"])
            if (
                current_task is None or current_task["status"] in TERMINAL_TASK_STATUSES
            ) and not events:
                break
            await asyncio.sleep(0.2)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/api/status", response_model=StatusResponse)
def get_status(device_id: str | None = None) -> StatusResponse:
    """获取 Agent 状态和版本信息（多设备支持）。"""
    from AutoGLM_GUI.phone_agent_manager import PhoneAgentManager

    manager = PhoneAgentManager.get_instance()

    if device_id is None:
        return StatusResponse(
            version=APP_VERSION,
            initialized=len(manager.list_agents()) > 0,
            step_count=0,
        )

    if not manager.is_initialized(device_id):
        return StatusResponse(
            version=APP_VERSION,
            initialized=False,
            step_count=0,
        )

    agent = manager.get_agent(device_id)
    return StatusResponse(
        version=APP_VERSION,
        initialized=True,
        step_count=agent.step_count,
    )


@router.post("/api/reset")
def reset_agent(request: ResetRequest) -> dict[str, Any]:
    """重置 Agent 状态（多设备支持）。"""
    from AutoGLM_GUI.exceptions import AgentNotInitializedError
    from AutoGLM_GUI.phone_agent_manager import PhoneAgentManager

    device_id = request.device_id
    manager = PhoneAgentManager.get_instance()

    try:
        manager.reset_agent(device_id)
        return {
            "success": True,
            "device_id": device_id,
            "message": f"Agent reset for device {device_id}",
        }
    except AgentNotInitializedError:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")


@router.post("/api/chat/abort")
async def abort_chat(request: AbortRequest) -> dict[str, Any]:
    """Cancel the latest active task for the device."""
    from AutoGLM_GUI.phone_agent_manager import PhoneAgentManager
    from AutoGLM_GUI.task_manager import task_manager
    from AutoGLM_GUI.task_store import TERMINAL_TASK_STATUSES, TaskStatus

    task = await task_manager.cancel_latest_chat_task(request.device_id)
    success = task is not None and (
        task["status"] not in TERMINAL_TASK_STATUSES
        or task["status"] == TaskStatus.CANCELLED.value
    )
    if not success:
        success = await PhoneAgentManager.get_instance().abort_streaming_chat_async(
            request.device_id
        )

    return {
        "success": success,
        "message": "Abort requested" if success else "No active chat found",
    }


@router.get("/api/config", response_model=ConfigResponse)
def get_config_endpoint() -> ConfigResponse:
    """获取当前有效配置."""
    from AutoGLM_GUI.config_manager import config_manager
    from AutoGLM_GUI.schemas import mask_api_key

    # 热重载：检查文件是否被外部修改
    config_manager.load_file_config()

    # 获取有效配置和来源
    effective_config = config_manager.get_effective_config()
    source = config_manager.get_config_source()

    # 检测冲突
    conflicts = config_manager.detect_conflicts()

    # 判断决策模型是否使用了回退
    file_config = config_manager._file_layer.to_dict()
    decision_uses_fallback = not file_config.get("decision_base_url")

    # API Key 始终返回脱敏值，不返回明文
    api_key_masked = mask_api_key(effective_config.api_key) if effective_config.api_key else ""
    decision_api_key_masked = mask_api_key(effective_config.decision_api_key or "") if effective_config.decision_api_key else ""

    return ConfigResponse(
        base_url=effective_config.base_url,
        model_name=effective_config.model_name,
        api_key=api_key_masked,  # 返回脱敏值而非明文
        api_key_masked=api_key_masked,
        source=source.value,
        agent_type=effective_config.agent_type,
        agent_config_params=effective_config.agent_config_params,
        default_max_steps=effective_config.default_max_steps,
        layered_max_turns=effective_config.layered_max_turns,
        decision_base_url=effective_config.decision_base_url,
        decision_model_name=effective_config.decision_model_name,
        decision_api_key=decision_api_key_masked,  # 返回脱敏值而非明文
        decision_api_key_masked=decision_api_key_masked,
        decision_uses_fallback=decision_uses_fallback,
        supports_vision=effective_config.supports_vision,
        conflicts=[
            {
                "field": c.field,
                "file_value": c.file_value,
                "override_value": c.override_value,
                "override_source": c.override_source.value,
            }
            for c in conflicts
        ]
        if conflicts
        else None,
    )


@router.post("/api/config")
def save_config_endpoint(request: ConfigSaveRequest) -> dict[str, Any]:
    """保存配置到文件.

    配置保存后需重启应用以立即生效。
    """
    from AutoGLM_GUI.config_manager import ConfigModel, config_manager
    from AutoGLM_GUI.schemas import mask_api_key

    try:
        # 检查 API Key 是否被用户修改（脱敏值说明未修改，保留原值）
        effective_config = config_manager.get_effective_config()
        current_api_key = effective_config.api_key if effective_config.api_key != "EMPTY" else ""
        current_decision_api_key = effective_config.decision_api_key or ""

        # 如果前端传回的 api_key 包含 *，说明用户未修改，使用原值
        api_key_to_save = request.api_key
        if api_key_to_save and "*" in api_key_to_save:
            api_key_to_save = current_api_key

        decision_api_key_to_save = request.decision_api_key
        if decision_api_key_to_save and "*" in decision_api_key_to_save:
            decision_api_key_to_save = current_decision_api_key

        # Validate incoming configuration
        ConfigModel(
            base_url=request.base_url,
            model_name=request.model_name,
            api_key=api_key_to_save or "EMPTY",
            default_max_steps=request.default_max_steps,
            layered_max_turns=request.layered_max_turns,
        )

        provided_fields = request.model_fields_set

        # 保存配置（合并模式，不丢失字段）
        success = config_manager.save_file_config(
            base_url=request.base_url,
            model_name=request.model_name,
            api_key=api_key_to_save,
            agent_type=request.agent_type,
            agent_config_params=request.agent_config_params,
            default_max_steps=request.default_max_steps,
            layered_max_turns=request.layered_max_turns,
            decision_base_url=request.decision_base_url,
            decision_model_name=request.decision_model_name,
            decision_api_key=decision_api_key_to_save,
            supports_vision=request.supports_vision,
            merge_mode=True,
            default_max_steps_set="default_max_steps" in provided_fields,
            layered_max_turns_set="layered_max_turns" in provided_fields,
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to save config")

        # 同步到环境变量
        config_manager.sync_to_env()

        # 检测冲突并返回警告
        conflicts = config_manager.detect_conflicts()

        response_message = (
            f"Configuration saved to {config_manager.get_config_path()}."
            " Restart required to apply new configuration immediately."
        )

        if conflicts:
            warnings = [
                f"{c.field}: file value overridden by {c.override_source.value}"
                for c in conflicts
            ]
            return {
                "success": True,
                "message": response_message,
                "warnings": warnings,
                "restart_required": True,
            }

        return {
            "success": True,
            "message": response_message,
            "restart_required": True,
        }

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Invalid configuration: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/config")
def delete_config_endpoint() -> dict[str, Any]:
    """删除配置文件."""
    from AutoGLM_GUI.config_manager import config_manager

    try:
        success = config_manager.delete_file_config()

        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete config")

        return {"success": True, "message": "Configuration deleted"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/config/test", response_model=ConfigTestResponse)
async def test_config_endpoint(request: ConfigTestRequest) -> ConfigTestResponse:
    """测试模型连接并检测视觉支持能力."""
    import time

    from openai import AsyncOpenAI

    base_url = request.base_url.strip().rstrip("/")
    api_key = request.api_key or "EMPTY"
    model_name = request.model_name.strip()

    if not base_url:
        return ConfigTestResponse(success=False, error="Base URL 不能为空")

    client = AsyncOpenAI(base_url=base_url, api_key=api_key, timeout=30.0)

    # 1. 连通性测试 — 发送简单文本请求
    try:
        t0 = time.monotonic()
        await client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10,
            stream=False,
        )
        elapsed_ms = (time.monotonic() - t0) * 1000
    except Exception as e:
        err_msg = str(e)
        if "401" in err_msg or "Unauthorized" in err_msg or "authentication" in err_msg.lower():
            return ConfigTestResponse(success=False, error="API Key 无效或未授权")
        if "404" in err_msg or "not found" in err_msg.lower():
            return ConfigTestResponse(success=False, error=f"模型 '{model_name}' 不存在")
        if "Connection" in err_msg or "connect" in err_msg.lower():
            return ConfigTestResponse(success=False, error=f"无法连接到 {base_url}")
        return ConfigTestResponse(success=False, error=err_msg[:200])

    # 2. 视觉支持检测 — 发送带图片的请求
    supports_vision = None
    try:
        import base64

        tiny_png = base64.b64encode(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
            b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00"
            b"\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        ).decode()

        await client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe this image in one word."},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{tiny_png}"},
                        },
                    ],
                }
            ],
            max_tokens=10,
            stream=False,
        )
        supports_vision = True
    except Exception:
        supports_vision = False

    return ConfigTestResponse(
        success=True,
        response_time_ms=round(elapsed_ms, 0),
        supports_vision=supports_vision,
    )
