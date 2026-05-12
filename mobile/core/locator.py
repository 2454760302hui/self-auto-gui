"""
移动端智能定位器
支持多种定位策略：resource_id, accessibility_id, text, xpath, image 等
"""
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from drivers.base import PlatformDriver
from .errors import LocatorError


class LocatorStrategy(ABC):
    """定位策略抽象基类"""

    name: str = ""
    priority: int = 100

    @abstractmethod
    def can_handle(self, locator_str: str) -> bool:
        """判断是否能处理此定位器字符串"""

    @abstractmethod
    def locate(self, driver: PlatformDriver, value: str) -> Optional[Any]:
        """使用此策略定位元素"""


class ResourceIDStrategy(LocatorStrategy):
    """resource-id 定位策略"""
    name = "resource_id"
    priority = 5

    def can_handle(self, locator_str: str) -> bool:
        return locator_str.startswith("rid=")

    def locate(self, driver: PlatformDriver, value: str) -> Optional[Any]:
        resource_id = value[4:]  # 去掉 "rid="
        return driver.find_element({"type": "resource_id", "value": resource_id})


class AccessibilityIDStrategy(LocatorStrategy):
    """accessibility-id 定位策略"""
    name = "accessibility_id"
    priority = 10

    def can_handle(self, locator_str: str) -> bool:
        return locator_str.startswith("aid=")

    def locate(self, driver: PlatformDriver, value: str) -> Optional[Any]:
        aid = value[4:]
        return driver.find_element({"type": "accessibility_id", "value": aid})


class TextStrategy(LocatorStrategy):
    """精确文本定位策略"""
    name = "text"
    priority = 15

    def can_handle(self, locator_str: str) -> bool:
        return locator_str.startswith("text=")

    def locate(self, driver: PlatformDriver, value: str) -> Optional[Any]:
        text = value[5:]
        return driver.find_element({"type": "text", "value": text})


class TextContainsStrategy(LocatorStrategy):
    """包含文本定位策略"""
    name = "textContains"
    priority = 16

    def can_handle(self, locator_str: str) -> bool:
        return locator_str.startswith("textContains=")

    def locate(self, driver: PlatformDriver, value: str) -> Optional[Any]:
        text = value[13:]
        # 尝试 text 定位（部分驱动支持模糊匹配）
        return driver.find_element({"type": "text", "value": text})


class DescriptionStrategy(LocatorStrategy):
    """description 定位策略"""
    name = "description"
    priority = 20

    def can_handle(self, locator_str: str) -> bool:
        return locator_str.startswith("desc=")

    def locate(self, driver: PlatformDriver, value: str) -> Optional[Any]:
        desc = value[5:]
        return driver.find_element({"type": "description", "value": desc})


class ClassNameStrategy(LocatorStrategy):
    """class-name 定位策略"""
    name = "class_name"
    priority = 25

    def can_handle(self, locator_str: str) -> bool:
        return locator_str.startswith("className=")

    def locate(self, driver: PlatformDriver, value: str) -> Optional[Any]:
        cls_name = value[10:]
        return driver.find_element({"type": "class_name", "value": cls_name})


class XPathStrategy(LocatorStrategy):
    """XPath 定位策略"""
    name = "xpath"
    priority = 30

    def can_handle(self, locator_str: str) -> bool:
        return locator_str.startswith("xpath=")

    def locate(self, driver: PlatformDriver, value: str) -> Optional[Any]:
        xpath = value[6:]
        return driver.find_element({"type": "xpath", "value": xpath})


class PredicateStrategy(LocatorStrategy):
    """iOS NSPredicate 定位策略"""
    name = "predicate"
    priority = 35

    def can_handle(self, locator_str: str) -> bool:
        return locator_str.startswith("predicate=")

    def locate(self, driver: PlatformDriver, value: str) -> Optional[Any]:
        predicate = value[10:]
        return driver.find_element({"type": "predicate", "value": predicate})


class ClassChainStrategy(LocatorStrategy):
    """iOS class-chain 定位策略"""
    name = "class_chain"
    priority = 36

    def can_handle(self, locator_str: str) -> bool:
        return locator_str.startswith("classChain=")

    def locate(self, driver: PlatformDriver, value: str) -> Optional[Any]:
        chain = value[11:]
        return driver.find_element({"type": "class_chain", "value": chain})


class CoordinateStrategy(LocatorStrategy):
    """坐标定位策略（返回坐标字典而非元素）"""
    name = "coordinate"
    priority = 40

    def can_handle(self, locator_str: str) -> bool:
        return locator_str.startswith("coord=")

    def locate(self, driver: PlatformDriver, value: str) -> Optional[Any]:
        coord_str = value[6:]
        try:
            parts = coord_str.split(",")
            x, y = int(parts[0].strip()), int(parts[1].strip())
            return {"type": "coordinate", "x": x, "y": y}
        except (ValueError, IndexError):
            return None


class ImageStrategy(LocatorStrategy):
    """图像匹配定位策略（基于 OpenCV）"""
    name = "image"
    priority = 50

    def can_handle(self, locator_str: str) -> bool:
        return locator_str.startswith("image=")

    def locate(self, driver: PlatformDriver, value: str) -> Optional[Any]:
        image_path = value[6:]
        if not os.path.exists(image_path):
            return None

        try:
            import cv2
            import numpy as np
            from PIL import Image
            import tempfile

            # 截取当前屏幕
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                screen_path = tmp.name
            try:
                driver.screenshot(screen_path)

                # 模板匹配
                screen = cv2.imread(screen_path)
                template = cv2.imread(image_path)

                if screen is None or template is None:
                    return None

                result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

                if max_val < 0.8:
                    return None

                # 计算中心坐标
                h, w = template.shape[:2]
                center_x = max_loc[0] + w // 2
                center_y = max_loc[1] + h // 2

                return {"type": "coordinate", "x": center_x, "y": center_y}
            finally:
                # 清理临时文件
                if os.path.exists(screen_path):
                    os.unlink(screen_path)

        except ImportError:
            return None


class SmartLocator:
    """智能定位器"""

    def __init__(self, driver: PlatformDriver, runner=None):
        self._driver = driver
        self._runner = runner
        self._strategies: List[LocatorStrategy] = []
        self._locators: Dict[str, Any] = {}
        self._aliases: Dict[str, str] = {}

        self._register_default_strategies()

    def _register_default_strategies(self) -> None:
        """注册默认定位策略"""
        default_strategies = [
            ResourceIDStrategy(),
            AccessibilityIDStrategy(),
            TextStrategy(),
            TextContainsStrategy(),
            DescriptionStrategy(),
            ClassNameStrategy(),
            XPathStrategy(),
            PredicateStrategy(),
            ClassChainStrategy(),
            CoordinateStrategy(),
            ImageStrategy(),
        ]

        # 只注册当前驱动支持的策略
        supported = set(self._driver.supported_strategies)
        for strategy in default_strategies:
            if strategy.name in supported or strategy.name in ("coordinate", "image"):
                self._strategies.append(strategy)

        # 按优先级排序
        self._strategies.sort(key=lambda s: s.priority)

    def register_strategy(self, strategy: LocatorStrategy) -> None:
        """注册自定义定位策略"""
        self._strategies.append(strategy)
        self._strategies.sort(key=lambda s: s.priority)

    def set_locators(self, locators: Dict[str, Any]) -> None:
        """设置定位器库"""
        self._locators = locators

    def set_aliases(self, aliases: Dict[str, str]) -> None:
        """设置别名"""
        self._aliases = aliases

    def locate(self, config: Dict[str, Any]) -> Optional[Any]:
        """
        定位元素

        优先级:
        1. 直接定位器字符串 (定位器/locator)
        2. 定位器库查找 (元素/element)
        3. 名称多策略回退 (名称/name)
        """
        # 1. 直接定位器字符串
        locator_str = config.get("定位器") or config.get("locator")
        if locator_str:
            element = self._locate_by_strategy(locator_str)
            if element is not None:
                return element

        # 2. 定位器库查找
        element_name = config.get("元素") or config.get("element")
        if element_name:
            # 先解析别名
            element_name = self._aliases.get(element_name, element_name)
            element = self._locate_from_library(element_name)
            if element is not None:
                return element

        # 3. 名称多策略回退
        name = config.get("名称") or config.get("name")
        if name:
            name = self._aliases.get(name, name)
            element = self._locate_by_name(name)
            if element is not None:
                return element

        # 如果 element/name 没有在库中找到，也尝试作为定位器字符串
        if element_name:
            element = self._locate_by_name(element_name)
            if element is not None:
                return element

        return None

    def _locate_from_library(self, element_name: str) -> Optional[Any]:
        """从定位器库查找元素"""
        locator_config = self._locators.get(element_name)
        if not locator_config:
            return None

        if isinstance(locator_config, str):
            return self._locate_by_strategy(locator_config)

        if isinstance(locator_config, dict):
            # 先尝试 primary
            primary = locator_config.get("primary", "")
            if primary:
                element = self._locate_by_strategy(primary)
                if element is not None:
                    return element

            # 再尝试 fallback 列表
            fallbacks = locator_config.get("fallback", [])
            for fallback in fallbacks:
                element = self._locate_by_strategy(fallback)
                if element is not None:
                    return element

        return None

    def _locate_by_strategy(self, locator_str: str) -> Optional[Any]:
        """按策略优先级尝试定位"""
        for strategy in self._strategies:
            if strategy.can_handle(locator_str):
                try:
                    element = strategy.locate(self._driver, locator_str)
                    if element is not None:
                        return element
                except Exception:
                    continue
        return None

    def _locate_by_name(self, name: str) -> Optional[Any]:
        """按名称多策略回退定位"""
        # 尝试 text 定位
        element = self._driver.find_element({"type": "text", "value": name})
        if element is not None:
            return element

        # 尝试 description 定位
        element = self._driver.find_element({"type": "description", "value": name})
        if element is not None:
            return element

        # 尝试 accessibility_id 定位
        element = self._driver.find_element({"type": "accessibility_id", "value": name})
        if element is not None:
            return element

        return None
