"""
扫描报告解析器
解析 Xray JSON/HTML 报告，结构化漏洞数据
"""
import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from loguru import logger

from .errors import ReportError


# 漏洞严重级别
SEVERITY_LEVELS = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
    "info": 0,
}


@dataclass
class VulnFinding:
    """漏洞发现"""
    plugin: str = ""
    url: str = ""
    vuln_class: str = ""
    severity: str = "medium"
    detail: Dict[str, Any] = field(default_factory=dict)
    create_time: int = 0
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def severity_level(self) -> int:
        return SEVERITY_LEVELS.get(self.severity.lower(), 0)

    @property
    def is_critical(self) -> bool:
        return self.severity.lower() == "critical"

    @property
    def is_high(self) -> bool:
        return self.severity.lower() == "high"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugin": self.plugin,
            "url": self.url,
            "vuln_class": self.vuln_class,
            "severity": self.severity,
            "detail": self.detail,
            "create_time": self.create_time,
        }


@dataclass
class ReportSummary:
    """报告摘要"""
    total: int = 0
    by_severity: Dict[str, int] = field(default_factory=dict)
    by_plugin: Dict[str, int] = field(default_factory=dict)
    by_url: Dict[str, int] = field(default_factory=dict)
    findings: List[VulnFinding] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "by_severity": self.by_severity,
            "by_plugin": self.by_plugin,
            "by_url": self.by_url,
        }


def parse_json_report(path: str) -> List[VulnFinding]:
    """解析 Xray JSON 报告"""
    if not os.path.exists(path):
        raise ReportError.file_not_found(path)

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    if not content.strip():
        raise ReportError.no_findings(path)

    # Xray JSON 可能是数组或逐行 JSON，也可能有编码问题
    # 优先使用对象提取法（最健壮）
    findings = _extract_json_objects(content)

    if not findings:
        # 回退到标准解析
        try:
            data = json.loads(content)
            if isinstance(data, list):
                for item in data:
                    finding = _parse_finding(item)
                    if finding:
                        findings.append(finding)
            elif isinstance(data, dict):
                finding = _parse_finding(data)
                if finding:
                    findings.append(finding)
        except json.JSONDecodeError:
            pass

    if not findings:
        # 回退到逐行解析
        for line in content.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                finding = _parse_finding(item)
                if finding:
                    findings.append(finding)
            except json.JSONDecodeError:
                continue

    if not findings:
        raise ReportError.no_findings(path)

    logger.info(f"解析报告: {path}, 发现 {len(findings)} 个漏洞")
    return findings


def _extract_json_objects(content: str) -> List[VulnFinding]:
    """从可能有编码问题的 JSON 文本中提取独立 JSON 对象"""
    content = content.lstrip('\ufeff').strip()
    findings = []
    depth = 0
    current_start = None

    for i, ch in enumerate(content):
        if ch == '{' and depth == 0:
            current_start = i
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and current_start is not None:
                obj_str = content[current_start:i + 1]
                try:
                    item = json.loads(obj_str)
                    finding = _parse_finding(item)
                    if finding:
                        findings.append(finding)
                except (json.JSONDecodeError, ValueError):
                    pass
                current_start = None

    return findings


def _parse_finding(item: Dict[str, Any]) -> Optional[VulnFinding]:
    """解析单个漏洞条目"""
    if not isinstance(item, dict):
        return None

    plugin = item.get("plugin", "")
    if not plugin:
        return None

    detail = item.get("detail", {})
    url = detail.get("addr", item.get("url", ""))
    vuln_class = item.get("vuln_class", "")
    severity = _infer_severity(plugin, vuln_class, item)
    create_time = item.get("create_time", 0)

    return VulnFinding(
        plugin=plugin,
        url=url,
        vuln_class=vuln_class,
        severity=severity,
        detail=detail,
        create_time=create_time,
        raw=item,
    )


def _infer_severity(plugin: str, vuln_class: str, item: Dict[str, Any]) -> str:
    """从插件名或 detail.severity 字段推断漏洞严重级别"""
    # 优先从 detail.severity 字段读取（Xray JSON 原生字段）
    detail = item.get("detail", {})
    if isinstance(detail, dict):
        raw_severity = detail.get("severity", "")
        if raw_severity:
            sev_map = {
                "critical": "critical", "crit": "critical", "4": "critical",
                "high": "high", "h": "high", "3": "high",
                "medium": "medium", "med": "medium", "2": "medium",
                "low": "low", "l": "low", "info": "low", "1": "low",
            }
            normalized = str(raw_severity).lower().strip()
            if normalized in sev_map:
                return sev_map[normalized]

    # fallback: 从插件名推断
    plugin_lower = plugin.lower()

    # 明确的高危插件
    critical_keywords = ["rce", "cmd-injection", "ssrf", "upload", "deserialization"]
    high_keywords = ["sqli", "sqldet", "xss", "xxe", "path-traversal", "ssti"]
    medium_keywords = ["brute-force", "csrf", "open-redirect"]
    low_keywords = ["baseline", "dirscan", "info", "header", "cors", "csp"]

    for kw in critical_keywords:
        if kw in plugin_lower:
            return "critical"

    for kw in high_keywords:
        if kw in plugin_lower:
            return "high"

    for kw in medium_keywords:
        if kw in plugin_lower:
            return "medium"

    for kw in low_keywords:
        if kw in plugin_lower:
            return "low"

    # 默认 medium
    return "medium"


def generate_summary(findings: List[VulnFinding]) -> ReportSummary:
    """生成漏洞摘要"""
    summary = ReportSummary(findings=findings)
    summary.total = len(findings)

    # 按严重级别统计
    for finding in findings:
        sev = finding.severity
        summary.by_severity[sev] = summary.by_severity.get(sev, 0) + 1

    # 按插件统计
    for finding in findings:
        summary.by_plugin[finding.plugin] = summary.by_plugin.get(finding.plugin, 0) + 1

    # 按 URL 统计
    for finding in findings:
        # 简化 URL（去掉路径参数）
        url_base = finding.url.split("?")[0]
        summary.by_url[url_base] = summary.by_url.get(url_base, 0) + 1

    return summary


def filter_by_severity(
    findings: List[VulnFinding], min_level: str = "medium"
) -> List[VulnFinding]:
    """按严重级别过滤漏洞"""
    min_val = SEVERITY_LEVELS.get(min_level.lower(), 0)
    return [f for f in findings if f.severity_level >= min_val]


def assert_no_critical(findings: List[VulnFinding]) -> None:
    """断言无严重漏洞"""
    critical = [f for f in findings if f.is_critical]
    if critical:
        urls = [f.url for f in critical[:5]]
        raise AssertionError(
            f"发现 {len(critical)} 个严重漏洞: {', '.join(urls)}"
        )


def assert_no_high(findings: List[VulnFinding]) -> None:
    """断言无高危漏洞"""
    high = [f for f in findings if f.is_high]
    if high:
        urls = [f.url for f in high[:5]]
        raise AssertionError(
            f"发现 {len(high)} 个高危漏洞: {', '.join(urls)}"
        )


def assert_max_severity(
    findings: List[VulnFinding],
    max_critical: int = 0,
    max_high: int = 0,
    max_medium: int = -1,
) -> Dict[str, Any]:
    """断言漏洞数量不超过阈值，返回检查结果"""
    by_sev = {}
    for f in findings:
        by_sev[f.severity] = by_sev.get(f.severity, 0) + 1

    result = {"passed": True, "violations": []}

    critical_count = by_sev.get("critical", 0)
    if critical_count > max_critical:
        result["passed"] = False
        result["violations"].append(
            f"严重漏洞 {critical_count} 个，超过阈值 {max_critical}"
        )

    high_count = by_sev.get("high", 0)
    if high_count > max_high:
        result["passed"] = False
        result["violations"].append(
            f"高危漏洞 {high_count} 个，超过阈值 {max_high}"
        )

    if max_medium >= 0:
        medium_count = by_sev.get("medium", 0)
        if medium_count > max_medium:
            result["passed"] = False
            result["violations"].append(
                f"中危漏洞 {medium_count} 个，超过阈值 {max_medium}"
            )

    return result


def format_summary_table(summary: ReportSummary) -> str:
    """格式化摘要表格"""
    lines = []
    lines.append("=" * 60)
    lines.append(f"漏洞扫描报告摘要 (共 {summary.total} 个)")
    lines.append("=" * 60)

    # 按严重级别
    lines.append("\n按严重级别:")
    for sev in ["critical", "high", "medium", "low", "info"]:
        count = summary.by_severity.get(sev, 0)
        if count > 0:
            lines.append(f"  {sev:10s}: {count}")

    # 按插件 Top 10
    lines.append("\n按漏洞类型 (Top 10):")
    sorted_plugins = sorted(summary.by_plugin.items(), key=lambda x: -x[1])[:10]
    for plugin, count in sorted_plugins:
        lines.append(f"  {plugin:50s}: {count}")

    # 按 URL Top 5
    lines.append("\n按目标 URL (Top 5):")
    sorted_urls = sorted(summary.by_url.items(), key=lambda x: -x[1])[:5]
    for url, count in sorted_urls:
        lines.append(f"  {url[:55]:55s}: {count}")

    lines.append("=" * 60)
    return "\n".join(lines)
