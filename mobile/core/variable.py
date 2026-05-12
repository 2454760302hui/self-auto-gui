"""
变量解析器
支持 ${var}, @{data}, ${date}, ${datetime}, ${timestamp}, ${random} 等变量替换
"""
import re
import random
from datetime import datetime
from typing import Any, Dict, List, Optional


class VariableResolver:
    """变量解析器"""

    RESERVED_KEYS = {"config", "locators", "aliases", "test_data"}

    def __init__(
        self,
        variables: Optional[Dict[str, Any]] = None,
        test_data: Optional[Dict[str, Any]] = None,
        aliases: Optional[Dict[str, str]] = None,
    ):
        self._variables: Dict[str, Any] = variables or {}
        self._test_data: Dict[str, Any] = test_data or {}
        self._aliases: Dict[str, str] = aliases or {}

    def resolve(self, value: Any) -> Any:
        """递归解析变量"""
        if isinstance(value, str):
            return self._resolve_string(value)
        elif isinstance(value, dict):
            return {k: self.resolve(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self.resolve(item) for item in value]
        return value

    def set_variable(self, name: str, value: Any) -> None:
        """设置变量"""
        self._variables[name] = value

    def get_variable(self, name: str, default: Any = None) -> Any:
        """获取变量"""
        return self._variables.get(name, default)

    def resolve_element_name(self, name: str) -> str:
        """通过别名解析元素名称"""
        return self._aliases.get(name, name)

    def _resolve_string(self, value: str) -> Any:
        """解析字符串中的变量"""
        # 先处理 @{data} 测试数据引用
        value = self._resolve_test_data(value)
        # 再处理 ${var} 变量引用
        value = self._resolve_variables(value)
        return value

    def _resolve_test_data(self, value: str) -> str:
        """解析 @{data} 测试数据引用"""
        pattern = r'@\{(\w+)\}'

        def replace_match(match):
            key = match.group(1)
            if key in self._test_data:
                data = self._test_data[key]
                if isinstance(data, list):
                    return str(random.choice(data))
                return str(data)
            return match.group(0)

        return re.sub(pattern, replace_match, value)

    def _resolve_variables(self, value: str) -> Any:
        """解析 ${var} 变量引用"""
        pattern = r'\$\{(\w+)\}'

        matches = list(re.finditer(pattern, value))
        if not matches:
            return value

        # 如果整个字符串就是一个变量引用，返回原始类型
        if len(matches) == 1 and matches[0].group(0) == value:
            key = matches[0].group(1)
            resolved = self._resolve_single_variable(key)
            if resolved is not None:
                return resolved
            return value

        # 否则替换为字符串
        def replace_match(match):
            key = match.group(1)
            resolved = self._resolve_single_variable(key)
            if resolved is not None:
                return str(resolved)
            return match.group(0)

        return re.sub(pattern, replace_match, value)

    def _resolve_single_variable(self, key: str) -> Any:
        """解析单个变量"""
        # 内置变量
        if key == "date":
            return datetime.now().strftime("%Y-%m-%d")
        elif key == "datetime":
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        elif key == "timestamp":
            return int(datetime.now().timestamp())
        elif key == "random":
            return f"{random.randint(1000, 9999)}"

        # 用户变量
        if key in self._variables:
            return self._variables[key]

        return None

    @property
    def variables(self) -> Dict[str, Any]:
        return dict(self._variables)

    @property
    def test_data(self) -> Dict[str, Any]:
        return dict(self._test_data)

    @property
    def aliases(self) -> Dict[str, str]:
        return dict(self._aliases)
