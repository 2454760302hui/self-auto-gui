"""
安全测试配置加载
"""
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import yaml

from .errors import SecurityError


@dataclass
class AuthConfig:
    """认证配置"""
    enabled: bool = False
    login_url: str = ""
    username: str = ""
    password: str = ""
    username_selector: str = ""
    password_selector: str = ""
    submit_selector: str = ""
    cookie_domain: str = ""


@dataclass
class ScanConfig:
    """扫描配置"""
    # 二进制路径
    xray_path: str = ""
    rad_path: str = ""
    xray_config: str = ""
    rad_config: str = ""

    # 代理
    proxy: str = "127.0.0.1:7777"

    # 目标
    targets: List[str] = field(default_factory=list)
    targets_file: str = ""

    # 输出
    output_dir: str = "reports"

    # 等待时间
    xray_startup_wait: float = 5.0
    scan_interval: float = 3.0
    result_wait: float = 10.0

    # 并发
    max_concurrent: int = 3

    # 插件
    enabled_plugins: List[str] = field(default_factory=lambda: [
        "baseline", "brute-force", "cmd-injection", "sqldet", "xss", "xxe"
    ])

    # 认证
    auth: AuthConfig = field(default_factory=AuthConfig)

    # 漏洞阈值（用于断言）
    max_critical: int = 0
    max_high: int = 0
    max_medium: int = -1  # -1 表示不限制

    # Xray CA 证书
    ca_cert: str = ""
    ca_key: str = ""


def load_config(config_path: str = None) -> ScanConfig:
    """从 YAML 文件加载配置"""
    if config_path and os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return _dict_to_config(data)

    # 尝试默认路径
    default_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "config", "scan_config.yml"
    )
    if os.path.exists(default_path):
        with open(default_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return _dict_to_config(data)

    # 使用默认配置 + 自动推断路径
    return _auto_detect_paths(ScanConfig())


def _dict_to_config(data: Dict[str, Any]) -> ScanConfig:
    """将字典转为 ScanConfig"""
    config = ScanConfig()

    # 二进制路径
    config.xray_path = data.get("xray_path", config.xray_path)
    config.rad_path = data.get("rad_path", config.rad_path)
    config.xray_config = data.get("xray_config", config.xray_config)
    config.rad_config = data.get("rad_config", config.rad_config)

    # 代理
    config.proxy = data.get("proxy", config.proxy)

    # 目标
    config.targets = data.get("targets", config.targets)
    config.targets_file = data.get("targets_file", config.targets_file)

    # 输出
    config.output_dir = data.get("output_dir", config.output_dir)

    # 等待时间
    config.xray_startup_wait = data.get("xray_startup_wait", config.xray_startup_wait)
    config.scan_interval = data.get("scan_interval", config.scan_interval)
    config.result_wait = data.get("result_wait", config.result_wait)

    # 并发
    config.max_concurrent = data.get("max_concurrent", config.max_concurrent)

    # 插件
    config.enabled_plugins = data.get("enabled_plugins", config.enabled_plugins)

    # 漏洞阈值
    config.max_critical = data.get("max_critical", config.max_critical)
    config.max_high = data.get("max_high", config.max_high)
    config.max_medium = data.get("max_medium", config.max_medium)

    # CA 证书
    config.ca_cert = data.get("ca_cert", config.ca_cert)
    config.ca_key = data.get("ca_key", config.ca_key)

    # 认证
    auth_data = data.get("auth", {})
    if auth_data:
        config.auth = AuthConfig(
            enabled=auth_data.get("enabled", False),
            login_url=auth_data.get("login_url", ""),
            username=auth_data.get("username", ""),
            password=auth_data.get("password", ""),
            username_selector=auth_data.get("username_selector", ""),
            password_selector=auth_data.get("password_selector", ""),
            submit_selector=auth_data.get("submit_selector", ""),
            cookie_domain=auth_data.get("cookie_domain", ""),
        )

    return _auto_detect_paths(config)


def _auto_detect_paths(config: ScanConfig) -> ScanConfig:
    """自动推断 Xray_Rad_complete 目录下的路径"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    xray_dir = os.path.join(base_dir, "Xray_Rad_complete")

    if os.path.exists(xray_dir):
        if not config.xray_path:
            xray_exe = os.path.join(xray_dir, "xray_windows_amd64.exe")
            if os.path.exists(xray_exe):
                config.xray_path = xray_exe

        if not config.rad_path:
            rad_exe = os.path.join(xray_dir, "rad_windows_amd64.exe")
            if os.path.exists(rad_exe):
                config.rad_path = rad_exe

        if not config.xray_config:
            xray_cfg = os.path.join(xray_dir, "config.yaml")
            if os.path.exists(xray_cfg):
                config.xray_config = xray_cfg

        if not config.rad_config:
            rad_cfg = os.path.join(xray_dir, "rad_config.yml")
            if os.path.exists(rad_cfg):
                config.rad_config = rad_cfg

        if not config.targets_file:
            targets = os.path.join(xray_dir, "target.txt")
            if os.path.exists(targets):
                config.targets_file = targets

        if not config.ca_cert:
            ca_crt = os.path.join(xray_dir, "ca.crt")
            if os.path.exists(ca_crt):
                config.ca_cert = ca_crt

        if not config.ca_key:
            ca_key = os.path.join(xray_dir, "ca.key")
            if os.path.exists(ca_key):
                config.ca_key = ca_key

    return config
