"""
输入操作：输入文本、按键、清空
"""
from typing import Any, Dict

from .base import OperationBase, OperationResult
from .registry import operation
from core.errors import OperationError


@operation("输入", "input")
class InputOperation(OperationBase):
    operation_name = "输入"

    def validate(self, params: Dict[str, Any]) -> None:
        value = params.get("value") or params.get("值") or params.get("text")
        if value is None:
            raise OperationError.invalid_params("输入", "value/值/text")

    def _execute(self, params: Dict[str, Any]) -> OperationResult:
        text = self._resolve_value(
            params.get("value") or params.get("值") or params.get("text")
        )
        element = self._find_element(params)
        if element is None:
            raise OperationError.failed("输入", "未找到元素", str(params))

        self._driver.input_text(element, str(text))
        return OperationResult(success=True, data={"text": text})


@operation("按键", "press_key")
class PressKeyOperation(OperationBase):
    operation_name = "按键"

    def validate(self, params: Dict[str, Any]) -> None:
        if not params.get("key") and not params.get("按键"):
            raise OperationError.invalid_params("按键", "key/按键")

    def _execute(self, params: Dict[str, Any]) -> OperationResult:
        key = self._resolve_value(params.get("key") or params.get("按键"))
        self._driver.press_key(str(key))
        return OperationResult(success=True, data={"key": key})


@operation("清空", "clear")
class ClearOperation(OperationBase):
    operation_name = "清空"

    def _execute(self, params: Dict[str, Any]) -> OperationResult:
        element = self._find_element(params)
        if element is None:
            raise OperationError.failed("清空", "未找到元素", str(params))

        self._driver.clear_text(element)
        return OperationResult(success=True)