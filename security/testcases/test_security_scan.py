"""
安全扫描测试
"""
import os
import sys
import pytest

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from core.scanner import Scanner
from core.config import load_config


class TestSecurityScan:
    """安全扫描测试"""

    @pytest.fixture(scope="class")
    def config(self):
        return load_config()

    def test_prerequisites(self, config):
        """验证扫描器前置条件"""
        scanner = Scanner(config)
        missing = scanner.check_prerequisites()
        assert not missing, f"缺少必要文件: {', '.join(missing)}"

    def test_xray_binary_exists(self, config):
        """验证 Xray 二进制存在"""
        assert config.xray_path, "未配置 xray_path"
        assert os.path.exists(config.xray_path), f"Xray 二进制不存在: {config.xray_path}"

    def test_rad_binary_exists(self, config):
        """验证 Rad 二进制存在"""
        assert config.rad_path, "未配置 rad_path"
        assert os.path.exists(config.rad_path), f"Rad 二进制不存在: {config.rad_path}"

    def test_targets_exist(self, config):
        """验证扫描目标存在"""
        targets = []
        if config.targets:
            targets.extend(config.targets)
        if config.targets_file and os.path.exists(config.targets_file):
            with open(config.targets_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        targets.append(line)
        assert targets, "无扫描目标"

    @pytest.mark.skipif(
        os.environ.get("RUN_SCAN") != "1",
        reason="需要设置 RUN_SCAN=1 才执行实际扫描"
    )
    def test_scan_all_targets(self, config):
        """执行完整扫描（需要 RUN_SCAN=1）"""
        scanner = Scanner(config)
        with scanner:
            targets = scanner._get_targets()
            results = scanner.scan_all(targets)
            scanner.wait_for_results()

        success_count = sum(1 for r in results if r["success"])
        assert success_count > 0, "所有目标扫描失败"
