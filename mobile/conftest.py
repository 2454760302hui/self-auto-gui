"""
pytest fixture
"""
import os
import pytest

sys_path_appended = False


def pytest_configure(config):
    """将项目根目录加入 sys.path"""
    global sys_path_appended
    if not sys_path_appended:
        import sys
        root_dir = os.path.dirname(os.path.abspath(__file__))
        if root_dir not in sys.path:
            sys.path.insert(0, root_dir)
        sys_path_appended = True


@pytest.fixture(scope="session")
def mobile_runner():
    """创建 Mobile Runner 会话级 fixture"""
    from core.runner import Runner

    config_path = os.environ.get("MOBILE_CONFIG", "config/test_android_login.yml")
    platform = os.environ.get("MOBILE_PLATFORM", None)
    device = os.environ.get("MOBILE_DEVICE", None)

    runner = Runner(config_file=config_path)
    try:
        runner.connect_device(platform=platform, device=device)
    except Exception as e:
        pytest.skip(f"Device not available: {e}")

    yield runner

    runner.disconnect_device()
