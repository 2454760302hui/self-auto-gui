"""
设备操作：获取设备信息、旋转设备、硬件按键
"""
from typing import Any, Dict

from .base import OperationBase, OperationResult
from .registry import operation
from core.errors import OperationError


@operation("获取设备信息", "get_device_info")
class GetDeviceInfoOperation(OperationBase):
    operation_name = "获取设备信息"

    def _execute(self, params: Dict[str, Any]) -> OperationResult:
        info = self._driver.get_device_info()
        return OperationResult(success=True, data=info)


@operation("旋转设备", "rotate_device")
class RotateDeviceOperation(OperationBase):
    operation_name = "旋转设备"

    def validate(self, params: Dict[str, Any]) -> None:
        orientation = params.get("orientation") or params.get("方向")
        if not orientation:
            raise OperationError.invalid_params("旋转设备", "orientation/方向")

    def _execute(self, params: Dict[str, Any]) -> OperationResult:
        orientation = self._resolve_value(params.get("orientation") or params.get("方向"))
        valid = {"portrait", "landscape", "left", "right"}
        if orientation not in valid:
            raise OperationError.failed(
                "旋转设备", f"无效方向: {orientation}", f"支持: {', '.join(valid)}"
            )

        self._driver.rotate_device(orientation)
        return OperationResult(success=True, data={"orientation": orientation})


@operation("硬件按键", "hardware_key")
class HardwareKeyOperation(OperationBase):
    operation_name = "硬件按键"

    def validate(self, params: Dict[str, Any]) -> None:
        if not params.get("key") and not params.get("按键"):
            raise OperationError.invalid_params("硬件按键", "key/按键")

    def _execute(self, params: Dict[str, Any]) -> OperationResult:
        key = self._resolve_value(params.get("key") or params.get("按键"))
        self._driver.press_key(str(key))
        return OperationResult(success=True, data={"key": key})