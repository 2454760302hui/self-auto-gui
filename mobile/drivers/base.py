"""
平台驱动抽象基类
定义所有平台驱动必须实现的接口
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class PlatformDriver(ABC):
    """平台驱动抽象基类"""

    platform: str = ""

    def _check_connected(self) -> None:
        """检查设备是否已连接，未连接时抛出异常"""
        pass

    @abstractmethod
    def connect(self, device: str) -> None:
        """连接设备"""

    @abstractmethod
    def disconnect(self) -> None:
        """断开设备连接"""

    @abstractmethod
    def launch_app(self, package: str, activity: str = None) -> None:
        """启动应用"""

    @abstractmethod
    def close_app(self, package: str) -> None:
        """关闭应用"""

    @abstractmethod
    def install_app(self, app_path: str) -> None:
        """安装应用"""

    @abstractmethod
    def uninstall_app(self, package: str) -> None:
        """卸载应用"""

    @abstractmethod
    def is_app_installed(self, package: str) -> bool:
        """检查应用是否已安装"""

    @abstractmethod
    def get_device_info(self) -> Dict[str, Any]:
        """获取设备信息"""

    @abstractmethod
    def find_element(self, locator_config: Dict[str, Any]) -> Optional[Any]:
        """查找元素（统一接口）"""

    @abstractmethod
    def tap(self, element: Any) -> None:
        """点击元素"""

    @abstractmethod
    def tap_coordinate(self, x: int, y: int) -> None:
        """点击坐标"""

    @abstractmethod
    def long_press(self, element: Any, duration: float = 1.0) -> None:
        """长按元素"""

    @abstractmethod
    def double_tap(self, element: Any) -> None:
        """双击元素"""

    @abstractmethod
    def input_text(self, element: Any, text: str) -> None:
        """输入文本"""

    @abstractmethod
    def clear_text(self, element: Any) -> None:
        """清空文本"""

    @abstractmethod
    def press_key(self, key: str) -> None:
        """按键（home, back, enter 等）"""

    @abstractmethod
    def swipe(self, direction: str, **kwargs) -> None:
        """滑动（up/down/left/right）"""

    @abstractmethod
    def scroll_to_text(self, text: str) -> None:
        """滚动到指定文本"""

    @abstractmethod
    def pinch(self, element: Any, scale: float = 0.5) -> None:
        """捏合"""

    @abstractmethod
    def zoom(self, element: Any, scale: float = 2.0) -> None:
        """放大"""

    @abstractmethod
    def get_text(self, element: Any) -> str:
        """获取元素文本"""

    @abstractmethod
    def get_attribute(self, element: Any, attr: str) -> Any:
        """获取元素属性"""

    @abstractmethod
    def is_visible(self, element: Any) -> bool:
        """检查元素是否可见"""

    @abstractmethod
    def is_exists(self, element: Any) -> bool:
        """检查元素是否存在"""

    @abstractmethod
    def wait_for_element(
        self, locator_config: Dict[str, Any], timeout: int = 10000, interval: float = 0.5
    ) -> Optional[Any]:
        """等待元素出现"""

    @abstractmethod
    def screenshot(self, path: str) -> str:
        """截图"""

    @abstractmethod
    def rotate_device(self, orientation: str) -> None:
        """旋转设备（portrait/landscape）"""

    @abstractmethod
    def pull_file(self, remote_path: str, local_path: str) -> None:
        """从设备拉取文件"""

    @abstractmethod
    def push_file(self, local_path: str, remote_path: str) -> None:
        """推送文件到设备"""

    @property
    def supported_strategies(self) -> List[str]:
        """返回此驱动支持的定位策略名称列表"""
        return []
