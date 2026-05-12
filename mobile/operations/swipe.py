"""
滑动操作：滑动、滚动、捏合、放大
"""
from typing import Any, Dict

from .base import OperationBase, OperationResult
from .registry import operation
from core.errors import OperationError


@operation("滑动", "swipe")
class SwipeOperation(OperationBase):
    operation_name = "滑动"

    def validate(self, params: Dict[str, Any]) -> None:
        direction = params.get("direction") or params.get("方向")
        if not direction:
            raise OperationError.invalid_params("滑动", "direction/方向")

    def _execute(self, params: Dict[str, Any]) -> OperationResult:
        direction = self._resolve_value(params.get("direction") or params.get("方向"))
        valid_directions = {"up", "down", "left", "right"}
        if direction not in valid_directions:
            raise OperationError.failed(
                "滑动", f"无效方向: {direction}", f"支持: {', '.join(valid_directions)}"
            )

        kwargs = {}
        scale = params.get("scale", params.get("比例"))
        if scale:
            kwargs["scale"] = float(scale)

        self._driver.swipe(direction, **kwargs)
        return OperationResult(success=True, data={"direction": direction})


@operation("滚动", "scroll")
class ScrollOperation(OperationBase):
    operation_name = "滚动"

    def _execute(self, params: Dict[str, Any]) -> OperationResult:
        text = self._resolve_value(params.get("text") or params.get("文本"))
        if text:
            self._driver.scroll_to_text(text)
            return OperationResult(success=True, data={"text": text})

        direction = self._resolve_value(params.get("direction") or params.get("方向", "down"))
        self._driver.swipe(direction)
        return OperationResult(success=True, data={"direction": direction})


@operation("捏合", "pinch")
class PinchOperation(OperationBase):
    operation_name = "捏合"

    def _execute(self, params: Dict[str, Any]) -> OperationResult:
        scale = float(params.get("scale", params.get("比例", 0.5)))
        element = self._find_element(params)
        if element is None:
            raise OperationError.failed("捏合", "未找到元素", str(params))

        self._driver.pinch(element, scale)
        return OperationResult(success=True, data={"scale": scale})


@operation("放大", "zoom")
class ZoomOperation(OperationBase):
    operation_name = "放大"

    def _execute(self, params: Dict[str, Any]) -> OperationResult:
        scale = float(params.get("scale", params.get("比例", 2.0)))
        element = self._find_element(params)
        if element is None:
            raise OperationError.failed("放大", "未找到元素", str(params))

        self._driver.zoom(element, scale)
        return OperationResult(success=True, data={"scale": scale})