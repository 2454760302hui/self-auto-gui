"""Device health monitor for XNext - collects battery, storage, memory info via ADB."""

from __future__ import annotations

import asyncio
import re
from typing import Any

from AutoGLM_GUI.logger import logger


async def _run_adb(serial: str, args: str, timeout: int = 5) -> str:
    """Run an ADB shell command and return stdout."""
    cmd = f"adb -s {serial} {args}"
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return stdout.decode("utf-8", errors="replace").strip()
    except asyncio.TimeoutError:
        proc.kill()
        return ""


async def get_battery_info(serial: str) -> dict[str, Any]:
    """Get battery level and status via ADB dumpsys."""
    output = await _run_adb(serial, "shell dumpsys battery")
    info: dict[str, Any] = {"level": None, "status": "unknown", "temperature": None}

    level_match = re.search(r"level:\s*(\d+)", output)
    if level_match:
        info["level"] = int(level_match.group(1))

    status_match = re.search(r"status:\s*(\d+)", output)
    if status_match:
        status_map = {
            "2": "charging",
            "3": "discharging",
            "4": "not_charging",
            "5": "full",
        }
        info["status"] = status_map.get(status_match.group(1), "unknown")

    temp_match = re.search(r"temperature:\s*(\d+)", output)
    if temp_match:
        info["temperature"] = int(temp_match.group(1)) / 10.0

    return info


async def get_storage_info(serial: str) -> dict[str, Any]:
    """Get storage usage via ABD df."""
    output = await _run_adb(serial, "shell df /data")
    info: dict[str, Any] = {"total_mb": None, "used_mb": None, "available_mb": None}

    lines = output.strip().split("\n")
    if len(lines) >= 2:
        parts = lines[1].split()
        if len(parts) >= 4:
            try:
                info["total_mb"] = int(parts[1]) // 1024
                info["used_mb"] = int(parts[2]) // 1024
                info["available_mb"] = int(parts[3]) // 1024
            except (ValueError, IndexError):
                pass

    return info


async def get_memory_info(serial: str) -> dict[str, Any]:
    """Get memory usage via ADB meminfo."""
    output = await _run_adb(serial, "shell cat /proc/meminfo")
    info: dict[str, Any] = {"total_mb": None, "available_mb": None}

    total_match = re.search(r"MemTotal:\s*(\d+)", output)
    if total_match:
        info["total_mb"] = int(total_match.group(1)) // 1024

    avail_match = re.search(r"MemAvailable:\s*(\d+)", output)
    if avail_match:
        info["available_mb"] = int(avail_match.group(1)) // 1024

    return info


async def get_device_health(serial: str) -> dict[str, Any]:
    """Collect all health metrics for a device."""
    try:
        battery, storage, memory = await asyncio.gather(
            get_battery_info(serial),
            get_storage_info(serial),
            get_memory_info(serial),
        )
        return {
            "serial": serial,
            "battery": battery,
            "storage": storage,
            "memory": memory,
        }
    except Exception as e:
        logger.warning(f"Failed to get health for {serial}: {e}")
        return {"serial": serial, "error": str(e)}
