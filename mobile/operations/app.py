"""
应用操作：启动、关闭、安装、卸载
"""
from typing import Any, Dict

from .base import OperationBase, OperationResult
from .registry import operation
from core.errors import OperationError


@operation("启动应用", "launch_app")
class LaunchAppOperation(OperationBase):
    operation_name = "启动应用"

    def validate(self, params: Dict[str, Any]) -> None:
        if not params.get("package") and not params.get("包名"):
            raise OperationError.invalid_params("启动应用", "package/包名")

    def _execute(self, params: Dict[str, Any]) -> OperationResult:
        package = self._resolve_value(params.get("package") or params.get("包名"))
        activity = self._resolve_value(params.get("activity") or params.get("活动"))
        self._driver.launch_app(package, activity)
        return OperationResult(success=True, data={"package": package, "activity": activity})


@operation("关闭应用", "close_app")
class CloseAppOperation(OperationBase):
    operation_name = "关闭应用"

    def validate(self, params: Dict[str, Any]) -> None:
        if not params.get("package") and not params.get("包名"):
            raise OperationError.invalid_params("关闭应用", "package/包名")

    def _execute(self, params: Dict[str, Any]) -> OperationResult:
        package = self._resolve_value(params.get("package") or params.get("包名"))
        self._driver.close_app(package)
        return OperationResult(success=True, data={"package": package})


@operation("安装应用", "install_app")
class InstallAppOperation(OperationBase):
    operation_name = "安装应用"

    def validate(self, params: Dict[str, Any]) -> None:
        if not params.get("path") and not params.get("路径"):
            raise OperationError.invalid_params("安装应用", "path/路径")

    def _execute(self, params: Dict[str, Any]) -> OperationResult:
        app_path = self._resolve_value(params.get("path") or params.get("路径"))
        self._driver.install_app(app_path)
        return OperationResult(success=True, data={"path": app_path})


@operation("卸载应用", "uninstall_app")
class UninstallAppOperation(OperationBase):
    operation_name = "卸载应用"

    def validate(self, params: Dict[str, Any]) -> None:
        if not params.get("package") and not params.get("包名"):
            raise OperationError.invalid_params("卸载应用", "package/包名")

    def _execute(self, params: Dict[str, Any]) -> OperationResult:
        package = self._resolve_value(params.get("package") or params.get("包名"))
        self._driver.uninstall_app(package)
        return OperationResult(success=True, data={"package": package})