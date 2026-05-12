"""
核心扫描器
管理 Xray + Rad 扫描生命周期
"""
import os
import time
import signal
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

from loguru import logger

from .config import ScanConfig
from .errors import ScannerError


class Scanner:
    """安全扫描器（Xray + Rad）"""

    def __init__(self, config: ScanConfig = None):
        self._config = config or ScanConfig()
        self._xray_process: Optional[subprocess.Popen] = None
        self._output_timestamp: str = ""
        self._json_output: str = ""
        self._html_output: str = ""
        self._scan_results: List[Dict[str, Any]] = []

    def __enter__(self):
        self.start_xray()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_xray()
        return False

    def check_prerequisites(self) -> List[str]:
        """检查必要文件，返回缺失列表"""
        missing = []

        if not self._config.xray_path or not os.path.exists(self._config.xray_path):
            missing.append(f"xray: {self._config.xray_path}")

        if not self._config.rad_path or not os.path.exists(self._config.rad_path):
            missing.append(f"rad: {self._config.rad_path}")

        if not self._config.targets and not self._config.targets_file:
            missing.append("targets (无目标)")
        elif self._config.targets_file and not os.path.exists(self._config.targets_file):
            missing.append(f"targets_file: {self._config.targets_file}")

        return missing

    def start_xray(self) -> str:
        """启动 Xray 被动扫描代理，返回输出时间戳"""
        missing = self.check_prerequisites()
        if missing:
            raise ScannerError.prerequisite_missing(missing)

        self._output_timestamp = time.strftime("%Y%m%d%H%M%S", time.localtime())

        # 确保输出目录存在
        os.makedirs(self._config.output_dir, exist_ok=True)

        self._json_output = os.path.join(
            self._config.output_dir, f"{self._output_timestamp}.json"
        )
        self._html_output = os.path.join(
            self._config.output_dir, f"{self._output_timestamp}.html"
        )

        cmd = [
            self._config.xray_path,
            "webscan",
            "--listen", self._config.proxy,
            "--html-output", self._html_output,
            "--json-output", self._json_output,
        ]

        # 如果有自定义 xray 配置
        if self._config.xray_config:
            cmd.extend(["--config", self._config.xray_config])

        try:
            self._xray_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0,
            )
            logger.info(f"Xray 已启动, 监听: {self._config.proxy}, PID: {self._xray_process.pid}")
            logger.info(f"JSON 报告: {self._json_output}")
            logger.info(f"HTML 报告: {self._html_output}")

            # 等待 Xray 启动
            time.sleep(self._config.xray_startup_wait)
            return self._output_timestamp

        except Exception as e:
            raise ScannerError.start_failed("xray", str(e))

    def stop_xray(self) -> None:
        """停止 Xray 进程"""
        if self._xray_process and self._xray_process.poll() is None:
            try:
                if os.name == "nt":
                    # Windows: 使用 taskkill 强制终止进程树
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(self._xray_process.pid)],
                        capture_output=True,
                    )
                else:
                    self._xray_process.terminate()
                    self._xray_process.wait(timeout=10)
                logger.info("Xray 已停止")
            except Exception as e:
                logger.warning(f"停止 Xray 时出错: {e}")
            finally:
                self._xray_process = None

    def scan_target(self, target: str, extra_args: List[str] = None) -> Dict[str, Any]:
        """扫描单个目标"""
        cmd = [
            self._config.rad_path,
            "-t", target,
            "-http-proxy", self._config.proxy,
        ]

        # 如果有自定义 rad 配置
        if self._config.rad_config:
            cmd.extend(["--config", self._config.rad_config])

        if extra_args:
            cmd.extend(extra_args)

        logger.info(f"扫描目标: {target}")
        start_time = time.time()

        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        try:
            stdout, stderr = process.communicate(timeout=300)
        except subprocess.TimeoutExpired:
            logger.warning(f"扫描超时 (300s): {target}, 终止进程")
            process.kill()
            stdout, stderr = process.communicate()
        except Exception as e:
            logger.error(f"扫描异常: {target} - {e}")
            if process.poll() is None:
                process.kill()
            raise
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()

        duration = time.time() - start_time

        result = {
            "target": target,
            "success": process.returncode == 0,
            "returncode": process.returncode,
            "duration": round(duration, 2),
            "stdout": stdout.decode("utf-8", errors="ignore"),
            "stderr": stderr.decode("utf-8", errors="ignore"),
        }

        if result["success"]:
            logger.info(f"  ✓ 扫描完成: {target} ({duration:.1f}s)")
        else:
            logger.warning(f"  ✗ 扫描失败: {target} - {result['stderr'][:200]}")

        self._scan_results.append(result)
        return result

    def scan_all(self, targets: List[str] = None, concurrent: bool = True) -> List[Dict[str, Any]]:
        """扫描所有目标"""
        targets = targets or self._get_targets()
        if not targets:
            logger.warning("无扫描目标")
            return []

        logger.info(f"开始扫描 {len(targets)} 个目标")

        if concurrent and len(targets) > 1:
            return self._scan_concurrent(targets)
        else:
            return self._scan_sequential(targets)

    def scan_with_auth(self, target: str, cookies: Dict[str, str]) -> Dict[str, Any]:
        """带认证 Cookie 扫描目标"""
        # 将 cookie 注入为 rad 额外参数
        cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
        extra_args = ["--header", f"Cookie: {cookie_str}"]
        return self.scan_target(target, extra_args=extra_args)

    def wait_for_results(self) -> None:
        """等待扫描结果生成"""
        logger.info(f"等待扫描结果生成 ({self._config.result_wait}s)...")
        time.sleep(self._config.result_wait)

    def get_results(self) -> Dict[str, Any]:
        """获取扫描结果"""
        return {
            "timestamp": self._output_timestamp,
            "json_output": self._json_output,
            "html_output": self._html_output,
            "scan_results": self._scan_results,
            "total_targets": len(self._scan_results),
            "success_count": sum(1 for r in self._scan_results if r["success"]),
            "fail_count": sum(1 for r in self._scan_results if not r["success"]),
        }

    def _get_targets(self) -> List[str]:
        """获取目标列表"""
        targets = list(self._config.targets)

        if self._config.targets_file and os.path.exists(self._config.targets_file):
            with open(self._config.targets_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        targets.append(line)

        # 去重
        return list(dict.fromkeys(targets))

    def _scan_sequential(self, targets: List[str]) -> List[Dict[str, Any]]:
        """串行扫描"""
        results = []
        for i, target in enumerate(targets, 1):
            logger.info(f"[{i}/{len(targets)}] 扫描目标")
            result = self.scan_target(target)
            results.append(result)

            if i < len(targets):
                time.sleep(self._config.scan_interval)

        return results

    def _scan_concurrent(self, targets: List[str]) -> List[Dict[str, Any]]:
        """并发扫描"""
        results = []
        with ThreadPoolExecutor(max_workers=self._config.max_concurrent) as executor:
            futures = {executor.submit(self.scan_target, t): t for t in targets}
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    target = futures[future]
                    logger.error(f"并发扫描异常: {target} - {e}")
                    results.append({
                        "target": target,
                        "success": False,
                        "returncode": -1,
                        "duration": 0,
                        "stdout": "",
                        "stderr": str(e),
                    })

        return results

    @property
    def is_xray_running(self) -> bool:
        """Xray 是否在运行"""
        return self._xray_process is not None and self._xray_process.poll() is None

    @property
    def config(self) -> ScanConfig:
        return self._config
