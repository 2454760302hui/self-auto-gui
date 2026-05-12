"""Input utilities for Android device text input."""

import base64
import subprocess
import urllib.parse

from AutoGLM_GUI.platform_utils import build_adb_command
from AutoGLM_GUI.logger import logger
from AutoGLM_GUI.trace import trace_span


def _is_adbkeyboard_active(device_id: str | None = None) -> bool:
    """Check if ADBKeyBoard is the current active IME."""
    adb_prefix = build_adb_command(device_id)
    result = subprocess.run(
        adb_prefix + ["shell", "settings", "get", "secure", "default_input_method"],
        capture_output=True, text=True,
    )
    return "com.android.adbkeyboard" in (result.stdout + result.stderr)


def type_text(text: str, device_id: str | None = None) -> None:
    adb_prefix = build_adb_command(device_id)

    with trace_span(
        "adb.type_text",
        attrs={"device_id": device_id, "text_length": len(text)},
    ):
        if _is_adbkeyboard_active(device_id):
            # Preferred: ADBKeyBoard broadcast (supports Unicode/CJK)
            encoded_text = base64.b64encode(text.encode("utf-8")).decode("utf-8")
            subprocess.run(
                adb_prefix
                + [
                    "shell", "am", "broadcast", "-a", "ADB_INPUT_B64",
                    "--es", "msg", encoded_text,
                ],
                capture_output=True, text=True,
            )
        else:
            # Fallback: adb shell input text (limited charset)
            encoded = urllib.parse.quote(text, safe="")
            subprocess.run(
                adb_prefix + ["shell", "input", "text", encoded],
                capture_output=True, text=True,
            )


def clear_text(device_id: str | None = None) -> None:
    adb_prefix = build_adb_command(device_id)

    with trace_span("adb.clear_text", attrs={"device_id": device_id}):
        if _is_adbkeyboard_active(device_id):
            subprocess.run(
                adb_prefix + ["shell", "am", "broadcast", "-a", "ADB_CLEAR_TEXT"],
                capture_output=True, text=True,
            )
        else:
            # Fallback: select all + delete via keyevents
            subprocess.run(
                adb_prefix + ["shell", "input", "keyevent", "67"],
                capture_output=True, text=True,
            )


def detect_and_set_adb_keyboard(device_id: str | None = None) -> str:
    adb_prefix = build_adb_command(device_id)

    with trace_span(
        "adb.detect_adb_keyboard",
        attrs={"device_id": device_id},
    ):
        result = subprocess.run(
            adb_prefix + ["shell", "settings", "get", "secure", "default_input_method"],
            capture_output=True,
            text=True,
        )
    current_ime = (result.stdout + result.stderr).strip()

    if "com.android.adbkeyboard/.AdbIME" not in current_ime:
        with trace_span(
            "adb.set_adb_keyboard",
            attrs={"device_id": device_id},
        ):
            subprocess.run(
                adb_prefix + ["shell", "ime", "set", "com.android.adbkeyboard/.AdbIME"],
                capture_output=True,
                text=True,
            )

    type_text("", device_id)

    return current_ime


def restore_keyboard(ime: str, device_id: str | None = None) -> None:
    adb_prefix = build_adb_command(device_id)

    with trace_span(
        "adb.restore_keyboard",
        attrs={"device_id": device_id},
    ):
        subprocess.run(
            adb_prefix + ["shell", "ime", "set", ime], capture_output=True, text=True
        )


def set_clipboard_text(text: str, device_id: str | None = None) -> None:
    """Set clipboard text on device."""
    adb_prefix = build_adb_command(device_id)

    with trace_span("adb.set_clipboard", attrs={"device_id": device_id, "text_length": len(text)}):
        if _is_adbkeyboard_active(device_id):
            encoded_text = base64.b64encode(text.encode("utf-8")).decode("utf-8")
            subprocess.run(
                adb_prefix + [
                    "shell", "am", "broadcast", "-a", "ADB_SET_CLIPBOARD",
                    "--es", "msg", encoded_text,
                ],
                capture_output=True, text=True,
            )
        else:
            # Fallback: use content provider
            encoded = urllib.parse.quote(text, safe="")
            subprocess.run(
                adb_prefix + [
                    "shell", "content", "call",
                    "--uri", "content://clipboard",
                    "--method", "setClipboardText",
                    "--arg", encoded,
                ],
                capture_output=True, text=True,
            )


def get_clipboard_text(device_id: str | None = None) -> str:
    """Get clipboard text from device. Returns empty string if unavailable."""
    adb_prefix = build_adb_command(device_id)

    with trace_span("adb.get_clipboard", attrs={"device_id": device_id}):
        try:
            result = subprocess.run(
                adb_prefix + [
                    "shell", "content", "query",
                    "--uri", "content://clipboard",
                ],
                capture_output=True, text=True, timeout=5,
            )
            text = result.stdout.strip()
            # Remove any column name prefix from content query output
            if text.startswith("text="):
                text = text[5:]
            return text
        except Exception as e:
            logger.warning(f"Failed to get clipboard text: {e}")
            return ""


def paste_text(device_id: str | None = None) -> None:
    """Trigger paste action via keyevent."""
    adb_prefix = build_adb_command(device_id)

    with trace_span("adb.paste", attrs={"device_id": device_id}):
        subprocess.run(
            adb_prefix + ["shell", "input", "keyevent", "279"],
            capture_output=True, text=True,
        )


def select_all_text(device_id: str | None = None) -> None:
    """Trigger select-all via keyevent."""
    adb_prefix = build_adb_command(device_id)

    with trace_span("adb.select_all", attrs={"device_id": device_id}):
        subprocess.run(
            adb_prefix + ["shell", "input", "keyevent", "295"],
            capture_output=True, text=True,
        )
