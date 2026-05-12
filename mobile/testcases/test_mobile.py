"""
pytest 参数化桥接
将 YAML 流程转换为 pytest 测试用例
"""
import os
import sys

import pytest

# 确保项目根目录在 sys.path 中
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from core.config import ConfigLoader


def get_flow_names():
    """从配置文件获取所有流程名称"""
    config_path = os.environ.get("MOBILE_CONFIG", "config/test_android_login.yml")

    if not os.path.exists(config_path):
        return []

    try:
        loader = ConfigLoader(config_path=config_path)
        loader.load(validate=False)
        return list(loader.get_flows().keys())
    except Exception:
        return []


class TestMobile:
    """Mobile 自动化测试"""

    @pytest.fixture(scope="class")
    def runner(self, request):
        """创建 Runner 实例"""
        from core.runner import Runner

        config_path = os.environ.get("MOBILE_CONFIG", "config/test_android_login.yml")
        platform = os.environ.get("MOBILE_PLATFORM", None)
        device = os.environ.get("MOBILE_DEVICE", None)

        runner = Runner(config_file=config_path)
        runner.connect_device(platform=platform, device=device)

        yield runner

        runner.disconnect_device()

    @pytest.mark.parametrize("flow_name", get_flow_names())
    def test_flow(self, runner, flow_name):
        """执行 YAML 流程测试"""
        result = runner.run_flow(flow_name)
        assert result, f"流程 '{flow_name}' 执行失败"
