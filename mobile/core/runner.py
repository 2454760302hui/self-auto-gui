"""
Mobile 自动化框架 Runner
基于 OperationRegistry 的操作分发，替代 if/elif 链
支持 Allure 报告生成
"""
import os
import time
from typing import Any, Dict, List, Optional

from loguru import logger

# Allure 报告支持
try:
    import allure
    from allure_commons.types import AttachmentType
    HAS_ALLURE = True
except ImportError:
    HAS_ALLURE = False
    allure = None

from .config import ConfigLoader, GlobalConfig
from .variable import VariableResolver
from .locator import SmartLocator
from .errors import MobileError, OperationError, DeviceError
from drivers import create_driver
from drivers.base import PlatformDriver
from operations.registry import OperationRegistry
from operations.base import OperationResult


class Runner:
    """Mobile 自动化框架主执行器"""

    def __init__(self, config_file: str = None, config: Dict[str, Any] = None):
        # 加载配置
        self._config_loader = ConfigLoader(config_path=config_file, config=config)
        self._config = self._config_loader.load(validate=True)

        # 解析配置
        self._global_config = self._config_loader.get_global_config()
        self._flows = self._config_loader.get_flows()
        self._locators = self._config_loader.get_locators()
        self._aliases = self._config_loader.get_aliases()
        self._test_data = self._config_loader.get_test_data()

        # 初始化变量解析器
        self._resolver = VariableResolver(
            test_data=self._test_data,
            aliases=self._aliases,
        )

        # 运行时状态
        self._driver: Optional[PlatformDriver] = None
        self._locator: Optional[SmartLocator] = None
        self._variables: Dict[str, Any] = {}
        self._action_history: List[Dict[str, Any]] = []
        self._success_count: int = 0
        self._fail_count: int = 0
        self._connected: bool = False

        # 确保所有操作已注册
        self._ensure_operations_registered()

    def _ensure_operations_registered(self) -> None:
        """确保所有操作模块已导入（触发注册）"""
        try:
            from operations import (  # noqa: F401
                app, tap, input, swipe, assert_op, wait,
                screenshot, device, file,
            )
        except ImportError as e:
            logger.warning(f"Failed to register operations: {e}")

    def connect_device(self, platform: str = None, device: str = None) -> None:
        """连接设备"""
        platform = platform or self._global_config.platform.platform
        device = device or self._global_config.platform.device

        if not platform:
            raise DeviceError.driver_init_failed("", "未指定平台")

        if not device:
            logger.warning("未指定设备地址，将使用默认设备")

        logger.info(f"连接设备: platform={platform}, device={device}")

        # 创建驱动
        self._driver = create_driver(platform)
        self._driver.connect(device)

        # 初始化定位器
        self._locator = SmartLocator(self._driver, self)
        self._locator.set_locators(self._locators)
        self._locator.set_aliases(self._aliases)

        self._connected = True
        logger.info("设备连接成功")

        # 如果配置了 app，自动启动
        app = self._global_config.platform.app
        if app:
            logger.info(f"自动启动应用: {app}")
            self._driver.launch_app(app)

    def disconnect_device(self) -> None:
        """断开设备连接"""
        if self._driver and self._connected:
            self._driver.disconnect()
            self._connected = False
            logger.info("设备已断开")

    def run_flow(self, flow_name: str) -> bool:
        """执行测试流程"""
        if flow_name not in self._flows:
            raise OperationError.failed(
                "执行流程", f"流程不存在: {flow_name}"
            )

        steps = self._flows[flow_name]
        logger.info(f"开始执行流程: {flow_name} ({len(steps)} 步)")

        flow_success = 0
        flow_fail = 0

        for i, step in enumerate(steps, 1):
            step_name = step.get("name", step.get("名称", f"步骤 {i}"))
            logger.info(f"  [{i}/{len(steps)}] {step_name}")

            # Allure 步骤包装
            if HAS_ALLURE:
                with allure.step(f"步骤 {i}: {step_name}"):
                    result = self._execute_step(step)
                    self._attach_step_result(result, i, step_name)
            else:
                result = self._execute_step(step)

            # 记录历史
            self._action_history.append({
                "flow": flow_name,
                "step": i,
                "name": step_name,
                "success": result.success,
                "error": result.error,
                "duration": result.duration,
            })

            if result.success:
                flow_success += 1
                self._success_count += 1
                logger.info(f"    ✓ 成功 ({result.duration:.2f}s)")
            else:
                flow_fail += 1
                self._fail_count += 1
                logger.error(f"    ✗ 失败: {result.error} ({result.duration:.2f}s)")

                # 失败时截图
                if self._global_config.screenshot.on_fail:
                    self._take_screenshot_on_fail(flow_name, i)

                # Allure 失败记录
                if HAS_ALLURE:
                    allure.attach(
                        f"错误: {result.error}",
                        name="失败原因",
                        attachment_type=allure.attachment_type.TEXT,
                    )

        total = flow_success + flow_fail
        logger.info(
            f"流程完成: {flow_name} - "
            f"成功 {flow_success}/{total}, 失败 {flow_fail}/{total}"
        )

        # Allure 流程摘要
        if HAS_ALLURE:
            allure.attach(
                f"成功: {flow_success}, 失败: {flow_fail}, 总计: {total}",
                name="流程统计",
                attachment_type=allure.attachment_type.TEXT,
            )

        return flow_fail == 0

    def _attach_step_result(self, result: OperationResult, step_num: int, step_name: str) -> None:
        """将步骤结果附加到 Allure 报告"""
        if not HAS_ALLURE:
            return

        # 附加步骤信息
        allure.attach(
            f"步骤: {step_name}\n"
            f"状态: {'成功' if result.success else '失败'}\n"
            f"耗时: {result.duration:.2f}s\n"
            f"错误: {result.error or '无'}",
            name=f"步骤 {step_num} 详情",
            attachment_type=allure.attachment_type.TEXT,
        )

    def _execute_step(self, step: Dict[str, Any]) -> OperationResult:
        """执行单个步骤（基于 OperationRegistry 分发）"""
        # 提取操作类型（忽略 name/名称 键）
        op_keys = [k for k in step.keys() if k not in ("name", "名称")]
        if not op_keys:
            return OperationResult(success=False, error="步骤缺少操作类型")

        op_type = op_keys[0]
        params = step[op_type]

        if not isinstance(params, dict):
            params = {}

        # 解析变量
        params = self._resolver.resolve(params)

        # 通过 Registry 查找操作处理类
        handler_class = OperationRegistry.get_handler(op_type)
        if handler_class is None:
            return OperationResult(
                success=False,
                error=f"未知操作: {op_type}",
            )

        # 创建操作实例并执行
        try:
            handler = handler_class(
                driver=self._driver,
                locator=self._locator,
                resolver=self._resolver,
            )
            result = handler.execute(params)

            # 如果操作设置了变量，保存到 runner
            if result.success and isinstance(result.data, dict):
                save_to = params.get("save_to") or params.get("保存到")
                if save_to:
                    self._resolver.set_variable(save_to, result.data)

            return result
        except Exception as e:
            return OperationResult(success=False, error=f"{type(e).__name__}: {e}")

    def _take_screenshot_on_fail(self, flow_name: str, step_num: int) -> None:
        """失败时截图"""
        try:
            timestamp = int(time.time())
            dir_path = self._global_config.screenshot.dir
            os.makedirs(dir_path, exist_ok=True)
            path = os.path.join(dir_path, f"{flow_name}_step{step_num}_{timestamp}.png")
            self._driver.screenshot(path)
            logger.info(f"    截图已保存: {path}")

            # 附加到 Allure
            if HAS_ALLURE:
                allure.attach.file(
                    path,
                    name=f"失败截图 - 步骤 {step_num}",
                    attachment_type=AttachmentType.PNG,
                )
        except Exception as e:
            logger.warning(f"    截图失败: {e}")

    def list_flows(self) -> List[str]:
        """列出所有流程名称"""
        return list(self._flows.keys())

    def get_history(self) -> List[Dict[str, Any]]:
        """获取执行历史"""
        return list(self._action_history)

    def get_variables(self) -> Dict[str, Any]:
        """获取当前变量"""
        return self._resolver.variables

    def set_variable(self, name: str, value: Any) -> None:
        """设置变量"""
        self._resolver.set_variable(name, value)

    @property
    def driver(self) -> Optional[PlatformDriver]:
        return self._driver

    @property
    def success_count(self) -> int:
        return self._success_count

    @property
    def fail_count(self) -> int:
        return self._fail_count

    @property
    def connected(self) -> bool:
        return self._connected
