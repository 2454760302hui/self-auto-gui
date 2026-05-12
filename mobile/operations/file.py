"""
文件操作：拉取文件、推送文件
"""
from typing import Any, Dict

from .base import OperationBase, OperationResult
from .registry import operation
from core.errors import OperationError


@operation("拉取文件", "pull_file")
class PullFileOperation(OperationBase):
    operation_name = "拉取文件"

    def validate(self, params: Dict[str, Any]) -> None:
        if not params.get("remote") and not params.get("远程路径"):
            raise OperationError.invalid_params("拉取文件", "remote/远程路径")
        if not params.get("local") and not params.get("本地路径"):
            raise OperationError.invalid_params("拉取文件", "local/本地路径")

    def _execute(self, params: Dict[str, Any]) -> OperationResult:
        remote = self._resolve_value(params.get("remote") or params.get("远程路径"))
        local = self._resolve_value(params.get("local") or params.get("本地路径"))
        self._driver.pull_file(remote, local)
        return OperationResult(success=True, data={"remote": remote, "local": local})


@operation("推送文件", "push_file")
class PushFileOperation(OperationBase):
    operation_name = "推送文件"

    def validate(self, params: Dict[str, Any]) -> None:
        if not params.get("local") and not params.get("本地路径"):
            raise OperationError.invalid_params("推送文件", "local/本地路径")
        if not params.get("remote") and not params.get("远程路径"):
            raise OperationError.invalid_params("推送文件", "remote/远程路径")

    def _execute(self, params: Dict[str, Any]) -> OperationResult:
        local = self._resolve_value(params.get("local") or params.get("本地路径"))
        remote = self._resolve_value(params.get("remote") or params.get("远程路径"))
        self._driver.push_file(local, remote)
        return OperationResult(success=True, data={"local": local, "remote": remote})