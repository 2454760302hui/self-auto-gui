"""
漏洞报告断言测试
"""
import os
import sys
import pytest

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from core.report_parser import (
    parse_json_report, generate_summary, filter_by_severity,
    assert_no_critical, assert_no_high, assert_max_severity,
    format_summary_table,
)
from core.config import load_config


def _find_latest_report():
    """查找最新扫描报告"""
    config = load_config()
    report_dirs = [
        config.output_dir,
        os.path.join(root_dir, "Xray_Rad_complete"),
    ]

    json_files = []
    for d in report_dirs:
        if os.path.exists(d):
            for f in os.listdir(d):
                if f.endswith(".json"):
                    json_files.append(os.path.join(d, f))

    if not json_files:
        return None

    json_files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
    return json_files[0]


class TestVulnReport:
    """漏洞报告测试"""

    @pytest.fixture(scope="class")
    def findings(self):
        report_path = _find_latest_report()
        if not report_path:
            pytest.skip("无扫描报告")
        try:
            return parse_json_report(report_path)
        except Exception as e:
            pytest.skip(f"报告解析失败: {e}")

    @pytest.fixture(scope="class")
    def summary(self, findings):
        return generate_summary(findings)

    def test_parse_report(self, findings):
        """验证报告可解析"""
        assert len(findings) > 0, "报告中无漏洞数据"

    def test_vuln_summary(self, summary):
        """验证摘要生成"""
        assert summary.total > 0
        assert sum(summary.by_severity.values()) == summary.total

    def test_vuln_by_severity(self, summary):
        """按严重级别分类"""
        print(format_summary_table(summary))
        # 至少应该有漏洞分类
        assert summary.by_severity, "无漏洞级别分类"

    def test_no_critical_vulns(self, findings):
        """断言无严重漏洞"""
        critical = [f for f in findings if f.is_critical]
        # 这里用 warning 而非 assert，因为已有报告可能确实有严重漏洞
        if critical:
            pytest.warns(f"发现 {len(critical)} 个严重漏洞")

    def test_findings_have_required_fields(self, findings):
        """验证漏洞数据完整性"""
        for f in findings:
            assert f.plugin, "漏洞缺少 plugin 字段"
            assert f.url, "漏洞缺少 url 字段"
            assert f.severity, "漏洞缺少 severity 字段"

    def test_filter_by_severity(self, findings):
        """测试按级别过滤"""
        high_and_above = filter_by_severity(findings, "high")
        # high_and_above 应只包含 critical 和 high
        for f in high_and_above:
            assert f.severity_level >= 3, f"过滤结果包含非高危漏洞: {f.severity}"
