"""
断言操作
"""
from typing import Any, Dict

from .base import OperationBase, OperationResult
from .registry import operation
from core.errors import AssertFailError, OperationError


@operation("断言", "assert", "验证")
class AssertOperation(OperationBase):
    operation_name = "断言"

    def _execute(self, params: Dict[str, Any]) -> OperationResult:
        # 确定断言模式
        if "visible" in params or "可见" in params:
            return self._assert_visible(params)
        elif "text" in params or "文本" in params:
            return self._assert_text(params)
        elif "attribute" in params or "属性" in params:
            return self._assert_attribute(params)
        elif "exists" in params or "存在" in params:
            return self._assert_exists(params)
        else:
            # 默认断言元素可见
            return self._assert_visible(params)

    def _assert_visible(self, params: Dict[str, Any]) -> OperationResult:
        """断言元素可见性"""
        expected = params.get("visible", params.get("可见", True))
        element = self._find_element(params)

        if element is None:
            if expected:
                raise AssertFailError.element_not_visible(str(params))
            return OperationResult(success=True, data={"visible": False})

        actual = self._driver.is_visible(element)
        if bool(actual) != bool(expected):
            raise AssertFailError.element_not_visible(str(params))

        return OperationResult(success=True, data={"visible": actual})

    def _assert_text(self, params: Dict[str, Any]) -> OperationResult:
        """断言元素文本"""
        expected = self._resolve_value(params.get("text") or params.get("文本"))
        element = self._find_element(params)

        if element is None:
            raise OperationError.failed("断言", "未找到元素", str(params))

        actual = self._driver.get_text(element)
        if actual != expected:
            raise AssertFailError.value_mismatch(expected, actual, str(params))

        return OperationResult(success=True, data={"text": actual})

    def _assert_attribute(self, params: Dict[str, Any]) -> OperationResult:
        """断言元素属性"""
        attr_name = params.get("attribute") or params.get("属性")
        expected = self._resolve_value(params.get("value") or params.get("值"))
        element = self._find_element(params)

        if element is None:
            raise OperationError.failed("断言", "未找到元素", str(params))

        actual = self._driver.get_attribute(element, attr_name)
        if actual != expected:
            raise AssertFailError.value_mismatch(expected, actual, str(params))

        return OperationResult(success=True, data={attr_name: actual})

    def _assert_exists(self, params: Dict[str, Any]) -> OperationResult:
        """断言元素是否存在"""
        expected = params.get("exists", params.get("存在", True))
        element = self._find_element(params)

        actual = element is not None
        if actual != bool(expected):
            if expected:
                raise AssertFailError.element_not_exists(str(params))
            else:
                raise AssertFailError(
                    "断言失败: 元素不应存在",
                    details={"元素": str(params)},
                )

        return OperationResult(success=True, data={"exists": actual})