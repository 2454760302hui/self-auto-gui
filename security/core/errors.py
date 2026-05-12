"""
安全测试框架错误体系
"""
from typing import Any, Dict, List, Optional


class SecurityError(Exception):
    """安全测试框架基础异常"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        return {"error": self.message, "details": self.details}


class ScannerError(SecurityError):
    """扫描器错误（启动/执行失败）"""

    @classmethod
    def binary_not_found(cls, name: str, path: str) -> "ScannerError":
        return cls(f"扫描器二进制不存在: {name}", {"name": name, "path": path})

    @classmethod
    def start_failed(cls, name: str, reason: str) -> "ScannerError":
        return cls(f"扫描器启动失败: {name}", {"name": name, "reason": reason})

    @classmethod
    def scan_failed(cls, target: str, reason: str) -> "ScannerError":
        return cls(f"扫描目标失败: {target}", {"target": target, "reason": reason})

    @classmethod
    def prerequisite_missing(cls, items: List[str]) -> "ScannerError":
        return cls(f"缺少必要文件: {', '.join(items)}", {"missing": items})


class ReportError(SecurityError):
    """报告错误（解析/生成失败）"""

    @classmethod
    def file_not_found(cls, path: str) -> "ReportError":
        return cls(f"报告文件不存在: {path}", {"path": path})

    @classmethod
    def parse_failed(cls, path: str, reason: str) -> "ReportError":
        return cls(f"报告解析失败: {path}", {"path": path, "reason": reason})

    @classmethod
    def no_findings(cls, path: str) -> "ReportError":
        return cls(f"报告中无漏洞数据: {path}", {"path": path})


class AuthError(SecurityError):
    """认证错误"""

    @classmethod
    def login_failed(cls, url: str, reason: str) -> "AuthError":
        return cls(f"登录失败: {url}", {"url": url, "reason": reason})

    @classmethod
    def no_cookie(cls, url: str) -> "AuthError":
        return cls(f"登录后未获取到 Cookie: {url}", {"url": url})

    @classmethod
    def browser_not_available(cls) -> "AuthError":
        return cls("Selenium/Chrome 不可用", {})
