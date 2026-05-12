"""
驱动工厂
"""
from typing import Optional

from .base import PlatformDriver
from core.errors import DeviceError


def create_driver(platform: str) -> PlatformDriver:
    """根据平台创建驱动实例"""
    platform = platform.lower().strip()

    if platform == "android":
        from .android import AndroidDriver
        return AndroidDriver()
    elif platform == "ios":
        from .ios import IOSDriver
        return IOSDriver()
    elif platform in ("harmony", "harmonyos"):
        from .harmony import HarmonyDriver
        return HarmonyDriver()
    else:
        raise DeviceError.driver_init_failed(
            platform,
            f"不支持的平台: {platform}，支持: android, ios, harmony"
        )
