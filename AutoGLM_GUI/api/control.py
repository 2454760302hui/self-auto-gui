"""Device control routes (tap/swipe/touch/keyevent/text/clipboard/ui-dump/apps/pytest/yaml/gif/record)."""

import asyncio
import base64
import io
import os
import subprocess
import tempfile
import time
from typing import List

from pydantic import BaseModel
from fastapi import APIRouter

from AutoGLM_GUI.device_manager import DeviceManager
from AutoGLM_GUI.devices.adb_device import ADBDevice
from AutoGLM_GUI.platform_utils import build_adb_command
from AutoGLM_GUI.schemas import (
    BackRequest,
    BackResponse,
    ClearTextRequest,
    ClearTextResponse,
    ClipboardGetRequest,
    ClipboardGetResponse,
    ClipboardSetRequest,
    ClipboardSetResponse,
    CurrentAppRequest,
    CurrentAppResponse,
    DoubleTapRequest,
    DoubleTapResponse,
    ForceStopRequest,
    ForceStopResponse,
    GifGenerateRequest,
    GifGenerateResponse,
    RecentAppsRequest,
    RecentAppsResponse,
    AppStateRequest,
    AppStateResponse,
    UninstallRequest,
    UninstallResponse,
    HomeRequest,
    HomeResponse,
    InstalledAppsRequest,
    InstalledAppsResponse,
    InstalledAppInfo,
    KeyEventRequest,
    KeyEventResponse,
    LaunchRequest,
    LaunchResponse,
    LongPressRequest,
    LongPressResponse,
    PasteRequest,
    PasteResponse,
    PytestRunRequest,
    PytestRunResponse,
    ScreenshotControlRequest,
    ScreenshotControlResponse,
    ScrollRequest,
    ScrollResponse,
    SelectAllRequest,
    SelectAllResponse,
    SwipeRequest,
    SwipeResponse,
    TapRequest,
    TapResponse,
    TextInputRequest,
    TextInputResponse,
    TouchDownRequest,
    TouchDownResponse,
    TouchMoveRequest,
    TouchMoveResponse,
    TouchUpRequest,
    TouchUpResponse,
    UiDumpRequest,
    UiDumpResponse,
    YamlRunRequest,
    YamlRunResponse,
    RecordStartRequest,
    RecordStartResponse,
    RecordStopRequest,
    RecordStopResponse,
)
from AutoGLM_GUI.types import DeviceConnectionType

router = APIRouter()

# Global recording state
_recording_state: dict[str, dict] = {}  # device_id -> {actions, screenshots, start_time}


@router.post("/api/control/tap", response_model=TapResponse)
async def control_tap(request: TapRequest) -> TapResponse:
    """Execute tap at specified device coordinates."""
    try:
        if not request.device_id:
            return TapResponse(success=False, error="device_id is required")

        device_manager = DeviceManager.get_instance()
        device = device_manager.get_device_protocol(request.device_id)
        await asyncio.to_thread(
            device.tap,
            x=request.x,
            y=request.y,
            delay=request.delay,
        )

        return TapResponse(success=True)
    except Exception as e:
        return TapResponse(success=False, error=str(e))


@router.post("/api/control/keyevent", response_model=KeyEventResponse)
async def control_keyevent(request: KeyEventRequest) -> KeyEventResponse:
    """Send a key event to the device."""
    try:
        if not request.device_id:
            return KeyEventResponse(success=False, error="device_id is required")

        device_manager = DeviceManager.get_instance()
        managed = device_manager.get_device_by_device_id(request.device_id)
        if not managed:
            return KeyEventResponse(success=False, error="device not found")

        if managed.connection_type == DeviceConnectionType.HDC:
            from AutoGLM_GUI.hdc.connection import build_hdc_command
            hdc_prefix = build_hdc_command(request.device_id)
            def _send_keyevent():
                subprocess.run(
                    hdc_prefix + ["shell", "input", "keyevent", str(request.keycode)],
                    capture_output=True,
                    text=True,
                )
            await asyncio.to_thread(_send_keyevent)
        else:
            adb_prefix = build_adb_command(request.device_id)
            def _send_keyevent():
                subprocess.run(
                    adb_prefix + ["shell", "input", "keyevent", str(request.keycode)],
                    capture_output=True,
                    text=True,
                )
            await asyncio.to_thread(_send_keyevent)
        return KeyEventResponse(success=True)
    except Exception as e:
        return KeyEventResponse(success=False, error=str(e))


@router.post("/api/control/text", response_model=TextInputResponse)
async def control_text(request: TextInputRequest) -> TextInputResponse:
    """Send text input to the device."""
    try:
        if not request.device_id:
            return TextInputResponse(success=False, error="device_id is required")

        device_manager = DeviceManager.get_instance()
        device = device_manager.get_device_protocol(request.device_id)

        def _send_text():
            device.type_text(request.text)

        await asyncio.to_thread(_send_text)
        return TextInputResponse(success=True)
    except Exception as e:
        return TextInputResponse(success=False, error=str(e))


@router.post("/api/control/swipe", response_model=SwipeResponse)
async def control_swipe(request: SwipeRequest) -> SwipeResponse:
    """Execute swipe from start to end coordinates."""
    try:
        if not request.device_id:
            return SwipeResponse(success=False, error="device_id is required")

        device_manager = DeviceManager.get_instance()
        device = device_manager.get_device_protocol(request.device_id)
        await asyncio.to_thread(
            device.swipe,
            start_x=request.start_x,
            start_y=request.start_y,
            end_x=request.end_x,
            end_y=request.end_y,
            duration_ms=request.duration_ms,
            delay=request.delay,
        )

        return SwipeResponse(success=True)
    except Exception as e:
        return SwipeResponse(success=False, error=str(e))


@router.post("/api/control/touch/down", response_model=TouchDownResponse)
async def control_touch_down(request: TouchDownRequest) -> TouchDownResponse:
    """Send touch DOWN event at specified device coordinates."""
    try:
        from AutoGLM_GUI.adb_plus import touch_down_async

        await touch_down_async(
            x=request.x,
            y=request.y,
            device_id=request.device_id,
            delay=request.delay,
        )

        return TouchDownResponse(success=True)
    except Exception as e:
        return TouchDownResponse(success=False, error=str(e))


@router.post("/api/control/touch/move", response_model=TouchMoveResponse)
async def control_touch_move(request: TouchMoveRequest) -> TouchMoveResponse:
    """Send touch MOVE event at specified device coordinates."""
    try:
        from AutoGLM_GUI.adb_plus import touch_move_async

        await touch_move_async(
            x=request.x,
            y=request.y,
            device_id=request.device_id,
            delay=request.delay,
        )

        return TouchMoveResponse(success=True)
    except Exception as e:
        return TouchMoveResponse(success=False, error=str(e))


@router.post("/api/control/touch/up", response_model=TouchUpResponse)
async def control_touch_up(request: TouchUpRequest) -> TouchUpResponse:
    """Send touch UP event at specified device coordinates."""
    try:
        from AutoGLM_GUI.adb_plus import touch_up_async

        await touch_up_async(
            x=request.x,
            y=request.y,
            device_id=request.device_id,
            delay=request.delay,
        )

        return TouchUpResponse(success=True)
    except Exception as e:
        return TouchUpResponse(success=False, error=str(e))


# ─── Direct Device Control Endpoints ────────────────────────────────────


def _get_device(device_id: str | None):
    """Resolve device from device_id, raising ValueError if missing."""
    if not device_id:
        raise ValueError("device_id is required")
    return DeviceManager.get_instance().get_device_protocol(device_id)


@router.post("/api/control/back", response_model=BackResponse)
async def control_back(request: BackRequest) -> BackResponse:
    try:
        device = _get_device(request.device_id)
        await asyncio.to_thread(device.back, delay=request.delay)
        return BackResponse(success=True)
    except Exception as e:
        return BackResponse(success=False, error=str(e))


@router.post("/api/control/home", response_model=HomeResponse)
async def control_home(request: HomeRequest) -> HomeResponse:
    try:
        device = _get_device(request.device_id)
        await asyncio.to_thread(device.home, delay=request.delay)
        return HomeResponse(success=True)
    except Exception as e:
        return HomeResponse(success=False, error=str(e))


@router.post("/api/control/launch", response_model=LaunchResponse)
async def control_launch(request: LaunchRequest) -> LaunchResponse:
    try:
        device = _get_device(request.device_id)
        ok = await asyncio.to_thread(device.launch_app, request.app, delay=request.delay)
        if not ok:
            return LaunchResponse(success=False, error=f"App not found: {request.app}")
        return LaunchResponse(success=True)
    except Exception as e:
        return LaunchResponse(success=False, error=str(e))


@router.post("/api/control/double-tap", response_model=DoubleTapResponse)
async def control_double_tap(request: DoubleTapRequest) -> DoubleTapResponse:
    try:
        device = _get_device(request.device_id)
        await asyncio.to_thread(device.double_tap, request.x, request.y, delay=request.delay)
        return DoubleTapResponse(success=True)
    except Exception as e:
        return DoubleTapResponse(success=False, error=str(e))


@router.post("/api/control/long-press", response_model=LongPressResponse)
async def control_long_press(request: LongPressRequest) -> LongPressResponse:
    try:
        device = _get_device(request.device_id)
        await asyncio.to_thread(
            device.long_press, request.x, request.y,
            duration_ms=request.duration_ms, delay=request.delay,
        )
        return LongPressResponse(success=True)
    except Exception as e:
        return LongPressResponse(success=False, error=str(e))


@router.post("/api/control/clear", response_model=ClearTextResponse)
async def control_clear_text(request: ClearTextRequest) -> ClearTextResponse:
    try:
        device = _get_device(request.device_id)
        await asyncio.to_thread(device.clear_text)
        return ClearTextResponse(success=True)
    except Exception as e:
        return ClearTextResponse(success=False, error=str(e))


@router.post("/api/control/scroll", response_model=ScrollResponse)
async def control_scroll(request: ScrollRequest) -> ScrollResponse:
    try:
        device = _get_device(request.device_id)

        # Get screenshot to determine screen dimensions
        screenshot = await asyncio.to_thread(device.get_screenshot)
        w, h = screenshot.width, screenshot.height
        cx, cy = w // 2, h // 2
        d = request.distance

        direction_map = {
            "up":    (cx, cy + d // 2, cx, cy - d // 2),
            "down":  (cx, cy - d // 2, cx, cy + d // 2),
            "left":  (cx + d // 2, cy, cx - d // 2, cy),
            "right": (cx - d // 2, cy, cx + d // 2, cy),
        }
        sx, sy, ex, ey = direction_map[request.direction]

        await asyncio.to_thread(device.swipe, sx, sy, ex, ey, delay=request.delay)
        return ScrollResponse(success=True)
    except Exception as e:
        return ScrollResponse(success=False, error=str(e))


@router.post("/api/control/screenshot", response_model=ScreenshotControlResponse)
async def control_screenshot(request: ScreenshotControlRequest) -> ScreenshotControlResponse:
    try:
        device = _get_device(request.device_id)
        screenshot = await asyncio.to_thread(device.get_screenshot)
        return ScreenshotControlResponse(
            success=True,
            image=screenshot.base64_data,
            width=screenshot.width,
            height=screenshot.height,
        )
    except Exception as e:
        return ScreenshotControlResponse(success=False, error=str(e))


@router.post("/api/control/ui-dump", response_model=UiDumpResponse)
async def control_ui_dump(request: UiDumpRequest) -> UiDumpResponse:
    try:
        device = _get_device(request.device_id)

        from AutoGLM_GUI.accessibility import dump_ui_hierarchy

        elements = await asyncio.to_thread(dump_ui_hierarchy, device.device_id)
        element_list = []
        for el in elements:
            item = {
                "text": el.text,
                "content_desc": el.content_desc,
                "resource_id": el.resource_id,
                "class_name": el.class_name,
                "clickable": el.clickable,
                "bounds": list(el.bounds),
                "center": list(el.center),
                "package": el.package,
            }
            element_list.append(item)

        return UiDumpResponse(success=True, elements=element_list)
    except Exception as e:
        return UiDumpResponse(success=False, error=str(e))


@router.post("/api/control/current-app", response_model=CurrentAppResponse)
async def control_current_app(request: CurrentAppRequest) -> CurrentAppResponse:
    try:
        device = _get_device(request.device_id)
        app_name = await asyncio.to_thread(device.get_current_app)
        return CurrentAppResponse(success=True, app_name=app_name)
    except Exception as e:
        return CurrentAppResponse(success=False, error=str(e))


@router.post("/api/control/clipboard/set", response_model=ClipboardSetResponse)
async def control_clipboard_set(request: ClipboardSetRequest) -> ClipboardSetResponse:
    try:
        device = _get_device(request.device_id)
        await asyncio.to_thread(device.set_clipboard, request.text)
        return ClipboardSetResponse(success=True)
    except Exception as e:
        return ClipboardSetResponse(success=False, error=str(e))


@router.post("/api/control/clipboard/get", response_model=ClipboardGetResponse)
async def control_clipboard_get(request: ClipboardGetRequest) -> ClipboardGetResponse:
    try:
        device = _get_device(request.device_id)
        text = await asyncio.to_thread(device.get_clipboard)
        return ClipboardGetResponse(success=True, text=text)
    except Exception as e:
        return ClipboardGetResponse(success=False, error=str(e))


@router.post("/api/control/paste", response_model=PasteResponse)
async def control_paste(request: PasteRequest) -> PasteResponse:
    try:
        device = _get_device(request.device_id)
        await asyncio.to_thread(device.paste, delay=request.delay)
        return PasteResponse(success=True)
    except Exception as e:
        return PasteResponse(success=False, error=str(e))


@router.post("/api/control/select-all", response_model=SelectAllResponse)
async def control_select_all(request: SelectAllRequest) -> SelectAllResponse:
    try:
        device = _get_device(request.device_id)
        await asyncio.to_thread(device.select_all, delay=request.delay)
        return SelectAllResponse(success=True)
    except Exception as e:
        return SelectAllResponse(success=False, error=str(e))


@router.post("/api/control/apps", response_model=InstalledAppsResponse)
async def control_installed_apps(request: InstalledAppsRequest) -> InstalledAppsResponse:
    """List installed apps on device, separated into system and third-party."""
    try:
        if not request.device_id:
            return InstalledAppsResponse(success=False, error="device_id is required")

        managed = DeviceManager.get_instance().get_device_by_device_id(request.device_id)
        if not managed:
            return InstalledAppsResponse(success=False, error="device not found")

        if managed.connection_type == DeviceConnectionType.HDC:
            from AutoGLM_GUI.hdc.apps import list_installed_packages
            raw = await asyncio.to_thread(list_installed_packages, request.device_id)
        else:
            from AutoGLM_GUI.adb.apps import list_installed_packages, get_app_name as _get_app_name
            raw = await asyncio.to_thread(list_installed_packages, request.device_id)
            _get_app_name_ref = _get_app_name

        def _make_info(pkg: str) -> InstalledAppInfo:
            from AutoGLM_GUI.adb.apps import get_app_name as _gan
            name = _gan(pkg)
            return InstalledAppInfo(package_name=pkg, app_name=name)

        system = await asyncio.to_thread(lambda: [_make_info(p) for p in raw.get("system", [])])
        third_party = await asyncio.to_thread(lambda: [_make_info(p) for p in raw.get("third_party", [])])

        return InstalledAppsResponse(success=True, system=system, third_party=third_party)
    except Exception as e:
        return InstalledAppsResponse(success=False, error=str(e))


@router.post("/api/control/force-stop", response_model=ForceStopResponse)
async def control_force_stop(request: ForceStopRequest) -> ForceStopResponse:
    """Force stop (kill) an application by package name."""
    try:
        managed = DeviceManager.get_instance().get_device_by_device_id(request.device_id)
        if not managed:
            return ForceStopResponse(success=False, error="device not found")

        if managed.connection_type.name == "HDC":
            from AutoGLM_GUI.hdc.connection import build_hdc_command
            cmd_base = build_hdc_command(request.device_id)
            result = subprocess.run(
                cmd_base + ["shell", "aa", "force-stop", request.package],
                capture_output=True, text=True,
            )
        else:
            cmd_base = build_adb_command(request.device_id)
            subprocess.run(
                cmd_base + ["shell", "am", "force-stop", request.package],
                capture_output=True, text=True,
            )

        return ForceStopResponse(success=True)
    except Exception as e:
        return ForceStopResponse(success=False, error=str(e))


@router.post("/api/control/app-state", response_model=AppStateResponse)
async def control_app_state(request: AppStateRequest) -> AppStateResponse:
    """Check if a package is currently running / in foreground."""
    try:
        managed = DeviceManager.get_instance().get_device_by_device_id(request.device_id)
        if not managed:
            return AppStateResponse(success=False, error="device not found")

        # Get current foreground app
        try:
            device = managed.get_proxy()
            current = device.get_current_app() if hasattr(device, 'get_current_app') else ""
        except Exception:
            current = ""

        # Also check via dumpsys for HDC
        running = current == request.package

        if not running and managed.connection_type.name != "HDC":
            cmd_base = build_adb_command(request.device_id)
            result = subprocess.run(
                cmd_base + ["shell", "dumpsys", "activity", "activities"],
                capture_output=True, text=True,
            )
            # Look for the package in foreground activity stack
            running = request.package in result.stdout and "mResumedActivity" in result.stdout

        return AppStateResponse(success=True, running=running)
    except Exception as e:
        return AppStateResponse(success=False, error=str(e))


@router.post("/api/control/uninstall", response_model=UninstallResponse)
async def control_uninstall(request: UninstallRequest) -> UninstallResponse:
    """Uninstall a package (third-party only)."""
    try:
        managed = DeviceManager.get_instance().get_device_by_device_id(request.device_id)
        if not managed:
            return UninstallResponse(success=False, error="device not found")

        if managed.connection_type.name == "HDC":
            cmd_base = build_hdc_command(request.device_id)
            subprocess.run(
                cmd_base + ["shell", "bm", "uninstall", request.package],
                capture_output=True, text=True,
            )
        else:
            cmd_base = build_adb_command(request.device_id)
            # Use -k to keep data so it's faster
            subprocess.run(
                cmd_base + ["uninstall", request.package],
                capture_output=True, text=True,
            )

        return UninstallResponse(success=True)
    except Exception as e:
        return UninstallResponse(success=False, error=str(e))


@router.post("/api/control/recent-apps", response_model=RecentAppsResponse)
async def control_recent_apps(request: RecentAppsRequest) -> RecentAppsResponse:
    """Get recently used apps from the recents screen."""
    try:
        managed = DeviceManager.get_instance().get_device_by_device_id(request.device_id)
        if not managed:
            return RecentAppsResponse(success=False, error="device not found")

        if managed.connection_type.name == "HDC":
            from AutoGLM_GUI.hdc.connection import build_hdc_command
            cmd_base = build_hdc_command(request.device_id)
            result = subprocess.run(
                cmd_base + ["shell", "hidumper", "-s", "WindowManagerService", "-a"],
                capture_output=True, text=True,
            )
        else:
            cmd_base = build_adb_command(request.device_id)
            result = subprocess.run(
                cmd_base + ["shell", "dumpsys", "activity", "recents"],
                capture_output=True, text=True,
            )

        import re
        # Extract package names from output
        packages = re.findall(r'([a-z][a-z0-9._]+(?:\.[a-z][a-z0-9._]*)+)', result.stdout)
        # Deduplicate and filter common system packages
        system_blacklist = {"android", "com.android.systemui", "com.android.launcher",
                            "com.huawei.systemmanager", "com.huawei.android.launcher",
                            "com.android.launcher", "com.miui.home", "com.coloros.safecenter"}
        seen = set()
        recent = []
        for pkg in packages:
            if pkg not in system_blacklist and pkg not in seen:
                seen.add(pkg)
                recent.append(pkg)
        return RecentAppsResponse(success=True, packages=recent[:20])
    except Exception as e:
        return RecentAppsResponse(success=False, error=str(e))


@router.post("/api/control/pytest/run", response_model=PytestRunResponse)
async def control_pytest_run(request: PytestRunRequest) -> PytestRunResponse:
    """Run pytest code and return the output."""
    try:
        tmpdir = tempfile.mkdtemp(prefix="autoglm_pytest_")
        filepath = os.path.join(tmpdir, request.filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(request.code)

        def _run_pytest():
            return subprocess.run(
                ["python", filepath],
                capture_output=True,
                text=True,
                timeout=120,
            )

        result = await asyncio.to_thread(_run_pytest)

        output = result.stdout + result.stderr
        try:
            os.remove(filepath)
            os.rmdir(tmpdir)
        except OSError:
            pass

        return PytestRunResponse(
            success=result.returncode == 0,
            output=output,
        )
    except subprocess.TimeoutExpired:
        return PytestRunResponse(success=False, output="Test timed out after 120 seconds", error="timeout")
    except Exception as e:
        return PytestRunResponse(success=False, error=str(e))


@router.post("/api/control/yaml/run", response_model=YamlRunResponse)
async def control_yaml_run(request: YamlRunRequest) -> YamlRunResponse:
    """Run YAML test script and return the output."""
    try:
        tmpdir = tempfile.mkdtemp(prefix="autoglm_yaml_")
        yaml_path = os.path.join(tmpdir, request.filename)
        py_path = os.path.join(tmpdir, "run_yaml_test.py")

        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write(request.code)

        # Generate a pytest wrapper that loads and runs the YAML
        wrapper_lines = [
            '"""Auto-generated wrapper to run YAML test."""',
            'import yaml',
            'import subprocess',
            'import time',
            '',
            'def load_yaml(path):',
            '    with open(path, "r", encoding="utf-8") as f:',
            '        return yaml.safe_load(f)',
            '',
            'def adb_shell(cmd, device_id=None):',
            '    prefix = ["adb"]',
            '    if device_id:',
            '        prefix += ["-s", device_id]',
            '    prefix += ["shell", cmd]',
            '    subprocess.run(prefix, check=True, capture_output=True, text=True)',
            '',
            'def execute_step(step, device_id=None):',
            '    action = step.get("action", "")',
            '    if action == "tap":',
            '        adb_shell("input tap " + str(step["x"]) + " " + str(step["y"]), device_id)',
            '    elif action == "swipe":',
            '        dur = step.get("duration", 300)',
            '        adb_shell("input swipe " + str(step["start_x"]) + " " + str(step["start_y"]) + " " + str(step["end_x"]) + " " + str(step["end_y"]) + " " + str(dur), device_id)',
            '    elif action == "double_tap":',
            '        adb_shell("input tap " + str(step["x"]) + " " + str(step["y"]), device_id)',
            '        time.sleep(0.1)',
            '        adb_shell("input tap " + str(step["x"]) + " " + str(step["y"]), device_id)',
            '    elif action == "long_press":',
            '        dur = step.get("duration", 3000)',
            '        adb_shell("input swipe " + str(step["x"]) + " " + str(step["y"]) + " " + str(step["x"]) + " " + str(step["y"]) + " " + str(dur), device_id)',
            '    elif action == "input_text":',
            '        text = step.get("text", "").replace(" ", "%s")',
            '        adb_shell(\'input text "\' + text + \'"\'  , device_id)',
            '    elif action == "keyevent":',
            '        adb_shell("input keyevent " + str(step["keycode"]), device_id)',
            '    elif action == "launch":',
            '        adb_shell("monkey -p " + step["package"] + " -c android.intent.category.LAUNCHER 1", device_id)',
            '    elif action == "back":',
            '        adb_shell("input keyevent 4", device_id)',
            '    elif action == "home":',
            '        adb_shell("input keyevent 3", device_id)',
            '    elif action == "scroll_up":',
            '        adb_shell("input swipe 540 1500 540 500 300", device_id)',
            '    elif action == "scroll_down":',
            '        adb_shell("input swipe 540 500 540 1500 300", device_id)',
            '    elif action == "scroll_left":',
            '        adb_shell("input swipe 900 1200 180 1200 300", device_id)',
            '    elif action == "scroll_right":',
            '        adb_shell("input swipe 180 1200 900 1200 300", device_id)',
            '    elif action == "sleep":',
            '        time.sleep(step.get("duration", 1))',
            '    else:',
            '        print("Unknown action: " + action)',
            '    time.sleep(step.get("delay", 1))',
            '',
            'def test_yaml_flow():',
            f'    data = load_yaml(r"{yaml_path}")',
            '    device_id = data.get("device_id")',
            '    steps = data.get("steps", [])',
            '    print("Running " + str(len(steps)) + " steps from YAML...")',
            '    for i, step in enumerate(steps):',
            '        print("  Step " + str(i+1) + ": " + step.get("action", "unknown"))',
            '        execute_step(step, device_id)',
            '    print("All steps completed.")',
            '',
            'if __name__ == "__main__":',
            '    test_yaml_flow()',
        ]
        wrapper_code = "\n".join(wrapper_lines)
        with open(py_path, "w", encoding="utf-8") as f:
            f.write(wrapper_code)

        def _run_yaml_pytest():
            return subprocess.run(
                ["python", py_path],
                capture_output=True,
                text=True,
                timeout=120,
            )

        result = await asyncio.to_thread(_run_yaml_pytest)

        output = result.stdout + result.stderr
        try:
            os.remove(yaml_path)
            os.remove(py_path)
            os.rmdir(tmpdir)
        except OSError:
            pass

        return YamlRunResponse(
            success=result.returncode == 0,
            output=output,
        )
    except subprocess.TimeoutExpired:
        return YamlRunResponse(success=False, output="YAML test timed out after 60 seconds", error="timeout")
    except Exception as e:
        return YamlRunResponse(success=False, error=str(e))


@router.post("/api/control/gif/generate", response_model=GifGenerateResponse)
async def control_gif_generate(request: GifGenerateRequest) -> GifGenerateResponse:
    """Combine multiple screenshots into an animated GIF."""
    try:
        from PIL import Image

        if not request.images:
            return GifGenerateResponse(success=False, error="No images provided")

        frames = []
        for img_b64 in request.images:
            img_data = base64.b64decode(img_b64)
            img = Image.open(io.BytesIO(img_data)).convert("RGBA")
            # Resize to reasonable GIF size for performance
            img.thumbnail((400, 800), Image.LANCZOS)
            frames.append(img.convert("RGB"))

        if not frames:
            return GifGenerateResponse(success=False, error="Failed to decode images")

        buf = io.BytesIO()
        frames[0].save(
            buf,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            duration=request.duration_ms,
            loop=0,
        )
        gif_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

        return GifGenerateResponse(
            success=True,
            gif=gif_b64,
            frame_count=len(frames),
        )
    except ImportError:
        return GifGenerateResponse(success=False, error="Pillow not installed. Run: pip install Pillow")
    except Exception as e:
        return GifGenerateResponse(success=False, error=str(e))

# ─── Screen Recording Endpoints ──────────────────────────────────────────


@router.post("/api/control/record/start", response_model=RecordStartResponse)
async def control_record_start(request: RecordStartRequest) -> RecordStartResponse:
    """Start screen recording for device control operations."""
    try:
        if not request.device_id:
            return RecordStartResponse(success=False, error="device_id is required")

        device_id = request.device_id
        task_id = f"rec-{device_id}-{int(time.time() * 1000)}"

        _recording_state[device_id] = {
            "task_id": task_id,
            "actions": [],
            "screenshots": [],
            "start_time": time.time(),
        }

        return RecordStartResponse(
            success=True,
            message="Recording started",
            task_id=task_id,
        )
    except Exception as e:
        return RecordStartResponse(success=False, error=str(e))


@router.post("/api/control/record/stop", response_model=RecordStopResponse)
async def control_record_stop(request: RecordStopRequest) -> RecordStopResponse:
    """Stop screen recording and generate pytest/yaml code."""
    try:
        if not request.device_id:
            return RecordStopResponse(success=False, error="device_id is required")

        device_id = request.device_id
        if device_id not in _recording_state:
            return RecordStopResponse(
                success=False,
                error="No active recording found for this device",
            )

        state = _recording_state.pop(device_id)
        actions = state.get("actions", [])
        screenshots = state.get("screenshots", [])

        # Generate pytest code
        pytest_code = _build_pytest_code(actions, device_id)

        # Generate YAML code
        yaml_code = _build_yaml_code(actions, device_id)

        return RecordStopResponse(
            success=True,
            message="Recording stopped",
            task_id=state.get("task_id", ""),
            actions=actions,
            screenshots=screenshots,
            pytest_code=pytest_code,
            yaml_code=yaml_code,
        )
    except Exception as e:
        return RecordStopResponse(success=False, error=str(e))


def _build_pytest_code(actions: List[dict], device_id: str) -> str:
    """Build pytest code from recorded actions."""
    header = [
        '"""Auto-generated device control test."""',
        'import subprocess, time',
        f'DEVICE_ID = "{device_id}"',
        'def adb(cmd): subprocess.run(["adb","-s",DEVICE_ID,"shell",cmd],check=True)',
        'def tap(x,y): adb(f"input tap {x} {y}"); time.sleep(0.8)',
        'def dtap(x,y): tap(x,y); time.sleep(0.1); tap(x,y)',
        'def lpress(x,y,d=3000): adb(f"input swipe {x} {y} {x} {y} {d}"); time.sleep(1)',
        'def swipe(sx,sy,ex,ey,d=300): adb(f"input swipe {sx} {sy} {ex} {ey} {d}"); time.sleep(0.8)',
        'def scroll_up(): swipe(540,1500,540,500)',
        'def scroll_down(): swipe(540,500,540,1500)',
        'def scroll_left(): swipe(900,960,100,960)',
        'def scroll_right(): swipe(100,960,900,960)',
        'def back(): adb("input keyevent 4"); time.sleep(0.5)',
        'def home(): adb("input keyevent 3"); time.sleep(0.5)',
        'def launch(pkg): adb(f"monkey -p {pkg} -c android.intent.category.LAUNCHER 1"); time.sleep(2)',
        'def text(t): adb(f\'input text "{t}"\'); time.sleep(0.5)',
        'def key(k): adb(f"input keyevent {k}"); time.sleep(0.5)',
        '',
    ]

    steps = []
    for a in actions:
        action_type = a.get("type", "")
        params = a.get("params", {})

        if action_type == "tap":
            steps.append(f'tap({params.get("x", 0)}, {params.get("y", 0)})')
        elif action_type == "double_tap":
            steps.append(f'dtap({params.get("x", 0)}, {params.get("y", 0)})')
        elif action_type == "long_press":
            steps.append(f'lpress({params.get("x", 0)}, {params.get("y", 0)}, {params.get("duration", 3000)})')
        elif action_type == "swipe":
            steps.append(f'swipe({params.get("start_x", 0)},{params.get("start_y", 0)},{params.get("end_x", 0)},{params.get("end_y", 0)},{params.get("duration", 300)})')
        elif action_type == "scroll":
            direction = params.get("direction", "up")
            if direction == "up":
                steps.append("scroll_up()")
            elif direction == "down":
                steps.append("scroll_down()")
            elif direction == "left":
                steps.append("scroll_left()")
            elif direction == "right":
                steps.append("scroll_right()")
        elif action_type == "back":
            steps.append("back()")
        elif action_type == "home":
            steps.append("home()")
        elif action_type == "launch":
            pkg = params.get("app", "")
            steps.append(f'launch("{pkg}")')
        elif action_type == "type_text":
            t = params.get("text", "")
            steps.append(f'text("{t}")')
        elif action_type == "keyevent":
            steps.append(f'key({params.get("keycode", 0)})')
        else:
            steps.append(f'# {action_type}: {params}')

    if not steps:
        steps = ['# no actions recorded']

    return "\n".join(header + steps)


def _build_yaml_code(actions: List[dict], device_id: str) -> str:
    """Build YAML code from recorded actions."""
    steps = []
    for a in actions:
        action_type = a.get("type", "")
        params = a.get("params", {})

        step = {"action": action_type}
        step.update(params)
        steps.append(step)

    yaml_lines = [
        f'device_id: {device_id}',
        'steps:',
    ]

    for step in steps:
        action = step.pop("action", "")
        yaml_lines.append(f'  - action: {action}')
        for k, v in step.items():
            if isinstance(v, str):
                yaml_lines.append(f'    {k}: "{v}"')
            else:
                yaml_lines.append(f'    {k}: {v}')

    return "\n".join(yaml_lines)
