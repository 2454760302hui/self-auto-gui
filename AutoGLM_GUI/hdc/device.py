"""HarmonyOS device control operations via hdc shell."""

import subprocess

from AutoGLM_GUI.hdc.connection import build_hdc_command
from AutoGLM_GUI.adb.timing import TIMING_CONFIG
from AutoGLM_GUI.trace import trace_sleep, trace_span


def tap(x: int, y: int, device_id: str | None = None, delay: float | None = None) -> None:
    if delay is None:
        delay = TIMING_CONFIG.device.default_tap_delay

    hdc_prefix = build_hdc_command(device_id)
    with trace_span("hdc.tap", attrs={"device_id": device_id, "x": x, "y": y}):
        subprocess.run(
            hdc_prefix + ["shell", f"input tap {x} {y}"],
            capture_output=True, text=True,
        )
    trace_sleep(delay, name="sleep.device_tap_delay", attrs={"device_id": device_id})


def double_tap(x: int, y: int, device_id: str | None = None, delay: float | None = None) -> None:
    if delay is None:
        delay = TIMING_CONFIG.device.default_double_tap_delay

    hdc_prefix = build_hdc_command(device_id)
    with trace_span("hdc.double_tap", attrs={"device_id": device_id, "x": x, "y": y}):
        subprocess.run(
            hdc_prefix + ["shell", f"input tap {x} {y}"],
            capture_output=True, text=True,
        )
        trace_sleep(
            TIMING_CONFIG.device.double_tap_interval,
            name="sleep.device_double_tap_interval",
        )
        subprocess.run(
            hdc_prefix + ["shell", f"input tap {x} {y}"],
            capture_output=True, text=True,
        )
    trace_sleep(delay, name="sleep.device_double_tap_delay")


def long_press(
    x: int, y: int, duration_ms: int = 3000, device_id: str | None = None, delay: float | None = None,
) -> None:
    if delay is None:
        delay = TIMING_CONFIG.device.default_long_press_delay

    hdc_prefix = build_hdc_command(device_id)
    with trace_span("hdc.long_press", attrs={"device_id": device_id, "x": x, "y": y, "duration_ms": duration_ms}):
        subprocess.run(
            hdc_prefix + ["shell", f"input swipe {x} {y} {x} {y} {duration_ms}"],
            capture_output=True, text=True,
        )
    trace_sleep(delay, name="sleep.device_long_press_delay")


def swipe(
    start_x: int, start_y: int, end_x: int, end_y: int,
    duration_ms: int | None = None, device_id: str | None = None, delay: float | None = None,
) -> None:
    if delay is None:
        delay = TIMING_CONFIG.device.default_swipe_delay

    if duration_ms is None:
        dist_sq = (start_x - end_x) ** 2 + (start_y - end_y) ** 2
        duration_ms = max(1000, min(int(dist_sq / 1000), 2000))

    hdc_prefix = build_hdc_command(device_id)
    with trace_span("hdc.swipe", attrs={"device_id": device_id, "start_x": start_x, "start_y": start_y, "end_x": end_x, "end_y": end_y}):
        subprocess.run(
            hdc_prefix + ["shell", f"input swipe {start_x} {start_y} {end_x} {end_y} {duration_ms}"],
            capture_output=True, text=True,
        )
    trace_sleep(delay, name="sleep.device_swipe_delay")


def back(device_id: str | None = None, delay: float | None = None) -> None:
    if delay is None:
        delay = TIMING_CONFIG.device.default_back_delay

    hdc_prefix = build_hdc_command(device_id)
    with trace_span("hdc.back", attrs={"device_id": device_id}):
        subprocess.run(
            hdc_prefix + ["shell", "input keyevent 4"],
            capture_output=True, text=True,
        )
    trace_sleep(delay, name="sleep.device_back_delay")


def home(device_id: str | None = None, delay: float | None = None) -> None:
    if delay is None:
        delay = TIMING_CONFIG.device.default_home_delay

    hdc_prefix = build_hdc_command(device_id)
    with trace_span("hdc.home", attrs={"device_id": device_id}):
        subprocess.run(
            hdc_prefix + ["shell", "input keyevent KEYCODE_HOME"],
            capture_output=True, text=True,
        )
    trace_sleep(delay, name="sleep.device_home_delay")


def launch_app(app_name: str, device_id: str | None = None, delay: float | None = None) -> bool:
    """Launch an app on HarmonyOS. For now returns False as app bundle mapping differs."""
    if delay is None:
        delay = TIMING_CONFIG.device.default_launch_delay

    hdc_prefix = build_hdc_command(device_id)
    # HarmonyOS uses `aa start` with ability name and bundle name
    with trace_span("hdc.launch_app", attrs={"device_id": device_id, "app_name": app_name}):
        result = subprocess.run(
            hdc_prefix + ["shell", f"aa start -a EntryAbility -b {app_name}"],
            capture_output=True, text=True,
        )
    trace_sleep(delay, name="sleep.device_launch_delay")
    return result.returncode == 0


def get_current_app(device_id: str | None = None) -> str:
    """Get the currently focused app on HarmonyOS."""
    hdc_prefix = build_hdc_command(device_id)
    with trace_span("hdc.get_current_app", attrs={"device_id": device_id}):
        result = subprocess.run(
            hdc_prefix + ["shell", "aa dump -l"],
            capture_output=True, text=True,
        )
    output = result.stdout
    if not output:
        return "System Home"
    # Parse the output for the top ability
    for line in output.splitlines():
        line = line.strip()
        if "#" in line and "ability" in line.lower():
            return line.split("#")[0].strip()
    return "System Home"


def paste(device_id: str | None = None, delay: float | None = None) -> None:
    """Trigger paste via keyevent 279."""
    if delay is None:
        delay = TIMING_CONFIG.device.default_tap_delay

    hdc_prefix = build_hdc_command(device_id)
    with trace_span("hdc.paste", attrs={"device_id": device_id}):
        subprocess.run(
            hdc_prefix + ["shell", "input keyevent 279"],
            capture_output=True, text=True,
        )
    trace_sleep(delay, name="sleep.device_paste_delay", attrs={"device_id": device_id})


def select_all(device_id: str | None = None, delay: float | None = None) -> None:
    """Trigger select-all via keyevent 295."""
    if delay is None:
        delay = TIMING_CONFIG.device.default_tap_delay

    hdc_prefix = build_hdc_command(device_id)
    with trace_span("hdc.select_all", attrs={"device_id": device_id}):
        subprocess.run(
            hdc_prefix + ["shell", "input keyevent 295"],
            capture_output=True, text=True,
        )
    trace_sleep(delay, name="sleep.device_select_all_delay", attrs={"device_id": device_id})
