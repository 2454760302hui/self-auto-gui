"""HDC (HarmonyOS Device Connector) command builder and device listing."""

import subprocess
from typing import Sequence

from AutoGLM_GUI.logger import logger


def build_hdc_command(device_id: str | None = None, hdc_path: str = "hdc") -> list[str]:
    """Build HDC command prefix with optional device specifier.

    Args:
        device_id: Optional device serial number.
        hdc_path: Path to hdc executable.

    Returns:
        Command parts list, e.g. ["hdc", "-t", "device_id"].
    """
    cmd: list[str] = [hdc_path]
    if device_id:
        cmd.extend(["-t", device_id])
    return cmd


def list_hdc_devices(hdc_path: str = "hdc") -> list[dict[str, str]]:
    """List connected HarmonyOS devices via hdc.

    Returns:
        List of dicts with 'serial' and 'status' keys.
    """
    try:
        result = subprocess.run(
            [hdc_path, "list", "targets"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return []

        devices = []
        for line in result.stdout.strip().splitlines():
            line = line.strip()
            if not line or line.startswith("[") or line == "Empty":
                continue
            # hdc list targets outputs one serial per line
            devices.append({"serial": line, "status": "device"})
        return devices
    except (FileNotFoundError, subprocess.TimeoutExpired):
        logger.debug("hdc not found or timed out - HarmonyOS support disabled")
        return []
