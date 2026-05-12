"""
点击操作：点击、长按、双击
"""
from typing import Any, Dict

from .base import OperationBase, OperationResult
from .registry import operation
from core.errors import OperationError


@operation("点击", "tap")
class TapOperation(OperationBase):
    operation_name = "点击"

    def _execute(self, params: Dict[str, Any]) -> OperationResult:
        # 坐标点击
        x = params.get("x")
        y = params.get("y")
        if x is not None and y is not None:
            self._driver.tap_coordinate(int(x), int(y))
            return OperationResult(success=True, data={"x": x, "y": y})

        # 元素点击
        element = self._find_element(params)
        if element is None:
            raise OperationError.failed("点击", "未找到元素", str(params))

        # 坐标类型（图像匹配返回的）
        if isinstance(element, dict) and element.get("type") == "coordinate":
            self._driver.tap_coordinate(element["x"], element["y"])
            return OperationResult(success=True, data=element)

        self._driver.tap(element)
        return OperationResult(success=True)


@operation("长按", "long_press")
class LongPressOperation(OperationBase):
    operation_name = "长按"

    def _execute(self, params: Dict[str, Any]) -> OperationResult:
        duration = float(params.get("duration", params.get("持续时间", 1.0)))
        element = self._find_element(params)
        if element is None:
            raise OperationError.failed("长按", "未找到元素", str(params))

        if isinstance(element, dict) and element.get("type") == "coordinate":
            self._driver.tap_coordinate(element["x"], element["y"])
            return OperationResult(success=True, data=element)

        self._driver.long_press(element, duration)
        return OperationResult(success=True, data={"duration": duration})


@operation("双击", "double_tap")
class DoubleTapOperation(OperationBase):
    operation_name = "双击"

    def _execute(self, params: Dict[str, Any]) -> OperationResult:
        element = self._find_element(params)
        if element is None:
            raise OperationError.failed("双击", "未找到元素", str(params))

        if isinstance(element, dict) and element.get("type") == "coordinate":
            self._driver.tap_coordinate(element["x"], element["y"])
            return OperationResult(success=True, data=element)

        self._driver.double_tap(element)
        return OperationResult(success=True)