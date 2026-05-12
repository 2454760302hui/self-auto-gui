"""Screenshot capture for HarmonyOS devices via hdc."""

import base64
import os
import subprocess
import tempfile

from AutoGLM_GUI.hdc.connection import build_hdc_command
from AutoGLM_GUI.logger import logger
from AutoGLM_GUI.trace import trace_span


def capture_screenshot(device_id: str, hdc_path: str = "hdc", timeout: int = 10) -> dict:
    """Capture a screenshot from a HarmonyOS device.

    Uses `hdc shell snapshot_display` then `hdc file recv` to pull the image.

    Returns:
        Dict with 'success', 'image' (base64), 'width', 'height' keys.
    """
    hdc_prefix = build_hdc_command(device_id, hdc_path)
    remote_path = "/data/local/tmp/xnext_screenshot.png"

    with trace_span("hdc.capture_screenshot", attrs={"device_id": device_id}):
        # Take screenshot on device
        result = subprocess.run(
            hdc_prefix + ["shell", f"snapshot_display -f {remote_path}"],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode != 0:
            logger.warning(f"hdc screenshot capture failed: {result.stderr}")
            return {"success": False, "error": f"snapshot_display failed: {result.stderr}"}

        # Pull screenshot to local temp file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                hdc_prefix + ["file", "recv", remote_path, tmp_path],
                capture_output=True, text=True, timeout=timeout,
            )
            if result.returncode != 0:
                return {"success": False, "error": f"hdc file recv failed: {result.stderr}"}

            if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
                return {"success": False, "error": "Screenshot file is empty"}

            with open(tmp_path, "rb") as f:
                image_data = f.read()

            b64_data = base64.b64encode(image_data).decode("utf-8")

            # Get dimensions from PNG header
            width, height = _png_dimensions(image_data)

            return {
                "success": True,
                "image": b64_data,
                "width": width,
                "height": height,
                "is_sensitive": False,
            }
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

            # Clean up remote file
            subprocess.run(
                hdc_prefix + ["shell", f"rm -f {remote_path}"],
                capture_output=True, text=True, timeout=5,
            )


def _png_dimensions(data: bytes) -> tuple[int, int]:
    """Extract width and height from PNG IHDR chunk."""
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return 0, 0
    import struct
    width = struct.unpack(">I", data[16:20])[0]
    height = struct.unpack(">I", data[20:24])[0]
    return width, height
