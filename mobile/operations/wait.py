"""
等待操作
"""
import time
from typing import Any, Dict

from .base import OperationBase, OperationResult
from .registry import operation
from core.errors import LocatorError


@operation("等待", "wait")
class WaitOperation(OperationBase):
    operation_name = "等待"

    def _execute(self, params: Dict[str, Any]) -> OperationResult:
        seconds = min(float(params.get("seconds", params.get("秒", 1.0))), 60.0)
        time.sleep(seconds)
        return OperationResult(success=True, data={"seconds": seconds})


@operation("等待元素", "wait_for")
class WaitForElementOperation(OperationBase):
    operation_name = "等待元素"

    def _execute(self, params: Dict[str, Any]) -> OperationResult:
        timeout = int(params.get("timeout", params.get("超时", 10000)))
        interval = float(params.get("interval", params.get("间隔", 0.5)))

        # 构建定位器配置
        locator_config = {}
        for key in ("定位器", "locator", "元素", "element", "名称", "name"):
            if key in params:
                locator_config[key] = params[key]

        if not locator_config:
            return OperationResult(success=False, error="未指定定位方式")

        element = self._driver.wait_for_element(locator_config, timeout, interval)
        if element is None:
            raise LocatorError.timeout(str(locator_config), timeout)

        return OperationResult(success=True, data={"found": True})