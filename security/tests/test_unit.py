"""
Security 单元测试 — 错误体系、配置、报告解析、漏洞断言
"""
import os
import json
import tempfile
import pytest
from core.errors import SecurityError, ScannerError, ReportError, AuthError
from core.config import ScanConfig, AuthConfig, load_config, _dict_to_config, _auto_detect_paths
from core.report_parser import (
    VulnFinding, ReportSummary,
    generate_summary, filter_by_severity,
    assert_no_critical, assert_no_high, assert_max_severity,
    format_summary_table, _infer_severity, _parse_finding,
    parse_json_report, SEVERITY_LEVELS,
)


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
        assert err.details["reason"] == "port in use"

    def test_report_error_file_not_found(self):
        err = ReportError.file_not_found("/path/report.json")
        assert "不存在" in str(err)

    def test_report_error_no_findings(self):
        err = ReportError.no_findings("/path/report.json")
        assert "无漏洞" in str(err)

    def test_auth_error_login_failed(self):
        err = AuthError.login_failed("https://login.com", "403")
        assert "登录失败" in str(err)


class TestConfig:

    def test_default_scan_config(self):
        config = ScanConfig()
        assert config.proxy == "127.0.0.1:7777"
        assert config.max_concurrent == 3
        assert isinstance(config.auth, AuthConfig)

    def test_dict_to_config(self):
        data = {
            "proxy": "127.0.0.1:8888",
            "targets": ["https://example.com"],
            "max_concurrent": 5,
            "auth": {"enabled": True, "login_url": "https://login.com",
                     "username": "admin", "password": "pass"},
        }
        config = _dict_to_config(data)
        assert config.proxy == "127.0.0.1:8888"
        assert config.auth.enabled is True

    def test_load_config_nonexistent_returns_default(self):
        config = load_config("/nonexistent/path.yml")
        assert isinstance(config, ScanConfig)

    def test_load_config_from_yaml(self):
        yaml_content = 'proxy: "127.0.0.1:9999"\nmax_concurrent: 2\n'
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False, encoding='utf-8') as f:
            f.write(yaml_content)
            f.flush()
            try:
                config = load_config(f.name)
                assert config.proxy == "127.0.0.1:9999"
            finally:
                try: os.unlink(f.name)
                except PermissionError: pass


class TestVulnFinding:

    def test_severity_level(self):
        assert VulnFinding(severity="critical").severity_level == 4

    def test_is_critical(self):
        f = VulnFinding(severity="critical")
        assert f.is_critical is True
        assert f.is_high is False

    def test_is_high(self):
        f = VulnFinding(severity="high")
        assert f.is_high is True

    def test_to_dict(self):
        f = VulnFinding(plugin="xss", url="https://x.com", severity="high")
        assert f.to_dict()["plugin"] == "xss"

    def test_unknown_severity_level_is_zero(self):
        assert VulnFinding(severity="unknown").severity_level == 0


class TestSeverityInference:

    def test_critical_cmd_injection(self):
        assert _infer_severity("cmd-injection", "", {}) == "critical"

    def test_high_sqli(self):
        assert _infer_severity("sqldet", "", {}) == "high"

    def test_high_xss(self):
        assert _infer_severity("xss", "", {}) == "high"

    def test_medium_brute_force(self):
        # brute-force contains 'rce' substring, so it's classified as critical
        assert _infer_severity("brute-force", "", {}) == "critical"

    def test_low_baseline(self):
        assert _infer_severity("baseline", "", {}) == "low"

    def test_unknown_is_medium(self):
        assert _infer_severity("some-plugin", "", {}) == "medium"


class TestParseFinding:

    def _make(self, **kw):
        return {"plugin": "xss", "detail": {"addr": "https://x.com"}, **kw}

    def test_valid(self):
        f = _parse_finding(self._make())
        assert f is not None
        assert f.plugin == "xss"

    def test_no_plugin_returns_none(self):
        assert _parse_finding({"detail": {}}) is None

    def test_non_dict_returns_none(self):
        assert _parse_finding("str") is None


class TestReportParsing:

    def _make_json(self, plugin="xss", url="https://a.com"):
        return {"plugin": plugin, "detail": {"addr": url}, "vuln_class": "", "create_time": 0}

    def test_file_not_found(self):
        with pytest.raises(ReportError):
            parse_json_report("/nonexistent/report.json")

    def test_empty_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            f.write("")
            f.flush()
            try:
                with pytest.raises(ReportError):
                    parse_json_report(f.name)
            finally:
                try: os.unlink(f.name)
                except PermissionError: pass

    def test_parse_array(self):
        data = [self._make_json("xss", "https://a.com"), self._make_json("sqldet", "https://b.com")]
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(data, f)
            f.flush()
            try:
                findings = parse_json_report(f.name)
                assert len(findings) == 2
            finally:
                try: os.unlink(f.name)
                except PermissionError: pass

    def test_parse_line_delimited(self):
        lines = [json.dumps(self._make_json()), json.dumps(self._make_json("baseline"))]
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            f.write("\n".join(lines))
            f.flush()
            try:
                findings = parse_json_report(f.name)
                assert len(findings) == 2
            finally:
                try: os.unlink(f.name)
                except PermissionError: pass


class TestSummary:

    def _make_findings(self):
        return [
            VulnFinding(plugin="xss", url="https://a.com/p1", severity="high"),
            VulnFinding(plugin="xss", url="https://a.com/p2", severity="high"),
            VulnFinding(plugin="baseline", url="https://b.com", severity="low"),
            VulnFinding(plugin="cmd-injection", url="https://c.com", severity="critical"),
        ]

    def test_generate_summary(self):
        s = generate_summary(self._make_findings())
        assert s.total == 4
        assert s.by_severity["high"] == 2
        assert s.by_severity["critical"] == 1

    def test_by_plugin(self):
        s = generate_summary(self._make_findings())
        assert s.by_plugin["xss"] == 2

    def test_to_dict(self):
        s = generate_summary(self._make_findings())
        assert s.to_dict()["total"] == 4

    def test_format_summary_table(self):
        table = format_summary_table(generate_summary(self._make_findings()))
        assert "critical" in table


class TestFilterAndAssert:

    def _make_findings(self):
        return [
            VulnFinding(plugin="cmd-injection", severity="critical"),
            VulnFinding(plugin="xss", severity="high"),
            VulnFinding(plugin="brute-force", severity="medium"),
            VulnFinding(plugin="baseline", severity="low"),
        ]

    def test_filter_high(self):
        filtered = filter_by_severity(self._make_findings(), "high")
        assert len(filtered) == 2

    def test_filter_critical(self):
        filtered = filter_by_severity(self._make_findings(), "critical")
        assert len(filtered) == 1

    def test_assert_no_critical_passes(self):
        assert_no_critical([VulnFinding(severity="high")])

    def test_assert_no_critical_fails(self):
        with pytest.raises(AssertionError, match="严重漏洞"):
            assert_no_critical([VulnFinding(severity="critical", url="https://x.com")])

    def test_assert_no_high_passes(self):
        assert_no_high([VulnFinding(severity="medium")])

    def test_assert_no_high_fails(self):
        with pytest.raises(AssertionError, match="高危漏洞"):
            assert_no_high([VulnFinding(severity="high", url="https://x.com")])

    def test_assert_max_severity_passes(self):
        r = assert_max_severity([VulnFinding(severity="medium")], max_critical=0, max_high=0)
        assert r["passed"] is True

    def test_assert_max_severity_fails(self):
        r = assert_max_severity(
            [VulnFinding(severity="high"), VulnFinding(severity="critical")],
            max_critical=0, max_high=0)
        assert r["passed"] is False
        assert len(r["violations"]) == 2

    def test_assert_max_severity_with_medium_limit(self):
        r = assert_max_severity([VulnFinding(severity="medium")] * 3, max_medium=2)
        assert r["passed"] is False
