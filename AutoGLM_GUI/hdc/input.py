"""Text input for HarmonyOS devices via hdc shell."""

import subprocess
import urllib.parse

from AutoGLM_GUI.hdc.connection import build_hdc_command
from AutoGLM_GUI.logger import logger
from AutoGLM_GUI.trace import trace_span


def type_text(text: str, device_id: str | None = None) -> None:
    """Type text into the currently focused input field on HarmonyOS.

    Uses `hdc shell input text` which is simpler than ADB's ADBKeyBoard approach.
    """
    hdc_prefix = build_hdc_command(device_id)
    encoded = urllib.parse.quote(text, safe="")

    with trace_span("hdc.type_text", attrs={"device_id": device_id, "text_length": len(text)}):
        subprocess.run(
            hdc_prefix + ["shell", f"input text {encoded}"],
            capture_output=True, text=True,
        )


def clear_text(device_id: str | None = None) -> None:
    """Clear text in the currently focused input field via keyevents."""
    hdc_prefix = build_hdc_command(device_id)

    with trace_span("hdc.clear_text", attrs={"device_id": device_id}):
        # Select all then delete
        subprocess.run(
            hdc_prefix + ["shell", "input keyevent KEYCODE_MOVE_END"],
            capture_output=True, text=True,
        )
        # Multiple backspaces to clear
        for _ in range(min(100, 50)):
            subprocess.run(
                hdc_prefix + ["shell", "input keyevent 67"],
                capture_output=True, text=True,
            )


def set_clipboard_text(text: str, device_id: str | None = None) -> None:
    """Set clipboard text on HarmonyOS device."""
    import base64

    hdc_prefix = build_hdc_command(device_id)

    with trace_span("hdc.set_clipboard", attrs={"device_id": device_id, "text_length": len(text)}):
        encoded_text = base64.b64encode(text.encode("utf-8")).decode("utf-8")
        subprocess.run(
            hdc_prefix + [
                "shell", "am", "broadcast", "-a", "ADB_SET_CLIPBOARD",
                "--es", "msg", encoded_text,
            ],
            capture_output=True, text=True,
        )


def get_clipboard_text(device_id: str | None = None) -> str:
    """Get clipboard text from HarmonyOS device."""
    hdc_prefix = build_hdc_command(device_id)

    with trace_span("hdc.get_clipboard", attrs={"device_id": device_id}):
        try:
            result = subprocess.run(
                hdc_prefix + [
                    "shell", "content", "query",
                    "--uri", "content://clipboard",
                ],
                capture_output=True, text=True, timeout=5,
            )
            text = result.stdout.strip()
            if text.startswith("text="):
                text = text[5:]
            return text
        except Exception as e:
            logger.warning(f"Failed to get clipboard text: {e}")
            return ""


def paste_text(device_id: str | None = None) -> None:
    """Trigger paste via keyevent 279."""
    hdc_prefix = build_hdc_command(device_id)

    with trace_span("hdc.paste", attrs={"device_id": device_id}):
        subprocess.run(
            hdc_prefix + ["shell", "input keyevent 279"],
            capture_output=True, text=True,
        )


def select_all_text(device_id: str | None = None) -> None:
    """Trigger select-all via keyevent 295."""
    hdc_prefix = build_hdc_command(device_id)

    with trace_span("hdc.select_all", attrs={"device_id": device_id}):
        subprocess.run(
            hdc_prefix + ["shell", "input keyevent 295"],
            capture_output=True, text=True,
        )
