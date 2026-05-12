"""
Security 安全测试框架 CLI 入口
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import load_config
from core.scanner import Scanner
from core.report_parser import (
    parse_json_report, generate_summary, filter_by_severity,
    assert_no_critical, assert_no_high, assert_max_severity,
    format_summary_table,
)


def cmd_scan(args):
    """执行安全扫描"""
    config = load_config(args.config)

    # 覆盖配置
    if args.targets:
        config.targets_file = args.targets
    if args.output:
        config.output_dir = args.output
    if args.proxy:
        config.proxy = args.proxy

    # 检查前置条件
    scanner = Scanner(config)
    missing = scanner.check_prerequisites()
    if missing:
        print(f"错误: 缺少必要文件: {', '.join(missing)}")
        sys.exit(1)

    # 执行扫描
    with scanner:
        targets = scanner._get_targets()
        if not targets:
            print("错误: 无扫描目标")
            sys.exit(1)

        print(f"共 {len(targets)} 个目标，开始扫描...")
        results = scanner.scan_all(targets, concurrent=not args.sequential)

        scanner.wait_for_results()

    # 输出结果
    scan_info = scanner.get_results()
    print(f"\n扫描完成!")
    print(f"  成功: {scan_info['success_count']}/{scan_info['total_targets']}")
    print(f"  失败: {scan_info['fail_count']}/{scan_info['total_targets']}")
    print(f"  JSON 报告: {scan_info['json_output']}")
    print(f"  HTML 报告: {scan_info['html_output']}")

    # 如果指定了 --summary，解析报告
    if args.summary and scan_info["json_output"] and os.path.exists(scan_info["json_output"]):
        try:
            findings = parse_json_report(scan_info["json_output"])
            summary = generate_summary(findings)
            print(format_summary_table(summary))
        except Exception as e:
            print(f"报告解析失败: {e}")


def cmd_report(args):
    """解析扫描报告"""
    if not args.report:
        # 自动查找最新报告
        report_dir = args.output or "reports"
        xray_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Xray_Rad_complete")

        json_files = []
        for d in [report_dir, xray_dir]:
            if os.path.exists(d):
                for f in os.listdir(d):
                    if f.endswith(".json"):
                        json_files.append(os.path.join(d, f))

        if not json_files:
            print("未找到扫描报告")
            sys.exit(1)

        # 按修改时间排序，取最新的
        json_files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
        report_path = json_files[0]
        print(f"使用最新报告: {report_path}")
    else:
        report_path = args.report

    if not os.path.exists(report_path):
        print(f"报告文件不存在: {report_path}")
        sys.exit(1)

    try:
        findings = parse_json_report(report_path)
        summary = generate_summary(findings)

        if args.summary:
            print(format_summary_table(summary))
        else:
            # 列出所有漏洞
            print(f"共 {len(findings)} 个漏洞:\n")
            for i, f in enumerate(findings, 1):
                print(f"  [{i}] [{f.severity.upper()}] {f.plugin}")
                print(f"      URL: {f.url}")
                if f.vuln_class:
                    print(f"      类型: {f.vuln_class}")
                print()

    except Exception as e:
        print(f"报告解析失败: {e}")
        sys.exit(1)


def cmd_assert(args):
    """断言漏洞数量"""
    config = load_config(args.config)

    # 查找报告
    report_path = args.report
    if not report_path:
        # 自动查找
        for d in [config.output_dir, os.path.join(os.path.dirname(os.path.abspath(__file__)), "Xray_Rad_complete")]:
            if os.path.exists(d):
                for f in sorted(os.listdir(d), reverse=True):
                    if f.endswith(".json"):
                        report_path = os.path.join(d, f)
                        break
            if report_path:
                break

    if not report_path or not os.path.exists(report_path):
        print("未找到扫描报告，跳过断言")
        sys.exit(0)

    findings = parse_json_report(report_path)
    summary = generate_summary(findings)

    print(format_summary_table(summary))

    # 执行断言
    result = assert_max_severity(
        findings,
        max_critical=args.max_critical if args.max_critical is not None else config.max_critical,
        max_high=args.max_high if args.max_high is not None else config.max_high,
        max_medium=args.max_medium if args.max_medium is not None else config.max_medium,
    )

    if result["passed"]:
        print("\n[PASS] 漏洞断言通过")
    else:
        print("\n[FAIL] 漏洞断言失败:")
        for v in result["violations"]:
            print(f"  - {v}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Security 安全测试框架",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py scan                           执行安全扫描
  python run.py scan --summary                 扫描并显示摘要
  python run.py scan --sequential              串行扫描
  python run.py report                         解析最新报告
  python run.py report --report path.json      解析指定报告
  python run.py assert                         断言漏洞数量
  python run.py assert --max-critical 0        断言无严重漏洞
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # scan 子命令
    scan_parser = subparsers.add_parser("scan", help="执行安全扫描")
    scan_parser.add_argument("--config", "-c", help="配置文件路径")
    scan_parser.add_argument("--targets", "-t", help="目标文件路径")
    scan_parser.add_argument("--output", "-o", help="输出目录")
    scan_parser.add_argument("--proxy", "-p", help="代理地址")
    scan_parser.add_argument("--summary", "-s", action="store_true", help="扫描后显示摘要")
    scan_parser.add_argument("--sequential", action="store_true", help="串行扫描")

    # report 子命令
    report_parser = subparsers.add_parser("report", help="解析扫描报告")
    report_parser.add_argument("--report", "-r", help="报告文件路径")
    report_parser.add_argument("--output", "-o", help="报告搜索目录")
    report_parser.add_argument("--summary", "-s", action="store_true", help="显示摘要")

    # assert 子命令
    assert_parser = subparsers.add_parser("assert", help="断言漏洞数量")
    assert_parser.add_argument("--config", "-c", help="配置文件路径")
    assert_parser.add_argument("--report", "-r", help="报告文件路径")
    assert_parser.add_argument("--max-critical", type=int, help="最大严重漏洞数")
    assert_parser.add_argument("--max-high", type=int, help="最大高危漏洞数")
    assert_parser.add_argument("--max-medium", type=int, help="最大中危漏洞数")

    args = parser.parse_args()

    if args.command == "scan":
        cmd_scan(args)
    elif args.command == "report":
        cmd_report(args)
    elif args.command == "assert":
        cmd_assert(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()