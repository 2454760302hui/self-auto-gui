"""
iOS 驱动
基于 facebook-wda 实现
"""
import time
from typing import Any, Dict, List, Optional

from .base import PlatformDriver
from core.errors import DeviceError


class IOSDriver(PlatformDriver):
    """iOS 驱动（facebook-wda）"""

    platform = "ios"

    def __init__(self):
        self._client = None
        self._session = None
        self._device_addr = ""

    def _check_connected(self) -> None:
        """检查设备是否已连接"""
        if self._session is None and self._client is None:
            raise DeviceError.not_connected(self._device_addr or "unknown")

    def connect(self, device: str) -> None:
        import wda
        self._device_addr = device
        url = f"http://{device}"
        self._client = wda.Client(url)
        self._session = self._client.session()

    def disconnect(self) -> None:
        if self._session:
            try:
                self._session.close()
            except Exception:
                pass
            self._session = None
        self._client = None

    def launch_app(self, package: str, activity: str = None) -> None:
        self._check_connected()
        self._session = self._client.session(bundle_id=package)

    def close_app(self, package: str) -> None:
        self._check_connected()
        if self._session:
            self._session.close()

    def install_app(self, app_path: str) -> None:
        # wda 不直接支持安装，需要通过 xcodebuild 或其他工具
        raise NotImplementedError("iOS 安装应用请使用 xcodebuild 或其他工具")

    def uninstall_app(self, package: str) -> None:
        raise NotImplementedError("iOS 卸载应用请使用 ideviceinstaller 或其他工具")

    def is_app_installed(self, package: str) -> bool:
        # wda 不直接支持检查安装状态
        raise NotImplementedError("iOS 检查应用安装状态请使用 ideviceinstaller")

    def get_device_info(self) -> Dict[str, Any]:
        self._check_connected()
        info = self._client.info
        return {
            "platform": "ios",
            "device": info.get("name", ""),
            "version": info.get("version", ""),
        }

    def find_element(self, locator_config: Dict[str, Any]) -> Optional[Any]:
        locator_type = locator_config.get("type", "")
        value = locator_config.get("value", "")

        if locator_type == "accessibility_id":
            return self.find_by_accessibility_id(value)
        elif locator_type == "predicate":
            return self.find_by_predicate(value)
        elif locator_type == "class_chain":
            return self.find_by_class_chain(value)
        elif locator_type == "xpath":
            return self.find_by_xpath(value)
        elif locator_type == "text":
            return self.find_by_text(value)

        return None

    def find_by_accessibility_id(self, aid: str) -> Optional[Any]:
        try:
            el = self._session(id=aid)
            if el.exists:
                return el
        except Exception:
            pass
        return None

    def find_by_predicate(self, predicate: str) -> Optional[Any]:
        try:
            el = self._session(predicate=predicate)
            if el.exists:
                return el
        except Exception:
            pass
        return None

    def find_by_class_chain(self, chain: str) -> Optional[Any]:
        try:
            el = self._session(classChain=chain)
            if el.exists:
                return el
        except Exception:
            pass
        return None

    def find_by_xpath(self, xpath: str) -> Optional[Any]:
        try:
            el = self._session.xpath(xpath)
            if el.exists:
                return el
        except Exception:
            pass
        return None

    def find_by_text(self, text: str) -> Optional[Any]:
        try:
            el = self._session(text=text)
            if el.exists:
                return el
        except Exception:
            pass
        return None

    def tap(self, element: Any) -> None:
        self._check_connected()
        element.tap()

    def tap_coordinate(self, x: int, y: int) -> None:
        self._check_connected()
        self._session.tap(x, y)

    def long_press(self, element: Any, duration: float = 1.0) -> None:
        self._check_connected()
        element.tapHold(duration=duration)

    def double_tap(self, element: Any) -> None:
        self._check_connected()
        element.doubleTap()

    def input_text(self, element: Any, text: str) -> None:
        self._check_connected()
        element.set_text(text)

    def clear_text(self, element: Any) -> None:
        self._check_connected()
        element.clear_text()

    def press_key(self, key: str) -> None:
        self._check_connected()
        # iOS 模拟按键映射
        if key.lower() == "home":
            self._session.home()
        elif key.lower() == "volume_up":
            self._session.volume_up()
        elif key.lower() == "volume_down":
            self._session.volume_down()
        else:
            raise NotImplementedError(f"iOS 不支持按键: {key}")

    def swipe(self, direction: str, **kwargs) -> None:
        self._check_connected()
        size = self._session.window_size()
        w, h = size.width, size.height
        cx, cy = w // 2, h // 2

        if direction == "up":
            self._session.swipe(cx, cy, cx, cy - h // 3, **kwargs)
        elif direction == "down":
            self._session.swipe(cx, cy, cx, cy + h // 3, **kwargs)
        elif direction == "left":
            self._session.swipe(cx, cy, cx - w // 3, cy, **kwargs)
        elif direction == "right":
            self._session.swipe(cx, cy, cx + w // 3, cy, **kwargs)

    def scroll_to_text(self, text: str) -> None:
        self._check_connected()
        # iOS 通过多次滑动查找文本
        for _ in range(5):
            el = self.find_by_text(text)
            if el is not None:
                return
            self.swipe("up")

    def pinch(self, element: Any, scale: float = 0.5) -> None:
        self._check_connected()
        element.pinch(scale=scale)

    def zoom(self, element: Any, scale: float = 2.0) -> None:
        self._check_connected()
        element.pinch(scale=scale)

    def get_text(self, element: Any) -> str:
        self._check_connected()
        return element.text

    def get_attribute(self, element: Any, attr: str) -> Any:
        self._check_connected()
        return getattr(element, attr, None)

    def is_visible(self, element: Any) -> bool:
        self._check_connected()
        return element.exists

    def is_exists(self, element: Any) -> bool:
        self._check_connected()
        return element.exists

    def wait_for_element(
        self, locator_config: Dict[str, Any], timeout: int = 10000, interval: float = 0.5
    ) -> Optional[Any]:
        # 使用 WebDriverAgent 原生等待
        locator_type = locator_config.get("type", "")
        value = locator_config.get("value", "")
        try:
            if locator_type == "accessibility_id":
                el = self._session(id=value)
                if el.wait(timeout=timeout / 1000):
                    return el
            elif locator_type == "text":
                el = self._session(name=value)
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
        self._check_connected()
        img = self._session.screenshot()
        img.save(path)
        return path

    def rotate_device(self, orientation: str) -> None:
        self._check_connected()
        self._session.orientation = orientation

    def pull_file(self, remote_path: str, local_path: str) -> None:
        raise NotImplementedError("iOS 文件拉取请使用 idevicefs 或其他工具")

    def push_file(self, local_path: str, remote_path: str) -> None:
        raise NotImplementedError("iOS 文件推送请使用 idevicefs 或其他工具")

    @property
    def supported_strategies(self) -> List[str]:
        return ["accessibility_id", "text", "predicate", "class_chain", "xpath", "coordinate", "image"]
