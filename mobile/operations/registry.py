"""
操作注册表
"""
from typing import Any, Callable, Dict, List, Optional, Set


class OperationRegistry:
    """操作注册表（单例）"""

    _instance: Optional["OperationRegistry"] = None
    _operations: Dict[str, type] = {}

    def __new__(cls) -> "OperationRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register(cls, *names: str) -> Callable:
        """注册操作装饰器"""
        def decorator(operation_class: type) -> type:
            for name in names:
                cls._operations[name] = operation_class
            return operation_class
        return decorator

    @classmethod
    def get_handler(cls, name: str) -> Optional[type]:
        """获取操作处理类"""
        return cls._operations.get(name)

    @classmethod
    def has_operation(cls, name: str) -> bool:
        """检查操作是否已注册"""
        return name in cls._operations

    @classmethod
    def get_operation_names(cls) -> Set[str]:
        """获取所有已注册操作名称"""
        return set(cls._operations.keys())

    @classmethod
    def clear(cls) -> None:
        """清空注册表"""
        cls._operations.clear()


def operation(*names: str) -> Callable:
    """操作注册装饰器（快捷方式）"""
    return OperationRegistry.register(*names)