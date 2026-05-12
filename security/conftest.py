"""
pytest fixture
"""
import os
import sys
import pytest

# 将项目根目录加入 sys.path
root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)


@pytest.fixture(scope="session")
def security_config():
    """加载安全测试配置"""
    from core.config import load_config
    config_path = os.environ.get("SECURITY_CONFIG", None)
    return load_config(config_path)


@pytest.fixture(scope="session")
def security_scanner(security_config):
    """创建 Scanner 会话级 fixture"""
    from core.scanner import Scanner
    scanner = Scanner(security_config)
    yield scanner


@pytest.fixture(scope="session")
def scan_findings(security_config):
    """加载已有扫描结果（从最新 JSON 报告）"""
    from core.report_parser import parse_json_report

    # 查找最新报告
    report_dirs = [
        security_config.output_dir,
        os.path.join(root_dir, "Xray_Rad_complete"),
    ]

    json_files = []
    for d in report_dirs:
        if os.path.exists(d):
            for f in os.listdir(d):
                if f.endswith(".json"):
                    json_files.append(os.path.join(d, f))

    if not json_files:
        pytest.skip("无扫描报告")

    # 取最新
    json_files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
    try:
        return parse_json_report(json_files[0])
    except Exception as e:
        pytest.skip(f"报告解析失败: {e}")
