"""
Mobile 自动化框架错误体系
"""
from typing import Any, Dict, List, Optional


class ErrorCode:
    """错误码定义"""

    # 配置相关
    CONFIG_FILE_NOT_FOUND = "CONFIG_001"
    CONFIG_PARSE_ERROR = "CONFIG_002"
    CONFIG_VALIDATION_ERROR = "CONFIG_003"
    CONFIG_MISSING_REQUIRED = "CONFIG_004"
    CONFIG_INVALID_OPERATION = "CONFIG_005"
    CONFIG_INVALID_PLATFORM = "CONFIG_006"

    # 定位相关
    LOCATOR_NOT_FOUND = "LOCATOR_001"
    LOCATOR_MULTIPLE_MATCH = "LOCATOR_002"
    LOCATOR_TIMEOUT = "LOCATOR_003"
    LOCATOR_INVALID_FORMAT = "LOCATOR_004"
    LOCATOR_STRATEGY_FAILED = "LOCATOR_005"

    # 操作相关
    OPERATION_FAILED = "OPERATION_001"
    OPERATION_TIMEOUT = "OPERATION_002"
    OPERATION_NOT_SUPPORTED = "OPERATION_003"
    OPERATION_INVALID_PARAMS = "OPERATION_004"

    # 断言相关
    ASSERT_FAILED = "ASSERT_001"
    ASSERT_VALUE_MISMATCH = "ASSERT_002"
    ASSERT_ELEMENT_NOT_VISIBLE = "ASSERT_003"
    ASSERT_ELEMENT_NOT_EXISTS = "ASSERT_004"

    # 设备相关
    DEVICE_NOT_CONNECTED = "DEVICE_001"
    DEVICE_TIMEOUT = "DEVICE_002"
    DEVICE_APP_NOT_INSTALLED = "DEVICE_003"
    DEVICE_APP_CRASH = "DEVICE_004"
    DEVICE_DRIVER_INIT_FAILED = "DEVICE_005"

    # 平台相关
    PLATFORM_NOT_SUPPORTED = "PLATFORM_001"
    PLATFORM_DRIVER_INIT_FAILED = "PLATFORM_002"


class MobileError(Exception):
    """Mobile 框架基础异常类"""

    error_code: str = "MOBILE_000"

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None,
    ):
        self.message = message
        self.error_code = error_code or self.error_code
        self.details = details or {}
        self.suggestions = suggestions or []
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        parts = [f"[{self.error_code}] {self.message}"]
        if self.details:
            for key, value in self.details.items():
                parts.append(f"  {key}: {value}")
        if self.suggestions:
            parts.append("  建议:")
            for i, suggestion in enumerate(self.suggestions, 1):
                parts.append(f"    {i}. {suggestion}")
        return "\n".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "suggestions": self.suggestions,
        }


class ConfigError(MobileError):
    """配置错误"""

    error_code = ErrorCode.CONFIG_VALIDATION_ERROR

    @classmethod
    def file_not_found(cls, file_path: str) -> "ConfigError":
        return cls(
            f"配置文件不存在: {file_path}",
            error_code=ErrorCode.CONFIG_FILE_NOT_FOUND,
            suggestions=[
                "检查文件路径是否正确",
                "确认文件名拼写无误",
                "使用绝对路径避免路径问题",
            ],
        )

    @classmethod
    def parse_error(cls, file_path: str, error: str) -> "ConfigError":
        return cls(
            f"配置文件解析失败: {file_path}",
            error_code=ErrorCode.CONFIG_PARSE_ERROR,
            details={"原始错误": error},
            suggestions=[
                "检查 YAML 语法是否正确",
                "确认缩进使用空格而非 Tab",
            ],
        )

    @classmethod
    def missing_required(cls, field: str, parent: str = None) -> "ConfigError":
        location = f"{parent}.{field}" if parent else field
        return cls(
            f"缺少必需字段: {location}",
            error_code=ErrorCode.CONFIG_MISSING_REQUIRED,
            suggestions=[
                f"在配置中添加 '{field}' 字段",
                "参考文档中的配置示例",
            ],
        )

    @classmethod
    def invalid_operation(cls, operation: str, valid_operations: List[str] = None) -> "ConfigError":
        details = {}
        if valid_operations:
            details["支持的操作"] = ", ".join(valid_operations[:10]) + "..."
        return cls(
            f"未知的操作类型: {operation}",
            error_code=ErrorCode.CONFIG_INVALID_OPERATION,
            details=details,
            suggestions=[
                "检查操作名称拼写",
                "查看文档了解支持的操作类型",
            ],
        )

    @classmethod
    def invalid_platform(cls, platform: str, supported: List[str]) -> "ConfigError":
        return cls(
            f"不支持的平台: {platform}",
            error_code=ErrorCode.CONFIG_INVALID_PLATFORM,
            details={"支持的平台": ", ".join(supported)},
            suggestions=[f"使用以下平台之一: {', '.join(supported)}"],
        )


class LocatorError(MobileError):
    """定位器错误"""

    error_code = ErrorCode.LOCATOR_NOT_FOUND

    @classmethod
    def not_found(cls, locator: str, tried_strategies: List[str] = None) -> "LocatorError":
        details = {"定位器": locator}
        if tried_strategies:
            details["尝试的策略"] = ", ".join(tried_strategies)
        return cls(
            f"未找到元素: {locator}",
            error_code=ErrorCode.LOCATOR_NOT_FOUND,
            details=details,
            suggestions=[
                "检查元素是否存在于页面上",
                "确认应用是否完全加载",
                "尝试使用其他定位方式",
            ],
        )

    @classmethod
    def multiple_match(cls, locator: str, count: int) -> "LocatorError":
        return cls(
            f"定位器匹配到多个元素: {locator}",
            error_code=ErrorCode.LOCATOR_MULTIPLE_MATCH,
            details={"匹配数量": count},
            suggestions=[
                "使用更精确的定位器",
                "添加更多限定条件",
            ],
        )

    @classmethod
    def timeout(cls, locator: str, timeout: int) -> "LocatorError":
        return cls(
            f"等待元素超时: {locator}",
            error_code=ErrorCode.LOCATOR_TIMEOUT,
            details={"超时时间": f"{timeout}ms"},
            suggestions=[
                "增加等待时间",
                "检查元素是否动态加载",
            ],
        )

    @classmethod
    def invalid_format(cls, locator: str, reason: str) -> "LocatorError":
        return cls(
            f"定位器格式无效: {locator}",
            error_code=ErrorCode.LOCATOR_INVALID_FORMAT,
            details={"原因": reason},
            suggestions=[
                "检查定位器格式是否正确",
                "参考文档中的定位器格式说明",
            ],
        )


class OperationError(MobileError):
    """操作错误"""

    error_code = ErrorCode.OPERATION_FAILED

    @classmethod
    def failed(cls, operation: str, reason: str, element: str = None) -> "OperationError":
        details = {"操作": operation, "原因": reason}
        if element:
            details["元素"] = element
        return cls(
            f"操作执行失败: {operation}",
            error_code=ErrorCode.OPERATION_FAILED,
            details=details,
            suggestions=[
                "检查元素是否可交互",
                "确认应用状态是否正确",
            ],
        )

    @classmethod
    def not_supported(cls, operation: str) -> "OperationError":
        return cls(
            f"不支持的操作: {operation}",
            error_code=ErrorCode.OPERATION_NOT_SUPPORTED,
            suggestions=[
                "检查操作名称拼写",
                "查看文档了解支持的操作",
            ],
        )

    @classmethod
    def invalid_params(cls, operation: str, param: str) -> "OperationError":
        return cls(
            f"操作 '{operation}' 缺少必需参数: {param}",
            error_code=ErrorCode.OPERATION_INVALID_PARAMS,
            suggestions=[
                f"添加 '{param}' 参数",
                "参考文档了解参数要求",
            ],
        )


class AssertFailError(MobileError):
    """断言错误"""

    error_code = ErrorCode.ASSERT_FAILED

    @classmethod
    def value_mismatch(cls, expected: Any, actual: Any, element: str = None) -> "AssertFailError":
        details = {"期望值": expected, "实际值": actual}
        if element:
            details["元素"] = element
        return cls(
            "断言失败: 值不匹配",
            error_code=ErrorCode.ASSERT_VALUE_MISMATCH,
            details=details,
            suggestions=[
                "检查期望值是否正确",
                "确认元素是否正确",
            ],
        )

    @classmethod
    def element_not_visible(cls, element: str) -> "AssertFailError":
        return cls(
            "断言失败: 元素不可见",
            error_code=ErrorCode.ASSERT_ELEMENT_NOT_VISIBLE,
            details={"元素": element},
            suggestions=[
                "检查元素是否被隐藏",
                "确认应用是否正确加载",
            ],
        )

    @classmethod
    def element_not_exists(cls, element: str) -> "AssertFailError":
        return cls(
            "断言失败: 元素不存在",
            error_code=ErrorCode.ASSERT_ELEMENT_NOT_EXISTS,
            details={"元素": element},
            suggestions=[
                "检查元素是否在当前页面",
                "确认定位器是否正确",
            ],
        )


class DeviceError(MobileError):
    """设备错误"""

    error_code = ErrorCode.DEVICE_NOT_CONNECTED

    @classmethod
    def not_connected(cls, device: str) -> "DeviceError":
        return cls(
            f"设备未连接: {device}",
            error_code=ErrorCode.DEVICE_NOT_CONNECTED,
            details={"设备": device},
            suggestions=[
                "检查设备是否已连接",
                "确认 USB 调试已开启",
                "运行 adb devices 检查设备列表",
            ],
        )

    @classmethod
    def app_crash(cls, package: str) -> "DeviceError":
        return cls(
            f"应用崩溃: {package}",
            error_code=ErrorCode.DEVICE_APP_CRASH,
            details={"包名": package},
            suggestions=[
                "检查应用是否正常运行",
                "查看 logcat 日志了解崩溃原因",
            ],
        )

    @classmethod
    def driver_init_failed(cls, platform: str, reason: str) -> "DeviceError":
        return cls(
            f"驱动初始化失败: {platform}",
            error_code=ErrorCode.DEVICE_DRIVER_INIT_FAILED,
            details={"平台": platform, "原因": reason},
            suggestions=[
                "确认驱动依赖已安装",
                "检查设备连接状态",
            ],
        )
