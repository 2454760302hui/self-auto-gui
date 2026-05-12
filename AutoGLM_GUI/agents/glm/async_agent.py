"""AsyncGLMAgent - 异步 GLM Agent，使用流式文本解析。

支持两种模式：
- Vision 模式：模型支持图像输入，发送截图
- Text-only 模式：模型不支持图像，发送 UI 元素描述（通过 uiautomator dump）
"""

import asyncio
import json
import traceback
from collections.abc import AsyncGenerator
from typing import Any
from collections.abc import Callable

from AutoGLM_GUI.agents.base import AsyncAgentBase
from AutoGLM_GUI.agents.protocols import AsyncAgent
from AutoGLM_GUI.config import AgentConfig, ModelConfig
from AutoGLM_GUI.device_protocol import DeviceProtocol
from AutoGLM_GUI.logger import logger
from AutoGLM_GUI.model import MessageBuilder
from AutoGLM_GUI.prompt_config import get_messages, get_system_prompt
from AutoGLM_GUI.trace import trace_span

from .parser import GLMParser


class AsyncGLMAgent(AsyncAgentBase, AsyncAgent):
    """异步 GLM Agent，通过流式文本 + 自定义格式解析执行操作。"""

    def __init__(
        self,
        model_config: ModelConfig,
        agent_config: AgentConfig,
        device: DeviceProtocol,
        confirmation_callback: Callable[[str], bool] | None = None,
        takeover_callback: Callable[[str], None] | None = None,
    ):
        self.parser = GLMParser()
        super().__init__(
            model_config=model_config,
            agent_config=agent_config,
            device=device,
            confirmation_callback=confirmation_callback,
            takeover_callback=takeover_callback,
        )

    def _get_default_system_prompt(self, lang: str) -> str:
        prompt = get_system_prompt(lang)
        if not self.model_config.supports_vision:
            prompt += self._text_only_prompt_suffix()
        return prompt

    @staticmethod
    def _text_only_prompt_suffix() -> str:
        return """

重要提示：你无法看到屏幕截图，但会收到当前屏幕的UI元素列表。每个元素包含 text（文本）、desc（描述）、id（资源ID）、pos（坐标位置，0-1000比例）和 clickable（是否可点击）属性。
请根据这些UI元素信息判断应执行的操作。element 坐标请直接使用列表中的 pos 值。
"""

    def _prepare_initial_context(
        self, task: str, screenshot_base64: str, current_app: str
    ) -> None:
        screen_info = MessageBuilder.build_screen_info(current_app)

        if self.model_config.supports_vision:
            initial_message = f"{task}\n\n** Screen Info **\n\n{screen_info}"
            self._context.append(
                MessageBuilder.create_user_message(
                    text=initial_message, image_base64=screenshot_base64
                )
            )
            # Remove the image from initial context - _execute_step will add a fresh screenshot
            self._context[-1] = MessageBuilder.remove_images_from_message(
                self._context[-1]
            )
        else:
            # Text-only mode: get UI elements instead of screenshot
            ui_text = self._get_ui_elements_text(current_app)
            initial_message = f"{task}\n\n{ui_text}"
            self._context.append(
                MessageBuilder.create_user_message(text=initial_message)
            )

    def _get_ui_elements_text(self, current_app: str = "") -> str:
        """Dump UI hierarchy and build text description for non-vision models."""
        try:
            from AutoGLM_GUI.accessibility import dump_ui_hierarchy, build_screen_description

            screenshot = self.device.get_screenshot()
            elements = dump_ui_hierarchy(self.device.device_id)
            desc = build_screen_description(
                elements, screenshot.width, screenshot.height, current_app
            )
            logger.info(f"UI dump: {len(elements)} elements for text-only mode")
            return desc
        except Exception as e:
            logger.warning(f"UI dump failed: {e}")
            return f"** Screen Info **\n\nCurrent App: {current_app}\n(UI dump unavailable)"

    async def _execute_step(self) -> AsyncGenerator[dict[str, Any], None]:
        """执行单步：获取截图 → 流式调用 LLM → 解析文本 → 执行动作。"""
        self._step_count += 1

        # 1. 获取当前屏幕状态
        try:
            with trace_span(
                "step.capture_screenshot",
                attrs={"step": self._step_count, "agent_type": self.__class__.__name__},
            ):
                screenshot = await asyncio.to_thread(self.device.get_screenshot)
            with trace_span(
                "step.get_current_app",
                attrs={"step": self._step_count, "agent_type": self.__class__.__name__},
            ):
                current_app = await asyncio.to_thread(self.device.get_current_app)
        except Exception as e:
            logger.error(f"Failed to get device info: {e}")
            yield {"type": "error", "data": {"message": f"Device error: {e}"}}
            yield {
                "type": "step",
                "data": {
                    "step": self._step_count,
                    "thinking": "",
                    "action": None,
                    "success": False,
                    "finished": True,
                    "message": f"Device error: {e}",
                },
            }
            return

        # 2. 构建消息
        with trace_span(
            "step.build_message",
            attrs={"step": self._step_count, "agent_type": self.__class__.__name__},
        ):
            if self.model_config.supports_vision:
                screen_info = MessageBuilder.build_screen_info(current_app)
                text_content = f"** Screen Info **\n\n{screen_info}"
                self._context.append(
                    MessageBuilder.create_user_message(
                        text=text_content, image_base64=screenshot.base64_data
                    )
                )
            else:
                # Text-only mode: use UI elements instead of screenshot
                ui_text = self._get_ui_elements_text(current_app)
                self._context.append(
                    MessageBuilder.create_user_message(text=ui_text)
                )

        # 3. 流式调用 OpenAI
        try:
            if self.agent_config.verbose:
                msgs = get_messages(self.agent_config.lang)
                logger.debug(f"💭 {msgs['thinking']}:")

            thinking_parts = []
            raw_content = ""

            with trace_span(
                "step.llm",
                attrs={
                    "step": self._step_count,
                    "agent_type": self.__class__.__name__,
                    "model_name": self.model_config.model_name,
                    "message_count": len(self._context),
                },
            ):
                async for chunk_data in self._stream_openai(self._context):
                    if self._cancel_event.is_set():
                        raise asyncio.CancelledError()

                    if chunk_data["type"] == "thinking":
                        thinking_parts.append(chunk_data["content"])
                        yield {
                            "type": "thinking",
                            "data": {"chunk": chunk_data["content"]},
                        }
                        if self.agent_config.verbose:
                            logger.debug(chunk_data["content"])

                    elif chunk_data["type"] == "raw":
                        raw_content += chunk_data["content"]

            thinking = "".join(thinking_parts)

        except asyncio.CancelledError:
            logger.info(f"Step {self._step_count} cancelled during LLM call")
            raise

        except Exception as e:
            logger.error(f"LLM error: {e}")
            if self.agent_config.verbose:
                logger.debug(traceback.format_exc())
            yield {"type": "error", "data": {"message": f"Model error: {e}"}}
            yield {
                "type": "step",
                "data": {
                    "step": self._step_count,
                    "thinking": "",
                    "action": None,
                    "success": False,
                    "finished": True,
                    "message": f"Model error: {e}",
                },
            }
            return

        # 4. 解析 action
        with trace_span(
            "step.parse_action",
            attrs={"step": self._step_count, "agent_type": self.__class__.__name__},
        ):
            logger.info(f"raw_content ({len(raw_content)} chars): {raw_content[:500]}")
            _, action_str = self._parse_raw_response(raw_content)
            try:
                action = self.parser.parse(action_str)
            except ValueError as e:
                logger.warning(f"Failed to parse action: {e}, treating as finish")
                action = {"_metadata": "finish", "message": action_str}

        if self.agent_config.verbose:
            msgs = get_messages(self.agent_config.lang)
            logger.debug(f"🎯 {msgs['action']}:")
            logger.debug(json.dumps(action, ensure_ascii=False, indent=2))

        # 5. 执行 action
        try:
            with trace_span(
                "step.execute_action",
                attrs={
                    "step": self._step_count,
                    "agent_type": self.__class__.__name__,
                    "action_name": action.get("action"),
                    "action_type": action.get("_metadata"),
                },
            ):
                result = await asyncio.to_thread(
                    self.action_handler.execute,
                    action,
                    screenshot.width,
                    screenshot.height,
                )
        except Exception as e:
            logger.error(f"Action execution error: {e}")
            if self.agent_config.verbose:
                logger.debug(traceback.format_exc())
            from AutoGLM_GUI.actions import ActionResult

            result = ActionResult(success=False, should_finish=True, message=str(e))

        # 6. 更新上下文
        with trace_span(
            "step.update_context",
            attrs={"step": self._step_count, "agent_type": self.__class__.__name__},
        ):
            self._context[-1] = MessageBuilder.remove_images_from_message(
                self._context[-1]
            )
            self._context.append(
                MessageBuilder.create_assistant_message(
                    f"<think>{thinking}</think><answer>{action_str}</answer>"
                )
            )

        # 7. 检查完成
        finished = action.get("_metadata") == "finish" or result.should_finish
        if finished and self.agent_config.verbose:
            msgs = get_messages(self.agent_config.lang)
            logger.debug(
                f"✅ {msgs['task_completed']}: "
                f"{result.message or action.get('message', msgs['done'])}"
            )

        # 8. 返回步骤结果
        yield {
            "type": "step",
            "data": {
                "step": self._step_count,
                "thinking": thinking,
                "action": action,
                "success": result.success,
                "finished": finished,
                "message": result.message or action.get("message"),
                "screenshot": screenshot.base64_data if screenshot else None,
            },
        }

    async def _stream_openai(
        self, messages: list[dict[str, Any]]
    ) -> AsyncGenerator[dict[str, str], None]:
        """流式调用 OpenAI，yield thinking chunks。"""
        # Debug: log message structure (image count, roles)
        img_count = sum(
            1 for m in messages
            if isinstance(m.get("content"), list)
            for p in m["content"]
            if p.get("type") == "image_url"
        )
        logger.info(f"Calling LLM stream: {len(messages)} messages, {img_count} images")
        # Log each message role and content type for debugging
        for i, m in enumerate(messages):
            content = m.get("content")
            if isinstance(content, str):
                logger.debug(f"  msg[{i}] role={m['role']} type=str len={len(content)}")
            elif isinstance(content, list):
                parts_summary = [p.get("type", "?") for p in content]
                logger.debug(f"  msg[{i}] role={m['role']} type=list parts={parts_summary}")
            else:
                logger.debug(f"  msg[{i}] role={m['role']} type={type(content).__name__}")
        logger.debug(f"  model={self.model_config.model_name} extra_body={self.model_config.extra_body}")

        # For multi-turn with images, some API providers don't support stream=True.
        # The 400 error occurs during stream iteration, not creation, so we must
        # decide upfront whether to use stream or non-stream.
        # Text-only mode (no images) can always use stream.
        use_stream = not (len(messages) > 3 and img_count > 0)

        action_markers = ["finish(message=", "do(action="]

        if not use_stream:
            logger.info(f"Using non-stream mode: {len(messages)} messages, {img_count} images")
            # Non-streaming for providers that don't support stream + multi-turn
            response = await self.openai_client.chat.completions.create(
                messages=messages,  # type: ignore[arg-type]
                model=self.model_config.model_name,
                max_tokens=self.model_config.max_tokens,
                temperature=self.model_config.temperature,
                top_p=self.model_config.top_p,
                frequency_penalty=self.model_config.frequency_penalty,
                extra_body=self.model_config.extra_body,
                stream=False,
            )
            full_content = response.choices[0].message.content or ""
            yield {"type": "raw", "content": full_content}

            # Split thinking from action
            for marker in action_markers:
                if marker in full_content:
                    thinking_part = full_content.split(marker, 1)[0]
                    if thinking_part.strip():
                        yield {"type": "thinking", "content": thinking_part}
                    break
            else:
                if full_content.strip():
                    yield {"type": "thinking", "content": full_content}
            return

        # Streaming path
        stream = await self.openai_client.chat.completions.create(
            messages=messages,  # type: ignore[arg-type]
            model=self.model_config.model_name,
            max_tokens=self.model_config.max_tokens,
            temperature=self.model_config.temperature,
            top_p=self.model_config.top_p,
            frequency_penalty=self.model_config.frequency_penalty,
            extra_body=self.model_config.extra_body,
            stream=True,
        )
        buffer = ""
        in_action_phase = False

        try:
            async for chunk in stream:
                if self._cancel_event.is_set():
                    await stream.close()
                    raise asyncio.CancelledError()

                if len(chunk.choices) == 0:
                    continue

                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    yield {"type": "raw", "content": content}

                    if in_action_phase:
                        continue

                    buffer += content

                    marker_found = False
                    for marker in action_markers:
                        if marker in buffer:
                            thinking_part = buffer.split(marker, 1)[0]
                            yield {"type": "thinking", "content": thinking_part}
                            in_action_phase = True
                            marker_found = True
                            break

                    if marker_found:
                        continue

                    is_potential_marker = False
                    for marker in action_markers:
                        for i in range(1, len(marker)):
                            if buffer.endswith(marker[:i]):
                                is_potential_marker = True
                                break
                        if is_potential_marker:
                            break

                    if not is_potential_marker and len(buffer) > 0:
                        yield {"type": "thinking", "content": buffer}
                        buffer = ""

        finally:
            await stream.close()

    @staticmethod
    def _parse_raw_response(content: str) -> tuple[str, str]:
        """解析原始响应，提取 thinking 和 action。

        模型可能输出多种格式：
        1. do(action="Tap", element=[834,780]) — 直接动作
        2. <answer>思考</answer><answer>do(action="Tap", ...)</answer> — 多 answer 块
        3. <answer>do(action="Tap", ...)</answer> — 单 answer 块
        """
        # 先清理所有 </answer> 标签，统一处理
        cleaned = content.replace("</answer>", "")

        if "finish(message=" in cleaned:
            parts = cleaned.split("finish(message=", 1)
            thinking = parts[0].replace("<answer>", "").strip()
            action = "finish(message=" + parts[1].strip()
            return thinking, action

        if "do(action=" in cleaned:
            parts = cleaned.split("do(action=", 1)
            thinking = parts[0].replace("<answer>", "").strip()
            action = "do(action=" + parts[1].strip()
            return thinking, action

        if "<answer>" in content:
            parts = content.split("<answer>", 1)
            thinking = parts[0].strip()
            action = parts[1].replace("</answer>", "").strip()
            return thinking, action

        # Fallback: if raw content starts with do( or finish( without tags
        stripped = content.strip()
        if stripped.startswith("finish(") or stripped.startswith("do("):
            return "", stripped

        # If nothing matched, log and return empty action
        logger.warning(f"No action markers found in raw_content ({len(content)} chars): {content[:300]}")
        return "", content
