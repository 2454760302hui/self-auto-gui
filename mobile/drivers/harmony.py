"""
HarmonyOS 驱动
基于 hmdriver2 + HDC 实现
"""
import time
import subprocess
from typing import Any, Dict, List, Optional

from .base import PlatformDriver


class HarmonyDriver(PlatformDriver):
    """HarmonyOS 驱动（hmdriver2 + HDC）"""

    platform = "harmony"

    def __init__(self):
        self._device = None
        self._device_serial = ""

    def _check_connected(self) -> None:
        if self._device is None:
            from core.errors import DeviceError
            raise DeviceError.not_connected(self._device_serial or "unknown")

    def connect(self, device: str) -> None:
        try:
            import hmdriver2
            self._device = hmdriver2.connect(device)
            self._device_serial = device
        except ImportError:
            raise ImportError(
                "hmdriver2 未安装，请执行: pip install hmdriver2"
            )

    def disconnect(self) -> None:
        self._device = None
        self._device_serial = ""

    def launch_app(self, package: str, activity: str = None) -> None:
        self._check_connected()
        if activity:
            self._device.start_hap(package, activity)
        else:
            self._device.start_hap(package)

    def close_app(self, package: str) -> None:
        self._check_connected()
        self._device.force_stop_hap(package)

    def install_app(self, app_path: str) -> None:
        self._hdc_command(f"install {app_path}")

    def uninstall_app(self, package: str) -> None:
        self._hdc_command(f"uninstall {package}")

    def is_app_installed(self, package: str) -> bool:
        result = self._hdc_command(f"shell bm dump -n {package}")
        return package in result

    def get_device_info(self) -> Dict[str, Any]:
        info = {}
        try:
            info = self._device.device_info
        except Exception:
            pass
        return {
            "platform": "harmony",
            "device": self._device_serial,
            **info,
        }

    def find_element(self, locator_config: Dict[str, Any]) -> Optional[Any]:
        locator_type = locator_config.get("type", "")
        value = locator_config.get("value", "")

        if locator_type == "resource_id":
            return self.find_by_resource_id(value)
        elif locator_type == "text":
            return self.find_by_text(value)
        elif locator_type == "description":
            return self.find_by_description(value)
        elif locator_type == "class_name":
            return self.find_by_class_name(value)
        elif locator_type == "xpath":
            return self.find_by_xpath(value)

        return None

    def find_by_resource_id(self, resource_id: str) -> Optional[Any]:
        try:
            el = self._device(resourceId=resource_id)
            if el.exists:
                return el
        except Exception:
            pass
        return None

    def find_by_text(self, text: str) -> Optional[Any]:
        try:
            el = self._device(text=text)
            if el.exists:
                return el
        except Exception:
            pass
        return None

    def find_by_description(self, desc: str) -> Optional[Any]:
        try:
            el = self._device(description=desc)
            if el.exists:
                return el
        except Exception:
            pass
        return None

    def find_by_class_name(self, cls_name: str) -> Optional[Any]:
        try:
            el = self._device(className=cls_name)
            if el.exists:
                return el
        except Exception:
            pass
        return None

    def find_by_xpath(self, xpath: str) -> Optional[Any]:
        try:
            el = self._device.xpath(xpath)
            if el.exists:
                return el
        except Exception:
            pass
        return None

    def tap(self, element: Any) -> None:
        element.click()

    def tap_coordinate(self, x: int, y: int) -> None:
        self._device.click(x, y)

    def long_press(self, element: Any, duration: float = 1.0) -> None:
        element.long_click(duration=int(duration * 1000))

    def double_tap(self, element: Any) -> None:
        element.double_click()

    def input_text(self, element: Any, text: str) -> None:
        element.set_text(text)

    def clear_text(self, element: Any) -> None:
        element.clear_text()

    def press_key(self, key: str) -> None:
        key_map = {
            "home": "Home", "back": "Back", "enter": "Enter",
            "volume_up": "VolumeUp", "volume_down": "VolumeDown",
            "power": "Power",
        }
        mapped_key = key_map.get(key.lower(), key)
        self._device.press_key(mapped_key)

    def swipe(self, direction: str, **kwargs) -> None:
        self._device.swipe(direction, **kwargs)

    def scroll_to_text(self, text: str) -> None:
        self._device(scrollable=True).scroll.to(text=text)

    def pinch(self, element: Any, scale: float = 0.5) -> None:
        element.pinch_in(scale=scale)

    def zoom(self, element: Any, scale: float = 2.0) -> None:
        element.pinch_out(scale=scale)

    def get_text(self, element: Any) -> str:
        return element.get_text()

    def get_attribute(self, element: Any, attr: str) -> Any:
        info = element.info
        return info.get(attr)

    def is_visible(self, element: Any) -> bool:
        return element.exists

    def is_exists(self, element: Any) -> bool:
        return element.exists

    def wait_for_element(
        self, locator_config: Dict[str, Any], timeout: int = 10000, interval: float = 0.5
    ) -> Optional[Any]:
        # 鸿蒙使用 hdc timeout 参数
        locator_type = locator_config.get("type", "")
        value = locator_config.get("value", "")
        try:
            if locator_type == "resource_id":
                el = self._device(resourceId=value)
                if el.wait(timeout=timeout / 1000):
                    return el
            elif locator_type == "text":
                el = self._device(text=value)
                if el.wait(timeout=timeout / 1000):
                    return el
        except Exception:
            pass
        # fallback: 通用轮询
        deadline = time.time() + timeout / 1000
        while time.time() < deadline:
            el = self.find_element(locator_config)
            if el is not None:
                return el
            time.sleep(interval)
        return None

    def screenshot(self, path: str) -> str:
        self._device.screenshot(path)
        return path

    def rotate_device(self, orientation: str) -> None:
        self._device.set_orientation(orientation)

    def pull_file(self, remote_path: str, local_path: str) -> None:
        self._hdc_command(f"file recv {remote_path} {local_path}")

    def push_file(self, local_path: str, remote_path: str) -> None:
        self._hdc_command(f"file send {local_path} {remote_path}")

    def _hdc_command(self, cmd: str) -> str:
        """执行 HDC 命令"""
        full_cmd = f"hdc -t {self._device_serial} {cmd}"
        try:
            result = subprocess.run(
                full_cmd, shell=True, capture_output=True, text=True, timeout=30
            )
            return result.stdout
        except subprocess.TimeoutExpired:
            return ""

    @property
    def supported_strategies(self) -> List[str]:
        return ["resource_id", "text", "textContains", "description", "class_name", "xpath", "coordinate", "image"]
