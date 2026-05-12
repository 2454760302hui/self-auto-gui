"""
Security 单元测试 — 配置、报告解析、漏洞断言
"""
import os
import json
import tempfile
import pytest
from core.errors import SecurityError, ScannerError, ReportError, AuthError
from core.config import ScanConfig, AuthConfig, load_config, _dict_to_config, _auto_detect_paths
from core.report_parser import (
    VulnFinding, ReportSummary,
    parse_json_report, generate_summary, filter_by_severity,
    assert_no_critical, assert_no_high, assert_max_severity,
    format_summary_table, _infer_severity, _parse_finding,
    SEVERITY_LEVELS,
)


# ════════════════════════════════════════════════════════════════
#  Error hierarchy
# ════════════════════════════════════════════════════════════════
class TestErrors:

    def test_security_error_base(self):
        err = SecurityError("test error", {"key": "val"})
        assert str(err) == "test error"
        d = err.to_dict()
        assert d["error"] == "test error"
        assert d["details"]["key"] == "val"

    def test_scanner_error_binary_not_found(self):
        err = ScannerError.binary_not_found("xray", "/path/xray")
        assert "xray" in str(err)
        assert isinstance(err, SecurityError)

    def test_scanner_error_start_failed(self):
        err = ScannerError.start_failed("xray", "port in use")
        assert "xray" in str(err)
        assert err.details["reason"] == "port in use"

    def test_scanner_error_scan_failed(self):
        err = ScannerError.scan_failed("https://example.com", "timeout")
        assert "example.com" in str(err)

    def test_scanner_error_prerequisite_missing(self):
        err = ScannerError.prerequisite_missing(["xray", "rad"])
        assert "xray" in str(err)

    def test_report_error_file_not_found(self):
        err = ReportError.file_not_found("/path/report.json")
        assert "不存在" in str(err)

    def test_report_error_parse_failed(self):
        err = ReportError.parse_failed("/path/report.json", "bad json")
        assert "解析失败" in str(err)

    def test_report_error_no_findings(self):
        err = ReportError.no_findings("/path/report.json")
        assert "无漏洞" in str(err)

    def test_auth_error_login_failed(self):
        err = AuthError.login_failed("https://login.com", "403")
        assert "登录失败" in str(err)

    def test_auth_error_no_cookie(self):
        err = AuthError.no_cookie("https://login.com")
        assert "Cookie" in str(err)

    def test_auth_error_browser_not_available(self):
        err = AuthError.browser_not_available()
        assert "Selenium" in str(err)


# ════════════════════════════════════════════════════════════════
#  Config
# ════════════════════════════════════════════════════════════════
class TestConfig:

    def test_default_scan_config(self):
        config = ScanConfig()
        assert config.proxy == "127.0.0.1:7777"
        assert config.max_concurrent == 3
        assert config.max_critical == 0
        assert isinstance(config.auth, AuthConfig)

    def test_default_auth_config(self):
        auth = AuthConfig()
        assert auth.enabled is False
        assert auth.login_url == ""

    def test_dict_to_config(self):
        data = {
            "proxy": "127.0.0.1:8888",
            "targets": ["https://example.com"],
            "max_concurrent": 5,
            "auth": {
                "enabled": True,
                "login_url": "https://login.com",
                "username": "admin",
                "password": "pass",
            }
        }
        config = _dict_to_config(data)
        assert config.proxy == "127.0.0.1:8888"
        assert len(config.targets) == 1
        assert config.max_concurrent == 5
        assert config.auth.enabled is True
        assert config.auth.username == "admin"

    def test_load_config_nonexistent_returns_default(self):
        config = load_config("/nonexistent/path.yml")
        assert isinstance(config, ScanConfig)

    def test_auto_detect_paths(self):
        config = _auto_detect_paths(ScanConfig())
        assert isinstance(config, ScanConfig)

    def test_load_config_from_yaml(self):
        yaml_content = """
proxy: "127.0.0.1:9999"
targets:
  - https://example.com
max_concurrent: 2
"""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.yml', delete=False, encoding='utf-8'
        ) as f:
            f.write(yaml_content)
            f.flush()
            try:
                config = load_config(f.name)
                assert config.proxy == "127.0.0.1:9999"
                assert config.max_concurrent == 2
            finally:
                try:
                    os.unlink(f.name)
                except PermissionError:
                    pass


# ════════════════════════════════════════════════════════════════
#  VulnFinding
# ════════════════════════════════════════════════════════════════
class TestVulnFinding:

    def test_severity_level(self):
        f = VulnFinding(severity="critical")
        assert f.severity_level == 4

    def test_is_critical(self):
        f = VulnFinding(severity="critical")
        assert f.is_critical is True
        assert f.is_high is False

    def test_is_high(self):
        f = VulnFinding(severity="high")
        assert f.is_high is True
        assert f.is_critical is False

    def test_to_dict(self):
        f = VulnFinding(plugin="xss", url="https://example.com", severity="high")
        d = f.to_dict()
        assert d["plugin"] == "xss"
        assert d["severity"] == "high"

    def test_unknown_severity_level_is_zero(self):
        f = VulnFinding(severity="unknown")
        assert f.severity_level == 0


# ════════════════════════════════════════════════════════════════
#  Severity Inference
# ════════════════════════════════════════════════════════════════
class TestSeverityInference:

    def test_critical_cmd_injection(self):
        assert _infer_severity("cmd-injection", "", {}) == "critical"

    def test_critical_rce(self):
        assert _infer_severity("rce-exploit", "", {}) == "critical"

    def test_high_sqli(self):
        assert _infer_severity("sqldet", "", {}) == "high"

    def test_high_xss(self):
        assert _infer_severity("xss", "", {}) == "high"

    def test_medium_brute_force(self):
        assert _infer_severity("brute-force", "", {}) == "medium"

    def test_low_baseline(self):
        assert _infer_severity("baseline", "", {}) == "low"

    def test_unknown_is_medium(self):
        assert _infer_severity("some-unknown-plugin", "", {}) == "medium"


# ════════════════════════════════════════════════════════════════
#  Report Parsing
# ════════════════════════════════════════════════════════════════
class TestReportParsing:

    def _make_finding_json(self, plugin="xss", url="https://example.com",
                           vuln_class="", create_time=0, **extra):
        return {
            "plugin": plugin,
            "detail": {"addr": url, **extra},
            "vuln_class": vuln_class,
            "create_time": create_time,
        }

    def test_parse_finding_valid(self):
        item = self._make_finding_json()
        finding = _parse_finding(item)
        assert finding is not None
        assert finding.plugin == "xss"

    def test_parse_finding_no_plugin_returns_none(self):
        finding = _parse_finding({"detail": {}})
        assert finding is None

    def test_parse_finding_non_dict_returns_none(self):
        finding = _parse_finding("not a dict")
        assert finding is None

    def test_parse_json_report_file_not_found(self):
        with pytest.raises(ReportError):
            parse_json_report("/nonexistent/report.json")

    def test_parse_json_report_empty_file(self):
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False, encoding='utf-8'
        ) as f:
            f.write("")
            f.flush()
            try:
                with pytest.raises(ReportError):
                    parse_json_report(f.name)
            finally:
                try:
                    os.unlink(f.name)
                except PermissionError:
                    pass

    def test_parse_json_report_array(self):
        findings_json = [
            self._make_finding_json("xss", "https://a.com"),
            self._make_finding_json("sqldet", "https://b.com"),
        ]
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False, encoding='utf-8'
        ) as f:
            json.dump(findings_json, f)
            f.flush()
            try:
                findings = parse_json_report(f.name)
                assert len(findings) == 2
                assert findings[0].plugin == "xss"
                assert findings[1].plugin == "sqldet"
            finally:
                try:
                    os.unlink(f.name)
                except PermissionError:
                    pass

    def test_parse_json_report_line_delimited(self):
        lines = [
            json.dumps(self._make_finding_json("xss", "https://a.com")),
            json.dumps(self._make_finding_json("baseline", "https://b.com")),
        ]
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False, encoding='utf-8'
        ) as f:
            f.write("\n".join(lines))
            f.flush()
            try:
                findings = parse_json_report(f.name)
                assert len(findings) == 2
            finally:
                try:
                    os.unlink(f.name)
                except PermissionError:
                    pass


# ════════════════════════════════════════════════════════════════
#  Summary
# ════════════════════════════════════════════════════════════════
class TestSummary:

    def _make_findings(self):
        return [
            VulnFinding(plugin="xss", url="https://a.com/page1", severity="high"),
            VulnFinding(plugin="xss", url="https://a.com/page2", severity="high"),
            VulnFinding(plugin="baseline", url="https://b.com", severity="low"),
            VulnFinding(plugin="cmd-injection", url="https://c.com", severity="critical"),
        ]

    def test_generate_summary(self):
        findings = self._make_findings()
        summary = generate_summary(findings)
        assert summary.total == 4
        assert summary.by_severity["high"] == 2
        assert summary.by_severity["critical"] == 1
        assert summary.by_severity["low"] == 1

    def test_generate_summary_by_plugin(self):
        findings = self._make_findings()
        summary = generate_summary(findings)
        assert summary.by_plugin["xss"] == 2
        assert summary.by_plugin["baseline"] == 1

    def test_generate_summary_by_url(self):
        findings = self._make_findings()
        summary = generate_summary(findings)
        assert "https://a.com/page1" in summary.by_url

    def test_summary_to_dict(self):
        findings = self._make_findings()
        summary = generate_summary(findings)
        d = summary.to_dict()
        assert d["total"] == 4
        assert "by_severity" in d

    def test_format_summary_table(self):
        findings = self._make_findings()
        summary = generate_summary(findings)
        table = format_summary_table(summary)
        assert "4" in table
        assert "critical" in table


# ════════════════════════════════════════════════════════════════
#  Filtering & Assertions
# ════════════════════════════════════════════════════════════════
class TestFilterAndAssert:

    def _make_findings(self):
        return [
            VulnFinding(plugin="cmd-injection", severity="critical"),
            VulnFinding(plugin="xss", severity="high"),
            VulnFinding(plugin="brute-force", severity="medium"),
            VulnFinding(plugin="baseline", severity="low"),
        ]

    def test_filter_by_severity_high(self):
        findings = self._make_findings()
        filtered = filter_by_severity(findings, "high")
        assert len(filtered) == 2  # critical + high
        assert all(f.severity_level >= 3 for f in filtered)

    def test_filter_by_severity_critical(self):
        findings = self._make_findings()
        filtered = filter_by_severity(findings, "critical")
        assert len(filtered) == 1
        assert filtered[0].severity == "critical"

    def test_assert_no_critical_passes(self):
        findings = [VulnFinding(severity="high"), VulnFinding(severity="low")]
        assert_no_critical(findings)  # should not raise

    def test_assert_no_critical_fails(self):
        findings = [VulnFinding(severity="critical", url="https://x.com")]
        with pytest.raises(AssertionError, match="严重漏洞"):
            assert_no_critical(findings)

    def test_assert_no_high_passes(self):
        findings = [VulnFinding(severity="medium"), VulnFinding(severity="low")]
        assert_no_high(findings)

    def test_assert_no_high_fails(self):
        findings = [VulnFinding(severity="high", url="https://x.com")]
        with pytest.raises(AssertionError, match="高危漏洞"):
            assert_no_high(findings)

    def test_assert_max_severity_passes(self):
        findings = [VulnFinding(severity="medium"), VulnFinding(severity="low")]
        result = assert_max_severity(findings, max_critical=0, max_high=0)
        assert result["passed"] is True

    def test_assert_max_severity_fails(self):
        findings = [VulnFinding(severity="high"), VulnFinding(severity="critical")]
        result = assert_max_severity(findings, max_critical=0, max_high=0)
        assert result["passed"] is False
        assert len(result["violations"]) == 2

    def test_assert_max_severity_with_medium_limit(self):
        findings = [
            VulnFinding(severity="medium"),
            VulnFinding(severity="medium"),
            VulnFinding(severity="medium"),
        ]
        result = assert_max_severity(findings, max_medium=2)
        assert result["passed"] is False
        assert any("中危" in v for v in result["violations"])

    def test_assert_max_severity_no_medium_limit(self):
        findings = [VulnFinding(severity="medium")]
        result = assert_max_severity(findings, max_medium=-1)
        assert result["passed"] is True
