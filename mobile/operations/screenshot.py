"""
截图操作
"""
import os
import time
from typing import Any, Dict

from .base import OperationBase, OperationResult
from .registry import operation


@operation("截图", "screenshot")
class ScreenshotOperation(OperationBase):
    operation_name = "截图"

    def _execute(self, params: Dict[str, Any]) -> OperationResult:
        path = params.get("path") or params.get("路径")

        if not path:
            timestamp = int(time.time())
            path = f"screenshots/screenshot_{timestamp}.png"

        # 确保目录存在
        dir_path = os.path.dirname(path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)

        self._driver.screenshot(path)
        return OperationResult(success=True, data={"path": path})