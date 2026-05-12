"""
Mobile 自动化框架 CLI 入口
支持 Allure 报告生成
"""
import argparse
import sys
import os

# 将项目根目录加入 sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import ConfigLoader
from core.runner import Runner
from operations.registry import OperationRegistry

# 确保操作已注册
import operations  # noqa: F401

# Allure 支持
try:
    import allure
    from allure_commons.types import AttachmentType
    HAS_ALLURE = True
except ImportError:
    HAS_ALLURE = False


DEFAULT_CONFIG = "config/test_android_login.yml"


def main():
    parser = argparse.ArgumentParser(
        description="Mobile 自动化测试框架",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py --list                      列出所有流程
  python run.py --validate                  验证配置文件
  python run.py test_login                  执行指定流程
  python run.py --all                       执行所有流程
  python run.py --platform ios test_login   指定平台执行
  python run.py --report test_login         生成 Allure 报告
        """,
    )

    parser.add_argument("flow", nargs="?", help="要执行的流程名称")
    parser.add_argument("--config", "-c", default=DEFAULT_CONFIG, help="配置文件路径")
    parser.add_argument("--list", "-l", action="store_true", help="列出所有流程")
    parser.add_argument("--validate", "-v", action="store_true", help="验证配置文件")
    parser.add_argument("--all", "-a", action="store_true", help="执行所有流程")
    parser.add_argument("--platform", "-p", help="覆盖平台 (android/ios/harmony)")
    parser.add_argument("--device", "-d", help="覆盖设备地址")
    parser.add_argument("--operations", action="store_true", help="列出所有已注册操作")
    parser.add_argument("--report", "-r", action="store_true", help="生成 Allure 报告")
    parser.add_argument("--alluredir", default="allure-results", help="Allure 结果目录")

    args = parser.parse_args()

    # 列出操作
    if args.operations:
        names = sorted(OperationRegistry.get_operation_names())
        print(f"已注册操作 ({len(names)}):")
        for name in names:
            print(f"  - {name}")
        return

    # 验证配置
    if args.validate:
        try:
            loader = ConfigLoader(config_path=args.config)
            loader.load(validate=True)
            print(loader.get_validation_report())
        except Exception as e:
            print(f"验证失败: {e}")
            sys.exit(1)
        return

    # 列出流程
    if args.list:
        try:
            loader = ConfigLoader(config_path=args.config)
            loader.load(validate=False)
            flows = loader.get_flows()
            if flows:
                print(f"可用流程 ({len(flows)}):")
                for name in flows:
                    steps = flows[name]
                    print(f"  - {name} ({len(steps)} 步)")
            else:
                print("未发现任何流程")
        except Exception as e:
            print(f"加载配置失败: {e}")
            sys.exit(1)
        return

    # 执行流程
    if args.flow or args.all:
        # 检查 Allure 报告模式
        if args.report and not HAS_ALLURE:
            print("⚠️  未安装 allure-pytest，请运行: pip install allure-pytest")
            args.report = False

        try:
            runner = Runner(config_file=args.config)

            # 连接设备
            runner.connect_device(
                platform=args.platform,
                device=args.device,
            )

            try:
                if args.all:
                    # 执行所有流程
                    flows = runner.list_flows()
                    results = {}

                    for flow_name in flows:
                        # Allure 报告包装
                        if args.report and HAS_ALLURE:
                            allure.dynamic.title(flow_name)
                            allure.dynamic.feature("Mobile 自动化测试")

                        results[flow_name] = runner.run_flow(flow_name)

                    # 输出汇总
                    print("\n" + "=" * 50)
                    print("执行汇总:")
                    for name, success in results.items():
                        status = "✓ 通过" if success else "✗ 失败"
                        print(f"  {name}: {status}")
                    print("=" * 50)

                    # Allure 汇总
                    if args.report and HAS_ALLURE:
                        allure.attach(
                            "\n".join([f"{k}: {'通过' if v else '失败'}" for k, v in results.items()]),
                            name="执行汇总",
                            attachment_type=allure.attachment_type.TEXT,
                        )

                    all_passed = all(results.values())
                    sys.exit(0 if all_passed else 1)
                else:
                    # 执行指定流程
                    if args.report and HAS_ALLURE:
                        allure.dynamic.title(args.flow)
                        allure.dynamic.feature("Mobile 自动化测试")

                    success = runner.run_flow(args.flow)
                    sys.exit(0 if success else 1)
            finally:
                runner.disconnect_device()

        except Exception as e:
            print(f"执行失败: {e}")
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()