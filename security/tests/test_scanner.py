"""
Scanner 单元测试
使用 mocked subprocess 测试 Scanner 类的各个方法
"""
import os
import subprocess
import time
from unittest.mock import MagicMock, patch, PropertyMock, call

import pytest

from core.scanner import Scanner
from core.config import ScanConfig
from core.errors import ScannerError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_config(**overrides):
    """创建一个带有合理默认值的 ScanConfig（不依赖真实文件）"""
    defaults = dict(
        xray_path="C:/fake/xray.exe",
        rad_path="C:/fake/rad.exe",
        proxy="127.0.0.1:7777",
        output_dir="reports",
        targets=["http://example.com"],
        targets_file="",
        xray_startup_wait=0,
        scan_interval=0,
        result_wait=0,
        max_concurrent=3,
    )
    defaults.update(overrides)
    return ScanConfig(**defaults)


@pytest.fixture
def scanner():
    return Scanner(_make_config())


@pytest.fixture
def scanner_no_targets():
    return Scanner(_make_config(targets=[], targets_file=""))


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------

class TestScannerInit:

    def test_default_config(self):
        """Scanner() 不传参时使用默认 ScanConfig"""
        s = Scanner()
        assert isinstance(s._config, ScanConfig)

    def test_custom_config(self):
        cfg = _make_config(proxy="1.2.3.4:9999")
        s = Scanner(cfg)
        assert s.config.proxy == "1.2.3.4:9999"

    def test_initial_state(self):
        s = Scanner()
        assert s._xray_process is None
        assert s._output_timestamp == ""
        assert s._scan_results == []


# ---------------------------------------------------------------------------
# check_prerequisites
# ---------------------------------------------------------------------------

class TestCheckPrerequisites:

    @patch("core.scanner.os.path.exists", return_value=True)
    def test_all_present(self, mock_exists, scanner):
        missing = scanner.check_prerequisites()
        assert missing == []

    @patch("core.scanner.os.path.exists", return_value=False)
    def test_missing_xray(self, mock_exists, scanner):
        missing = scanner.check_prerequisites()
        assert any("xray" in m for m in missing)

    @patch("core.scanner.os.path.exists", return_value=False)
    def test_missing_rad(self, mock_exists, scanner):
        missing = scanner.check_prerequisites()
        assert any("rad" in m for m in missing)

    def test_missing_targets(self, scanner_no_targets):
        """当 targets 和 targets_file 都为空时报缺少目标"""
        scanner_no_targets._config.xray_path = "x"
        scanner_no_targets._config.rad_path = "r"
        with patch("core.scanner.os.path.exists", return_value=True):
            missing = scanner_no_targets.check_prerequisites()
        assert any("targets" in m.lower() or "无目标" in m for m in missing)

    @patch("core.scanner.os.path.exists")
    def test_missing_targets_file(self, mock_exists, scanner_no_targets):
        """targets_file 指向不存在的文件"""
        scanner_no_targets._config.xray_path = "x"
        scanner_no_targets._config.rad_path = "r"
        scanner_no_targets._config.targets_file = "missing.txt"
        # xray/rad paths exist, targets_file does not
        mock_exists.side_effect = lambda p: p not in ("missing.txt",)
        missing = scanner_no_targets.check_prerequisites()
        assert any("targets_file" in m for m in missing)


# ---------------------------------------------------------------------------
# start_xray
# ---------------------------------------------------------------------------

class TestStartXray:

    @patch("core.scanner.time.sleep")
    @patch("core.scanner.os.makedirs")
    @patch("core.scanner.os.path.exists", return_value=True)
    @patch("core.scanner.subprocess.Popen")
    def test_success(self, mock_popen, mock_exists, mock_makedirs, mock_sleep, scanner):
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_popen.return_value = mock_proc

        ts = scanner.start_xray()
        assert ts != ""
        assert scanner._xray_process is mock_proc
        mock_popen.assert_called_once()
        # output files should be set
        assert scanner._json_output.endswith(".json")
        assert scanner._html_output.endswith(".html")

    @patch("core.scanner.os.path.exists", return_value=False)
    def test_missing_prerequisites_raises(self, mock_exists, scanner):
        with pytest.raises(ScannerError):
            scanner.start_xray()

    @patch("core.scanner.os.makedirs")
    @patch("core.scanner.os.path.exists", return_value=True)
    @patch("core.scanner.subprocess.Popen", side_effect=OSError("boom"))
    def test_popen_exception_raises(self, mock_popen, mock_exists, mock_makedirs, scanner):
        with pytest.raises(ScannerError):
            scanner.start_xray()

    @patch("core.scanner.time.sleep")
    @patch("core.scanner.os.makedirs")
    @patch("core.scanner.os.path.exists", return_value=True)
    @patch("core.scanner.subprocess.Popen")
    def test_xray_config_appended(self, mock_popen, mock_exists, mock_makedirs, mock_sleep):
        cfg = _make_config(xray_config="custom_config.yaml")
        s = Scanner(cfg)
        mock_proc = MagicMock()
        mock_proc.pid = 999
        mock_popen.return_value = mock_proc

        s.start_xray()
        cmd = mock_popen.call_args[0][0]
        assert "--config" in cmd
        assert "custom_config.yaml" in cmd


# ---------------------------------------------------------------------------
# stop_xray
# ---------------------------------------------------------------------------

class TestStopXray:

    def test_already_stopped(self, scanner):
        """进程为 None 时 stop_xray 不报错"""
        scanner._xray_process = None
        scanner.stop_xray()  # should not raise

    def test_running_process_stops(self, scanner):
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None  # still running
        scanner._xray_process = mock_proc

        with patch("core.scanner.os.name", "posix"):
            scanner.stop_xray()

        mock_proc.terminate.assert_called_once()
        assert scanner._xray_process is None

    @patch("core.scanner.subprocess.run")
    def test_windows_taskkill(self, mock_run, scanner):
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.pid = 5555
        scanner._xray_process = mock_proc

        with patch("core.scanner.os.name", "nt"):
            scanner.stop_xray()

        mock_run.assert_called_once()
        taskkill_cmd = mock_run.call_args[0][0]
        assert "taskkill" in taskkill_cmd[0] or "taskkill" in str(taskkill_cmd)
        assert scanner._xray_process is None

    def test_stopped_process_does_nothing(self, scanner):
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 0  # already exited
        scanner._xray_process = mock_proc

        scanner.stop_xray()
        # Should NOT call terminate since process already exited
        mock_proc.terminate.assert_not_called()


# ---------------------------------------------------------------------------
# scan_target
# ---------------------------------------------------------------------------

class TestScanTarget:

    @patch("core.scanner.time.time", side_effect=[100, 205])
    @patch("core.scanner.subprocess.Popen")
    def test_success(self, mock_popen, mock_time, scanner):
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = (b"ok output", b"")
        mock_proc.returncode = 0
        mock_proc.poll.return_value = 0
        mock_popen.return_value = mock_proc

        result = scanner.scan_target("http://example.com")

        assert result["success"] is True
        assert result["returncode"] == 0
        assert result["target"] == "http://example.com"
        assert result["stdout"] == "ok output"

    @patch("core.scanner.time.time", side_effect=[100, 205])
    @patch("core.scanner.subprocess.Popen")
    def test_nonzero_returncode(self, mock_popen, mock_time, scanner):
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = (b"", b"some error")
        mock_proc.returncode = 1
        mock_proc.poll.return_value = 1
        mock_popen.return_value = mock_proc

        result = scanner.scan_target("http://fail.com")
        assert result["success"] is False
        assert result["returncode"] == 1

    @patch("core.scanner.time.time", side_effect=[100, 205])
    @patch("core.scanner.subprocess.Popen")
    def test_timeout_handling(self, mock_popen, mock_time, scanner):
        mock_proc = MagicMock()
        mock_proc.communicate.side_effect = subprocess.TimeoutExpired("cmd", 300)
        # Second call after kill should succeed
        mock_proc.communicate.side_effect = [
            subprocess.TimeoutExpired("cmd", 300),
            (b"", b"timeout"),
        ]
        mock_proc.returncode = -9
        mock_proc.poll.return_value = -9
        mock_popen.return_value = mock_proc

        result = scanner.scan_target("http://slow.com")
        mock_proc.kill.assert_called()
        assert result["target"] == "http://slow.com"

    @patch("core.scanner.time.time", side_effect=[100, 105])
    @patch("core.scanner.subprocess.Popen")
    def test_process_exception_reraises(self, mock_popen, mock_time, scanner):
        mock_proc = MagicMock()
        mock_proc.communicate.side_effect = RuntimeError("unexpected")
        mock_proc.poll.return_value = None
        mock_popen.return_value = mock_proc

        with pytest.raises(RuntimeError, match="unexpected"):
            scanner.scan_target("http://bad.com")
        mock_proc.kill.assert_called()

    @patch("core.scanner.time.time", side_effect=[100, 205])
    @patch("core.scanner.subprocess.Popen")
    def test_extra_args_passed(self, mock_popen, mock_time, scanner):
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = (b"", b"")
        mock_proc.returncode = 0
        mock_proc.poll.return_value = 0
        mock_popen.return_value = mock_proc

        scanner.scan_target("http://example.com", extra_args=["--custom", "val"])
        cmd = mock_popen.call_args[0][0]
        assert "--custom" in cmd
        assert "val" in cmd

    @patch("core.scanner.time.time", side_effect=[100, 205])
    @patch("core.scanner.subprocess.Popen")
    def test_result_appended_to_scan_results(self, mock_popen, mock_time, scanner):
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = (b"", b"")
        mock_proc.returncode = 0
        mock_proc.poll.return_value = 0
        mock_popen.return_value = mock_proc

        scanner.scan_target("http://a.com")
        assert len(scanner._scan_results) == 1

    @patch("core.scanner.time.time", side_effect=[100, 205])
    @patch("core.scanner.subprocess.Popen")
    def test_rad_config_appended(self, mock_popen, mock_time):
        cfg = _make_config(rad_config="rad_cfg.yml")
        s = Scanner(cfg)
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = (b"", b"")
        mock_proc.returncode = 0
        mock_proc.poll.return_value = 0
        mock_popen.return_value = mock_proc

        s.scan_target("http://example.com")
        cmd = mock_popen.call_args[0][0]
        assert "--config" in cmd
        assert "rad_cfg.yml" in cmd


# ---------------------------------------------------------------------------
# scan_all
# ---------------------------------------------------------------------------

class TestScanAll:

    def test_empty_targets_warning(self, scanner_no_targets):
        """无目标时返回空列表"""
        result = scanner_no_targets.scan_all()
        assert result == []

    @patch.object(Scanner, "_scan_sequential")
    @patch.object(Scanner, "_get_targets", return_value=["http://a.com"])
    def test_single_target_sequential(self, mock_targets, mock_seq, scanner):
        mock_seq.return_value = [{"target": "http://a.com", "success": True}]
        results = scanner.scan_all(concurrent=False)
        mock_seq.assert_called_once_with(["http://a.com"])

    @patch.object(Scanner, "_scan_concurrent")
    @patch.object(Scanner, "_get_targets", return_value=["http://a.com", "http://b.com"])
    def test_multiple_targets_concurrent(self, mock_targets, mock_conc, scanner):
        mock_conc.return_value = [
            {"target": "http://a.com", "success": True},
            {"target": "http://b.com", "success": True},
        ]
        results = scanner.scan_all(concurrent=True)
        mock_conc.assert_called_once()

    @patch.object(Scanner, "_scan_sequential")
    @patch.object(Scanner, "_get_targets", return_value=["http://a.com", "http://b.com"])
    def test_concurrent_false_forces_sequential(self, mock_targets, mock_seq, scanner):
        mock_seq.return_value = []
        scanner.scan_all(concurrent=False)
        mock_seq.assert_called_once()

    @patch.object(Scanner, "scan_target")
    def test_explicit_targets_override(self, mock_scan, scanner):
        mock_scan.return_value = {"target": "http://x.com", "success": True}
        scanner.scan_all(targets=["http://x.com"], concurrent=False)
        mock_scan.assert_called_once_with("http://x.com")


# ---------------------------------------------------------------------------
# scan_with_auth
# ---------------------------------------------------------------------------

class TestScanWithAuth:

    @patch.object(Scanner, "scan_target")
    def test_cookie_string_formatting(self, mock_scan, scanner):
        mock_scan.return_value = {"target": "http://a.com", "success": True}
        cookies = {"session": "abc123", "token": "xyz789"}

        scanner.scan_with_auth("http://a.com", cookies)

        call_args = mock_scan.call_args
        extra_args = call_args[1].get("extra_args") or call_args[0][1] if len(call_args[0]) > 1 else call_args[1]["extra_args"]
        cookie_header = extra_args[1]
        assert "session=abc123" in cookie_header
        assert "token=xyz789" in cookie_header

    @patch.object(Scanner, "scan_target")
    def test_single_cookie(self, mock_scan, scanner):
        mock_scan.return_value = {"target": "http://a.com", "success": True}
        scanner.scan_with_auth("http://a.com", {"sid": "val"})
        extra_args = mock_scan.call_args[1]["extra_args"]
        assert extra_args[1] == "Cookie: sid=val"


# ---------------------------------------------------------------------------
# wait_for_results
# ---------------------------------------------------------------------------

class TestWaitForResults:

    @patch("core.scanner.time.sleep")
    def test_sleep_called(self, mock_sleep, scanner):
        scanner.wait_for_results()
        mock_sleep.assert_called_once_with(scanner._config.result_wait)


# ---------------------------------------------------------------------------
# get_results
# ---------------------------------------------------------------------------

class TestGetResults:

    def test_returns_correct_structure(self, scanner):
        scanner._output_timestamp = "20260421120000"
        scanner._json_output = "report.json"
        scanner._html_output = "report.html"
        scanner._scan_results = [
            {"target": "http://a.com", "success": True, "returncode": 0, "duration": 10.0, "stdout": "", "stderr": ""},
            {"target": "http://b.com", "success": False, "returncode": 1, "duration": 5.0, "stdout": "", "stderr": "err"},
        ]

        result = scanner.get_results()

        assert result["timestamp"] == "20260421120000"
        assert result["json_output"] == "report.json"
        assert result["html_output"] == "report.html"
        assert result["total_targets"] == 2
        assert result["success_count"] == 1
        assert result["fail_count"] == 1

    def test_empty_results(self, scanner):
        result = scanner.get_results()
        assert result["total_targets"] == 0
        assert result["success_count"] == 0
        assert result["fail_count"] == 0


# ---------------------------------------------------------------------------
# _get_targets
# ---------------------------------------------------------------------------

class TestGetTargets:

    def test_from_config(self, scanner):
        targets = scanner._get_targets()
        assert "http://example.com" in targets

    @patch("builtins.open", create=True)
    @patch("core.scanner.os.path.exists", return_value=True)
    def test_from_file(self, mock_exists, mock_open, scanner_no_targets):
        scanner_no_targets._config.targets_file = "targets.txt"
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        mock_open.return_value.__iter__ = lambda s: iter([
            "http://a.com\n",
            "http://b.com\n",
            "# commented\n",
            "\n",
            "http://a.com\n",
        ])

        targets = scanner_no_targets._get_targets()
        assert "http://a.com" in targets
        assert "http://b.com" in targets
        assert len(targets) == 2  # deduplicated

    def test_comments_skipped(self, scanner_no_targets):
        """以 # 开头的行应被跳过"""
        scanner_no_targets._config.targets = []
        with patch("core.scanner.os.path.exists", return_value=False):
            targets = scanner_no_targets._get_targets()
        assert targets == []

    def test_dedup_preserves_order(self, scanner_no_targets):
        scanner_no_targets._config.targets = ["http://a.com", "http://b.com", "http://a.com"]
        with patch("core.scanner.os.path.exists", return_value=False):
            targets = scanner_no_targets._get_targets()
        assert targets == ["http://a.com", "http://b.com"]


# ---------------------------------------------------------------------------
# context manager
# ---------------------------------------------------------------------------

class TestContextManager:

    @patch.object(Scanner, "stop_xray")
    @patch.object(Scanner, "start_xray", return_value="ts")
    @patch("core.scanner.os.path.exists", return_value=True)
    def test_enter_starts_xray(self, mock_exists, mock_start, mock_stop):
        cfg = _make_config()
        with Scanner(cfg) as s:
            mock_start.assert_called_once()
            assert s is not None

    @patch.object(Scanner, "stop_xray")
    @patch.object(Scanner, "start_xray", return_value="ts")
    @patch("core.scanner.os.path.exists", return_value=True)
    def test_exit_stops_xray(self, mock_exists, mock_start, mock_stop):
        cfg = _make_config()
        with Scanner(cfg) as s:
            pass
        mock_stop.assert_called_once()

    @patch.object(Scanner, "stop_xray")
    @patch.object(Scanner, "start_xray", return_value="ts")
    @patch("core.scanner.os.path.exists", return_value=True)
    def test_exit_returns_false(self, mock_exists, mock_start, mock_stop):
        cfg = _make_config()
        s = Scanner(cfg)
        result = s.__exit__(None, None, None)
        assert result is False


# ---------------------------------------------------------------------------
# is_xray_running
# ---------------------------------------------------------------------------

class TestIsXrayRunning:

    def test_running(self, scanner):
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        scanner._xray_process = mock_proc
        assert scanner.is_xray_running is True

    def test_not_running_none(self, scanner):
        scanner._xray_process = None
        assert scanner.is_xray_running is False

    def test_not_running_exited(self, scanner):
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 0
        scanner._xray_process = mock_proc
        assert scanner.is_xray_running is False


# ---------------------------------------------------------------------------
# _scan_concurrent
# ---------------------------------------------------------------------------

class TestScanConcurrent:

    @patch.object(Scanner, "scan_target")
    def test_multiple_targets(self, mock_scan, scanner):
        mock_scan.side_effect = [
            {"target": "http://a.com", "success": True},
            {"target": "http://b.com", "success": True},
            {"target": "http://c.com", "success": True},
        ]
        results = scanner._scan_concurrent(["http://a.com", "http://b.com", "http://c.com"])
        assert len(results) == 3

    @patch.object(Scanner, "scan_target")
    def test_one_fails(self, mock_scan, scanner):
        mock_scan.side_effect = [
            {"target": "http://a.com", "success": True},
            RuntimeError("scan crashed"),
            {"target": "http://c.com", "success": True},
        ]
        results = scanner._scan_concurrent(["http://a.com", "http://b.com", "http://c.com"])
        # One result should be the error dict
        failed = [r for r in results if r.get("success") is False and r.get("returncode") == -1]
        assert len(failed) == 1
        assert failed[0]["stderr"] == "scan crashed"


# ---------------------------------------------------------------------------
# _scan_sequential
# ---------------------------------------------------------------------------

class TestScanSequential:

    @patch("core.scanner.time.sleep")
    @patch.object(Scanner, "scan_target")
    def test_interval_between_scans(self, mock_scan, mock_sleep, scanner):
        mock_scan.return_value = {"target": "x", "success": True}
        scanner._scan_sequential(["http://a.com", "http://b.com"])
        # sleep should be called once (between the two targets)
        mock_sleep.assert_called_once_with(scanner._config.scan_interval)

    @patch("core.scanner.time.sleep")
    @patch.object(Scanner, "scan_target")
    def test_single_target_no_sleep(self, mock_scan, mock_sleep, scanner):
        mock_scan.return_value = {"target": "x", "success": True}
        scanner._scan_sequential(["http://a.com"])
        mock_sleep.assert_not_called()

    @patch("core.scanner.time.sleep")
    @patch.object(Scanner, "scan_target")
    def test_results_in_order(self, mock_scan, mock_sleep, scanner):
        results_data = [
            {"target": "http://a.com", "success": True},
            {"target": "http://b.com", "success": False},
            {"target": "http://c.com", "success": True},
        ]
        mock_scan.side_effect = results_data
        results = scanner._scan_sequential(["http://a.com", "http://b.com", "http://c.com"])
        assert len(results) == 3
        assert results[0]["target"] == "http://a.com"
        assert results[1]["target"] == "http://b.com"
        assert results[2]["target"] == "http://c.com"
