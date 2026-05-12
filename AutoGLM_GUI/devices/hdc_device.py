"""HDC Device implementation of DeviceProtocol for HarmonyOS."""

from AutoGLM_GUI import hdc
from AutoGLM_GUI.device_protocol import DeviceProtocol, Screenshot
from AutoGLM_GUI.trace import trace_span


class HDCDevice(DeviceProtocol):
    """HarmonyOS device implementation using hdc subprocess calls.

    Note: This device does NOT implement detect_and_set_adb_keyboard or
    restore_keyboard since HarmonyOS uses `input text` directly without
    needing a custom IME.
    """

    def __init__(self, device_id: str):
        self._device_id = device_id

    @property
    def device_id(self) -> str:
        return self._device_id

    def get_screenshot(self, timeout: int = 10) -> Screenshot:
        with trace_span(
            "device.get_screenshot",
            attrs={"device_id": self._device_id, "device_impl": "hdc", "timeout": timeout},
        ):
            result = hdc.screenshot.capture_screenshot(self._device_id, timeout=timeout)
            if not result.get("success"):
                raise RuntimeError(result.get("error", "Screenshot failed"))
            return Screenshot(
                base64_data=result["image"],
                width=result.get("width", 0),
                height=result.get("height", 0),
                is_sensitive=result.get("is_sensitive", False),
            )

    def tap(self, x: int, y: int, delay: float | None = None) -> None:
        with trace_span("device.tap", attrs={"device_id": self._device_id, "device_impl": "hdc", "x": x, "y": y}):
            hdc.device.tap(x, y, self._device_id, delay)

    def double_tap(self, x: int, y: int, delay: float | None = None) -> None:
        with trace_span("device.double_tap", attrs={"device_id": self._device_id, "device_impl": "hdc", "x": x, "y": y}):
            hdc.device.double_tap(x, y, self._device_id, delay)

    def long_press(self, x: int, y: int, duration_ms: int = 3000, delay: float | None = None) -> None:
        with trace_span("device.long_press", attrs={"device_id": self._device_id, "device_impl": "hdc", "x": x, "y": y}):
            hdc.device.long_press(x, y, duration_ms, self._device_id, delay)

    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int | None = None, delay: float | None = None) -> None:
        with trace_span("device.swipe", attrs={"device_id": self._device_id, "device_impl": "hdc"}):
            hdc.device.swipe(start_x, start_y, end_x, end_y, duration_ms, self._device_id, delay)

    def type_text(self, text: str) -> None:
        with trace_span("device.type_text", attrs={"device_id": self._device_id, "device_impl": "hdc", "text_length": len(text)}):
            hdc.input.type_text(text, self._device_id)

    def clear_text(self) -> None:
        with trace_span("device.clear_text", attrs={"device_id": self._device_id, "device_impl": "hdc"}):
            hdc.input.clear_text(self._device_id)

    def back(self, delay: float | None = None) -> None:
        with trace_span("device.back", attrs={"device_id": self._device_id, "device_impl": "hdc"}):
            hdc.device.back(self._device_id, delay)

    def home(self, delay: float | None = None) -> None:
        with trace_span("device.home", attrs={"device_id": self._device_id, "device_impl": "hdc"}):
            hdc.device.home(self._device_id, delay)

    def launch_app(self, app_name: str, delay: float | None = None) -> bool:
        with trace_span("device.launch_app", attrs={"device_id": self._device_id, "device_impl": "hdc", "app_name": app_name}):
            return hdc.device.launch_app(app_name, self._device_id, delay)

    def get_current_app(self) -> str:
        with trace_span("device.get_current_app", attrs={"device_id": self._device_id, "device_impl": "hdc"}):
            return hdc.device.get_current_app(self._device_id)

    # === Clipboard Operations ===
    def get_clipboard(self) -> str:
        """Get clipboard text from HarmonyOS device."""
        with trace_span("device.get_clipboard", attrs={"device_id": self._device_id, "device_impl": "hdc"}):
            from AutoGLM_GUI.hdc.input import get_clipboard_text
            return get_clipboard_text(self._device_id)

    def set_clipboard(self, text: str) -> None:
        """Set clipboard text on HarmonyOS device."""
        with trace_span("device.set_clipboard", attrs={"device_id": self._device_id, "device_impl": "hdc", "text_length": len(text)}):
            from AutoGLM_GUI.hdc.input import set_clipboard_text
            set_clipboard_text(text, self._device_id)

    def paste(self, delay: float | None = None) -> None:
        """Trigger paste action via keyevent."""
        with trace_span("device.paste", attrs={"device_id": self._device_id, "device_impl": "hdc"}):
            hdc.device.paste(self._device_id, delay)

    def select_all(self, delay: float | None = None) -> None:
        """Trigger select-all via keyevent."""
        with trace_span("device.select_all", attrs={"device_id": self._device_id, "device_impl": "hdc"}):
            hdc.device.select_all(self._device_id, delay)
