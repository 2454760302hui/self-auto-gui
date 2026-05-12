"""
Android 驱动
基于 uiautomator2 实现
"""
import time
from typing import Any, Dict, List, Optional

from .base import PlatformDriver
from core.errors import DeviceError


class AndroidDriver(PlatformDriver):
    """Android 驱动（uiautomator2）"""

    platform = "android"

    def __init__(self):
        self._device = None
        self._device_addr = ""

    def _check_connected(self) -> None:
        """检查设备是否已连接"""
        if self._device is None:
            raise DeviceError.not_connected(self._device_addr or "unknown")

    def connect(self, device: str) -> None:
        import uiautomator2 as u2
        self._device_addr = device
        self._device = u2.connect(device)

    def disconnect(self) -> None:
        if self._device:
            try:
                self._device.stop_uiautomator()
            except Exception:
                pass
            self._device = None

    def launch_app(self, package: str, activity: str = None) -> None:
        self._check_connected()
        if activity:
            self._device.app_start(package, activity)
        else:
            self._device.app_start(package)

    def close_app(self, package: str) -> None:
        self._check_connected()
        self._device.app_stop(package)

    def install_app(self, app_path: str) -> None:
        self._check_connected()
        self._device.app_install(app_path)

    def uninstall_app(self, package: str) -> None:
        self._check_connected()
        self._device.app_uninstall(package)

    def is_app_installed(self, package: str) -> bool:
        self._check_connected()
        return package in self._device.app_list()

    def get_device_info(self) -> Dict[str, Any]:
        self._check_connected()
        info = self._device.info
        return {
            "platform": "android",
            "device": info.get("deviceName", ""),
            "version": info.get("version", ""),
            "screen": info.get("display", {}),
        }

    def find_element(self, locator_config: Dict[str, Any]) -> Optional[Any]:
        """根据定位器配置查找元素"""
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
        elif locator_type == "accessibility_id":
            return self.find_by_description(value)

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
        self._check_connected()
        element.click()

    def tap_coordinate(self, x: int, y: int) -> None:
        self._check_connected()
        self._device.click(x, y)

    def long_press(self, element: Any, duration: float = 1.0) -> None:
        self._check_connected()
        element.long_click(duration=int(duration * 1000))

    def double_tap(self, element: Any) -> None:
        self._check_connected()
        element.double_click()

    def input_text(self, element: Any, text: str) -> None:
        self._check_connected()
        element.set_text(text)

    def clear_text(self, element: Any) -> None:
        self._check_connected()
        element.clear_text()

    def press_key(self, key: str) -> None:
        self._check_connected()
        key_map = {
            "home": "home", "back": "back", "enter": "enter",
            "volume_up": "volumeUp", "volume_down": "volumeDown",
            "power": "power", "recent": "recentApps",
        }
        mapped_key = key_map.get(key.lower(), key)
        self._device.press(mapped_key)

    def swipe(self, direction: str, **kwargs) -> None:
        self._check_connected()
        self._device.swipe(direction, **kwargs)

    def scroll_to_text(self, text: str) -> None:
        self._check_connected()
        self._device(scrollable=True).scroll.to(text=text)

    def pinch(self, element: Any, scale: float = 0.5) -> None:
        self._check_connected()
        element.pinch_in(scale=scale)

    def zoom(self, element: Any, scale: float = 2.0) -> None:
        self._check_connected()
        element.pinch_out(scale=scale)

    def get_text(self, element: Any) -> str:
        self._check_connected()
        return element.get_text()

    def get_attribute(self, element: Any, attr: str) -> Any:
        self._check_connected()
        info = element.info
        return info.get(attr)

    def is_visible(self, element: Any) -> bool:
        self._check_connected()
        return element.exists

    def is_exists(self, element: Any) -> bool:
        self._check_connected()
        return element.exists

    def wait_for_element(
        self, locator_config: Dict[str, Any], timeout: int = 10000, interval: float = 0.5
    ) -> Optional[Any]:
        # 使用 uiautomator2 原生等待
        resource_id = locator_config.get("resource_id")
        text = locator_config.get("text")
        if resource_id:
            el = self._device(resourceId=resource_id)
            if el.wait(timeout=timeout / 1000):
                return el
        if text:
            el = self._device(text=text)
            if el.wait(timeout=timeout / 1000):
                return el
        # fallback: 通用轮询
        deadline = time.time() + timeout / 1000
        while time.time() < deadline:
            el = self.find_element(locator_config)
            if el is not None:
                return el
            time.sleep(interval)
        return None

    def screenshot(self, path: str) -> str:
        self._check_connected()
        self._device.screenshot(path)
        return path

    def rotate_device(self, orientation: str) -> None:
        self._check_connected()
        self._device.set_orientation(orientation)

    def pull_file(self, remote_path: str, local_path: str) -> None:
        self._check_connected()
        self._device.pull(remote_path, local_path)

    def push_file(self, local_path: str, remote_path: str) -> None:
        self._check_connected()
        self._device.push(local_path, remote_path)

    @property
    def supported_strategies(self) -> List[str]:
        return ["resource_id", "text", "textContains", "description", "class_name", "xpath", "coordinate", "image"]
