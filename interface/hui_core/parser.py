"""
YAML 用例解析器
提供 RunYaml 的别名导入，保持向后兼容性。
实际执行逻辑在 runner.RunYaml 中。
"""
from .runner import RunYaml  # noqa: F401

__all__ = ["RunYaml"]
