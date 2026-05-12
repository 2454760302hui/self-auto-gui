"""
Security 安全测试框架核心模块
"""
from .errors import SecurityError, ScannerError, ReportError, AuthError
from .config import ScanConfig, AuthConfig, load_config
from .scanner import Scanner
from .report_parser import (
    VulnFinding, ReportSummary,
    parse_json_report, generate_summary, filter_by_severity,
    assert_no_critical, assert_no_high, assert_max_severity,
    format_summary_table,
)
from .auth_handler import login_with_selenium, login_with_requests, get_auth_headers

__all__ = [
    "SecurityError", "ScannerError", "ReportError", "AuthError",
    "ScanConfig", "AuthConfig", "load_config",
    "Scanner",
    "VulnFinding", "ReportSummary",
    "parse_json_report", "generate_summary", "filter_by_severity",
    "assert_no_critical", "assert_no_high", "assert_max_severity",
    "format_summary_table",
    "login_with_selenium", "login_with_requests", "get_auth_headers",
]