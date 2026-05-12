"""
配置加载与验证
支持 Mobile YAML DSL 格式的配置文件
"""
import os
from typing import Any, Dict, List, Optional, Set

import yaml
from pydantic import BaseModel, Field

from .errors import ConfigError, ErrorCode


# --- Pydantic 模型 ---

class PlatformConfig(BaseModel):
    """平台配置"""
    platform: str = "android"
    device: str = ""
    app: str = ""


class ScreenshotConfig(BaseModel):
    """截图配置"""
    on_fail: bool = True
    dir: str = "screenshots"


class RetryConfig(BaseModel):
    """重试配置"""
    max_count: int = 3
    interval: float = 1.0


class WaitConfig(BaseModel):
    """等待配置"""
    timeout: int = 10000
    interval: float = 0.5


class GlobalConfig(BaseModel):
    """全局配置"""
    name: str = ""
    platform: PlatformConfig = PlatformConfig()
    screenshot: ScreenshotConfig = ScreenshotConfig()
    retry: RetryConfig = RetryConfig()
    wait: WaitConfig = WaitConfig()


class LocatorConfig(BaseModel):
    """定位器配置"""
    primary: str = ""
    fallback: List[str] = Field(default_factory=list)


# --- 保留字 ---

RESERVED_KEYS = {"config", "locators", "aliases", "test_data"}


# --- 验证器 ---

class ConfigValidator:
    """配置验证器"""

    SUPPORTED_PLATFORMS: Set[str] = {"android", "ios", "harmony"}

    SUPPORTED_OPERATIONS: Set[str] = {
        # 应用操作
        "启动应用", "launch_app", "关闭应用", "close_app",
        "安装应用", "install_app", "卸载应用", "uninstall_app",
        # 点击操作
        "点击", "tap", "长按", "long_press", "双击", "double_tap",
        # 输入操作
        "输入", "input", "按键", "press_key", "清空", "clear",
        # 滑动操作
        "滑动", "swipe", "滚动", "scroll", "捏合", "pinch", "放大", "zoom",
        # 断言操作
        "断言", "assert", "验证",
        # 等待操作
        "等待", "wait", "等待元素", "wait_for",
        # 截图操作
        "截图", "screenshot",
        # 设备操作
        "获取设备信息", "get_device_info", "旋转设备", "rotate_device",
        "硬件按键", "hardware_key",
        # 文件操作
        "拉取文件", "pull_file", "推送文件", "push_file",
        # 设置变量
        "设置变量", "set_variable", "set",
    }

    def __init__(self):
        self._errors: List[Dict[str, Any]] = []
        self._warnings: List[Dict[str, Any]] = []

    def validate(self, config: Dict[str, Any]) -> bool:
        """验证配置，返回是否有效"""
        self._errors.clear()
        self._warnings.clear()

        self._validate_global(config)
        self._validate_locators(config)
        self._validate_flows(config)

        return len(self._errors) == 0

    def get_errors(self) -> List[Dict[str, Any]]:
        return list(self._errors)

    def get_warnings(self) -> List[Dict[str, Any]]:
        return list(self._warnings)

    def get_report(self) -> str:
        parts = []
        if self._errors:
            parts.append(f"发现 {len(self._errors)} 个错误:")
            for err in self._errors:
                parts.append(f"  - {err['message']}")
        if self._warnings:
            parts.append(f"发现 {len(self._warnings)} 个警告:")
            for warn in self._warnings:
                parts.append(f"  - {warn['message']}")
        if not self._errors and not self._warnings:
            parts.append("配置验证通过，无错误和警告")
        return "\n".join(parts)

    def _validate_global(self, config: Dict[str, Any]) -> None:
        """验证全局配置"""
        global_config = config.get("config", {})
        if not global_config:
            self._warnings.append({
                "message": "缺少 config 全局配置",
                "suggestion": "建议添加 config 配置指定平台和设备",
            })
            return

        platform = global_config.get("platform", "")
        if platform and platform not in self.SUPPORTED_PLATFORMS:
            self._errors.append({
                "message": f"不支持的平台: {platform}",
                "suggestion": f"支持的平台: {', '.join(self.SUPPORTED_PLATFORMS)}",
            })

        device = global_config.get("device", "")
        if not device:
            self._warnings.append({
                "message": "未指定设备地址",
                "suggestion": "建议在 config 中指定 device",
            })

    def _validate_locators(self, config: Dict[str, Any]) -> None:
        """验证定位器配置"""
        locators = config.get("locators", {})
        if not locators:
            return

        for name, locator_config in locators.items():
            if isinstance(locator_config, dict):
                if not locator_config.get("primary"):
                    self._warnings.append({
                        "message": f"定位器 '{name}' 缺少 primary",
                        "suggestion": "建议为定位器指定 primary 定位方式",
                    })

    def _validate_flows(self, config: Dict[str, Any]) -> None:
        """验证流程配置"""
        flows = self._detect_flows(config)
        if not flows:
            self._warnings.append({
                "message": "未发现任何测试流程",
                "suggestion": "在 YAML 中添加测试流程（顶层 key 值为步骤列表）",
            })
            return

        for flow_name, steps in flows.items():
            if not isinstance(steps, list):
                self._errors.append({
                    "message": f"流程 '{flow_name}' 不是列表格式",
                    "suggestion": "流程应为步骤列表",
                })
                continue

            for i, step in enumerate(steps):
                if not isinstance(step, dict):
                    self._errors.append({
                        "message": f"流程 '{flow_name}' 步骤 {i+1} 不是字典格式",
                    })
                    continue
                self._validate_step(flow_name, i + 1, step)

    def _validate_step(self, flow_name: str, step_num: int, step: Dict[str, Any]) -> None:
        """验证单个步骤"""
        # 提取操作类型（忽略 name 键）
        op_keys = [k for k in step.keys() if k not in ("name", "名称")]
        if not op_keys:
            self._errors.append({
                "message": f"流程 '{flow_name}' 步骤 {step_num} 缺少操作类型",
            })
            return

        if len(op_keys) > 1:
            self._warnings.append({
                "message": f"流程 '{flow_name}' 步骤 {step_num} 有多个操作键: {op_keys}",
                "suggestion": "每个步骤应只有一个操作类型",
            })

        op_type = op_keys[0]
        if op_type not in self.SUPPORTED_OPERATIONS:
            self._warnings.append({
                "message": f"流程 '{flow_name}' 步骤 {step_num}: 未知操作 '{op_type}'",
                "suggestion": "检查操作名称拼写，或查看文档了解支持的操作",
            })

    @staticmethod
    def _detect_flows(config: Dict[str, Any]) -> Dict[str, Any]:
        """自动检测流程：顶层 key 值为步骤列表的即为流程"""
        flows = {}
        for key, value in config.items():
            if key in RESERVED_KEYS:
                continue
            if isinstance(value, list):
                flows[key] = value
        return flows


# --- 加载器 ---

class ConfigLoader:
    """配置加载器"""

    def __init__(self, config_path: str = None, config: Dict[str, Any] = None):
        self._config_path = config_path
        self._config: Optional[Dict[str, Any]] = config
        self._validator = ConfigValidator()
        self._loaded = False

    def load(self, validate: bool = True) -> Dict[str, Any]:
        """加载配置"""
        if self._config is not None:
            config = self._config
        elif self._config_path:
            config = self._load_from_file(self._config_path)
        else:
            raise ConfigError.missing_required("config_path 或 config")

        self._config = config
        self._loaded = True

        if validate:
            self._validator.validate(config)

        return config

    def validate(self) -> bool:
        """验证配置"""
        if not self._config:
            self.load(validate=False)
        return self._validator.validate(self._config)

    def get_config(self) -> Dict[str, Any]:
        """获取完整配置"""
        if not self._loaded:
            self.load(validate=False)
        return self._config

    def get_global_config(self) -> GlobalConfig:
        """获取全局配置（Pydantic 模型）"""
        config = self.get_config()
        raw_global = config.get("config", {})

        # 将 config 中的字段映射到 GlobalConfig
        platform_data = {}
        for field in ("platform", "device", "app"):
            if field in raw_global:
                platform_data[field] = raw_global[field]

        global_data = {"name": raw_global.get("name", "")}
        if platform_data:
            global_data["platform"] = platform_data

        return GlobalConfig(**global_data)

    def get_flows(self) -> Dict[str, Any]:
        """获取所有流程"""
        config = self.get_config()
        return ConfigValidator._detect_flows(config)

    def get_locators(self) -> Dict[str, Any]:
        """获取定位器库"""
        config = self.get_config()
        return config.get("locators", {})

    def get_aliases(self) -> Dict[str, str]:
        """获取别名"""
        config = self.get_config()
        return config.get("aliases", {})

    def get_test_data(self) -> Dict[str, Any]:
        """获取测试数据"""
        config = self.get_config()
        return config.get("test_data", {})

    def get_validation_report(self) -> str:
        """获取验证报告"""
        return self._validator.get_report()

    def _load_from_file(self, file_path: str) -> Dict[str, Any]:
        """从文件加载配置"""
        if not os.path.exists(file_path):
            raise ConfigError.file_not_found(file_path)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigError.parse_error(file_path, str(e))

        if not isinstance(content, dict):
            raise ConfigError.parse_error(file_path, "配置文件内容不是字典格式")

        return content
