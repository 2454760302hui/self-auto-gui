"""
操作基类
"""
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from drivers.base import PlatformDriver
from core.locator import SmartLocator
from core.variable import VariableResolver
from core.errors import OperationError


@dataclass
class OperationResult:
    """操作执行结果"""
    success: bool = True
    error: Optional[str] = None
    data: Any = None
    retried: int = 0
    recovered: bool = False
    strategy: Optional[str] = None
    duration: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "error": self.error,
            "data": self.data,
            "retried": self.retried,
            "recovered": self.recovered,
            "strategy": self.strategy,
            "duration": self.duration,
        }


class OperationBase(ABC):
    """操作基类"""

    operation_name: str = ""

    def __init__(
        self,
        driver: PlatformDriver,
        locator: SmartLocator,
        resolver: VariableResolver,
    ):
        self._driver = driver
        self._locator = locator
        self._resolver = resolver

    def execute(self, params: Dict[str, Any]) -> OperationResult:
        """执行操作（模板方法）"""
        start_time = time.time()
        try:
            self.validate(params)
            result = self._execute(params)
            result.duration = time.time() - start_time
            return result
        except OperationError as e:
            return OperationResult(
                success=False,
                error=str(e),
                duration=time.time() - start_time,
            )
        except Exception as e:
            return OperationResult(
                success=False,
                error=f"{type(e).__name__}: {e}",
                duration=time.time() - start_time,
            )

    def validate(self, params: Dict[str, Any]) -> None:
        """验证参数（子类可覆盖）"""
        pass

    @abstractmethod
    def _execute(self, params: Dict[str, Any]) -> OperationResult:
        """执行操作（子类实现）"""

    def _find_element(self, params: Dict[str, Any]) -> Optional[Any]:
        """查找元素"""
        return self._locator.locate(params)

    def _resolve_value(self, value: Any) -> Any:
        """解析变量"""
        return self._resolver.resolve(value)