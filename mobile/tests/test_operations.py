"""
Operations 单元测试 — 测试所有操作类
使用 mock 隔离 driver / locator / resolver 依赖
"""
import os
import sys
import time
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from operations.base import OperationBase, OperationResult
from operations.tap import TapOperation, LongPressOperation, DoubleTapOperation
from operations.input import InputOperation, PressKeyOperation, ClearOperation
from operations.swipe import SwipeOperation, ScrollOperation, PinchOperation, ZoomOperation
from operations.assert_op import AssertOperation
from operations.wait import WaitOperation, WaitForElementOperation
from operations.screenshot import ScreenshotOperation
from operations.device import GetDeviceInfoOperation, RotateDeviceOperation, HardwareKeyOperation
from operations.app import LaunchAppOperation, CloseAppOperation, InstallAppOperation, UninstallAppOperation
from operations.file import PullFileOperation, PushFileOperation
from operations.registry import OperationRegistry
from core.errors import OperationError, AssertFailError, LocatorError
from core.variable import VariableResolver


# ════════════════════════════════════════════════════════════════
#  Fixtures & helpers
# ════════════════════════════════════════════════════════════════

def make_mock_deps():
    """创建 mock driver, locator, resolver"""
    driver = MagicMock()
    driver.supported_strategies = [
        "resource_id", "accessibility_id", "text", "description",
        "class_name", "xpath", "predicate", "class_chain",
    ]

    locator = MagicMock()
    resolver = VariableResolver()
    return driver, locator, resolver


def make_op(op_class):
    """创建操作实例（带 mock 依赖）"""
    driver, locator, resolver = make_mock_deps()
    op = op_class(driver, locator, resolver)
    return op, driver, locator, resolver


# ════════════════════════════════════════════════════════════════
#  OperationResult
# ════════════════════════════════════════════════════════════════

class TestOperationResult:

    def test_defaults(self):
        r = OperationResult()
        assert r.success is True
        assert r.error is None
        assert r.data is None
        assert r.retried == 0
        assert r.recovered is False
        assert r.strategy is None
        assert r.duration == 0.0

    def test_to_dict(self):
        r = OperationResult(success=False, error="oops", data={"k": 1}, retried=2,
                            recovered=True, strategy="retry", duration=0.5)
        d = r.to_dict()
        assert d["success"] is False
        assert d["error"] == "oops"
        assert d["data"] == {"k": 1}
        assert d["retried"] == 2
        assert d["recovered"] is True
        assert d["strategy"] == "retry"
        assert d["duration"] == 0.5

    def test_custom_values(self):
        r = OperationResult(success=True, data="hello")
        assert r.data == "hello"


# ════════════════════════════════════════════════════════════════
#  TapOperation
# ════════════════════════════════════════════════════════════════

class TestTapOperation:

    def test_coordinate_tap(self):
        op, driver, locator, resolver = make_op(TapOperation)
        result = op.execute({"x": 100, "y": 200})
        assert result.success is True
        assert result.data == {"x": 100, "y": 200}
        driver.tap_coordinate.assert_called_once_with(100, 200)

    def test_coordinate_tap_string_values(self):
        op, driver, locator, resolver = make_op(TapOperation)
        result = op.execute({"x": "50", "y": "75"})
        assert result.success is True
        driver.tap_coordinate.assert_called_once_with(50, 75)

    def test_element_tap(self):
        op, driver, locator, resolver = make_op(TapOperation)
        mock_element = MagicMock()
        locator.locate.return_value = mock_element
        result = op.execute({"定位器": "text=Login"})
        assert result.success is True
        driver.tap.assert_called_once_with(mock_element)

    def test_coordinate_dict_tap(self):
        """当 locator 返回坐标 dict 时，应调用 tap_coordinate"""
        op, driver, locator, resolver = make_op(TapOperation)
        locator.locate.return_value = {"type": "coordinate", "x": 42, "y": 99}
        result = op.execute({"定位器": "image=template.png"})
        assert result.success is True
        driver.tap_coordinate.assert_called_once_with(42, 99)

    def test_element_not_found(self):
        op, driver, locator, resolver = make_op(TapOperation)
        locator.locate.return_value = None
        result = op.execute({"定位器": "text=Missing"})
        assert result.success is False
        assert "未找到元素" in result.error

    def test_duration_recorded(self):
        op, driver, locator, resolver = make_op(TapOperation)
        result = op.execute({"x": 10, "y": 20})
        assert result.duration >= 0


# ════════════════════════════════════════════════════════════════
#  LongPressOperation
# ════════════════════════════════════════════════════════════════

class TestLongPressOperation:

    def test_default_duration(self):
        op, driver, locator, resolver = make_op(LongPressOperation)
        mock_element = MagicMock()
        locator.locate.return_value = mock_element
        result = op.execute({"定位器": "rid=btn"})
        assert result.success is True
        assert result.data["duration"] == 1.0
        driver.long_press.assert_called_once_with(mock_element, 1.0)

    def test_custom_duration(self):
        op, driver, locator, resolver = make_op(LongPressOperation)
        mock_element = MagicMock()
        locator.locate.return_value = mock_element
        result = op.execute({"定位器": "rid=btn", "duration": 3.0})
        assert result.success is True
        assert result.data["duration"] == 3.0

    def test_chinese_duration_key(self):
        op, driver, locator, resolver = make_op(LongPressOperation)
        mock_element = MagicMock()
        locator.locate.return_value = mock_element
        result = op.execute({"定位器": "rid=btn", "持续时间": 2.5})
        assert result.success is True
        assert result.data["duration"] == 2.5

    def test_coordinate_element(self):
        op, driver, locator, resolver = make_op(LongPressOperation)
        locator.locate.return_value = {"type": "coordinate", "x": 50, "y": 60}
        result = op.execute({"定位器": "coord=50,60"})
        assert result.success is True
        driver.tap_coordinate.assert_called_once_with(50, 60)

    def test_element_not_found(self):
        op, driver, locator, resolver = make_op(LongPressOperation)
        locator.locate.return_value = None
        result = op.execute({"定位器": "text=Gone"})
        assert result.success is False
        assert "未找到元素" in result.error


# ════════════════════════════════════════════════════════════════
#  DoubleTapOperation
# ════════════════════════════════════════════════════════════════

class TestDoubleTapOperation:

    def test_element_double_tap(self):
        op, driver, locator, resolver = make_op(DoubleTapOperation)
        mock_element = MagicMock()
        locator.locate.return_value = mock_element
        result = op.execute({"定位器": "text=Item"})
        assert result.success is True
        driver.double_tap.assert_called_once_with(mock_element)

    def test_coordinate_element(self):
        op, driver, locator, resolver = make_op(DoubleTapOperation)
        locator.locate.return_value = {"type": "coordinate", "x": 10, "y": 20}
        result = op.execute({"定位器": "image=icon.png"})
        assert result.success is True
        driver.tap_coordinate.assert_called_once_with(10, 20)

    def test_element_not_found(self):
        op, driver, locator, resolver = make_op(DoubleTapOperation)
        locator.locate.return_value = None
        result = op.execute({"定位器": "text=None"})
        assert result.success is False
        assert "未找到元素" in result.error


# ════════════════════════════════════════════════════════════════
#  InputOperation
# ════════════════════════════════════════════════════════════════

class TestInputOperation:

    def test_input_with_value(self):
        op, driver, locator, resolver = make_op(InputOperation)
        mock_element = MagicMock()
        locator.locate.return_value = mock_element
        result = op.execute({"value": "hello", "定位器": "rid=input"})
        assert result.success is True
        assert result.data["text"] == "hello"
        driver.input_text.assert_called_once_with(mock_element, "hello")

    def test_input_with_chinese_key(self):
        op, driver, locator, resolver = make_op(InputOperation)
        mock_element = MagicMock()
        locator.locate.return_value = mock_element
        result = op.execute({"值": "world", "定位器": "rid=field"})
        assert result.success is True
        assert result.data["text"] == "world"

    def test_input_with_text_key(self):
        op, driver, locator, resolver = make_op(InputOperation)
        mock_element = MagicMock()
        locator.locate.return_value = mock_element
        result = op.execute({"text": "content", "定位器": "rid=f"})
        assert result.success is True
        assert result.data["text"] == "content"

    def test_missing_value_raises(self):
        op, driver, locator, resolver = make_op(InputOperation)
        result = op.execute({"定位器": "rid=input"})
        assert result.success is False
        assert "value" in result.error or "缺少" in result.error

    def test_element_not_found(self):
        op, driver, locator, resolver = make_op(InputOperation)
        locator.locate.return_value = None
        result = op.execute({"value": "text", "定位器": "rid=missing"})
        assert result.success is False

    def test_variable_resolution(self):
        op, driver, locator, resolver = make_op(InputOperation)
        resolver.set_variable("username", "admin")
        mock_element = MagicMock()
        locator.locate.return_value = mock_element
        result = op.execute({"value": "${username}", "定位器": "rid=f"})
        assert result.success is True
        assert result.data["text"] == "admin"


# ════════════════════════════════════════════════════════════════
#  PressKeyOperation
# ════════════════════════════════════════════════════════════════

class TestPressKeyOperation:

    def test_press_key(self):
        op, driver, locator, resolver = make_op(PressKeyOperation)
        result = op.execute({"key": "enter"})
        assert result.success is True
        assert result.data["key"] == "enter"
        driver.press_key.assert_called_once_with("enter")

    def test_press_key_chinese(self):
        op, driver, locator, resolver = make_op(PressKeyOperation)
        result = op.execute({"按键": "back"})
        assert result.success is True
        assert result.data["key"] == "back"

    def test_missing_key_raises(self):
        op, driver, locator, resolver = make_op(PressKeyOperation)
        result = op.execute({})
        assert result.success is False
        assert "key" in result.error or "缺少" in result.error


# ════════════════════════════════════════════════════════════════
#  ClearOperation
# ════════════════════════════════════════════════════════════════

class TestClearOperation:

    def test_clear_text(self):
        op, driver, locator, resolver = make_op(ClearOperation)
        mock_element = MagicMock()
        locator.locate.return_value = mock_element
        result = op.execute({"定位器": "rid=field"})
        assert result.success is True
        driver.clear_text.assert_called_once_with(mock_element)

    def test_element_not_found(self):
        op, driver, locator, resolver = make_op(ClearOperation)
        locator.locate.return_value = None
        result = op.execute({"定位器": "rid=gone"})
        assert result.success is False
        assert "未找到元素" in result.error


# ════════════════════════════════════════════════════════════════
#  SwipeOperation
# ════════════════════════════════════════════════════════════════

class TestSwipeOperation:

    def test_swipe_up(self):
        op, driver, locator, resolver = make_op(SwipeOperation)
        result = op.execute({"direction": "up"})
        assert result.success is True
        assert result.data["direction"] == "up"
        driver.swipe.assert_called_once_with("up")

    def test_swipe_down(self):
        op, driver, locator, resolver = make_op(SwipeOperation)
        result = op.execute({"direction": "down"})
        assert result.success is True
        driver.swipe.assert_called_once_with("down")

    def test_swipe_left(self):
        op, driver, locator, resolver = make_op(SwipeOperation)
        result = op.execute({"direction": "left"})
        assert result.success is True

    def test_swipe_right(self):
        op, driver, locator, resolver = make_op(SwipeOperation)
        result = op.execute({"direction": "right"})
        assert result.success is True

    def test_swipe_chinese_direction(self):
        op, driver, locator, resolver = make_op(SwipeOperation)
        result = op.execute({"方向": "up"})
        assert result.success is True

    def test_swipe_with_scale(self):
        op, driver, locator, resolver = make_op(SwipeOperation)
        result = op.execute({"direction": "up", "scale": 0.5})
        assert result.success is True
        driver.swipe.assert_called_once_with("up", scale=0.5)

    def test_missing_direction_raises(self):
        op, driver, locator, resolver = make_op(SwipeOperation)
        result = op.execute({})
        assert result.success is False
        assert "direction" in result.error or "缺少" in result.error

    def test_invalid_direction_raises(self):
        op, driver, locator, resolver = make_op(SwipeOperation)
        result = op.execute({"direction": "diagonal"})
        assert result.success is False
        assert "无效方向" in result.error


# ════════════════════════════════════════════════════════════════
#  ScrollOperation
# ════════════════════════════════════════════════════════════════

class TestScrollOperation:

    def test_scroll_to_text(self):
        op, driver, locator, resolver = make_op(ScrollOperation)
        result = op.execute({"text": "Settings"})
        assert result.success is True
        assert result.data["text"] == "Settings"
        driver.scroll_to_text.assert_called_once_with("Settings")

    def test_scroll_by_direction(self):
        op, driver, locator, resolver = make_op(ScrollOperation)
        result = op.execute({"direction": "down"})
        assert result.success is True
        driver.swipe.assert_called_once_with("down")

    def test_scroll_default_direction(self):
        op, driver, locator, resolver = make_op(ScrollOperation)
        result = op.execute({})
        assert result.success is True
        driver.swipe.assert_called_once_with("down")

    def test_scroll_chinese_text(self):
        op, driver, locator, resolver = make_op(ScrollOperation)
        result = op.execute({"文本": "设置"})
        assert result.success is True
        driver.scroll_to_text.assert_called_once_with("设置")


# ════════════════════════════════════════════════════════════════
#  PinchOperation
# ════════════════════════════════════════════════════════════════

class TestPinchOperation:

    def test_pinch_default_scale(self):
        op, driver, locator, resolver = make_op(PinchOperation)
        mock_element = MagicMock()
        locator.locate.return_value = mock_element
        result = op.execute({"定位器": "rid=map"})
        assert result.success is True
        assert result.data["scale"] == 0.5
        driver.pinch.assert_called_once_with(mock_element, 0.5)

    def test_pinch_custom_scale(self):
        op, driver, locator, resolver = make_op(PinchOperation)
        mock_element = MagicMock()
        locator.locate.return_value = mock_element
        result = op.execute({"定位器": "rid=map", "scale": 0.3})
        assert result.success is True
        assert result.data["scale"] == 0.3

    def test_pinch_chinese_scale(self):
        op, driver, locator, resolver = make_op(PinchOperation)
        mock_element = MagicMock()
        locator.locate.return_value = mock_element
        result = op.execute({"定位器": "rid=map", "比例": 0.7})
        assert result.success is True
        assert result.data["scale"] == 0.7

    def test_element_not_found(self):
        op, driver, locator, resolver = make_op(PinchOperation)
        locator.locate.return_value = None
        result = op.execute({"定位器": "rid=missing"})
        assert result.success is False


# ════════════════════════════════════════════════════════════════
#  ZoomOperation
# ════════════════════════════════════════════════════════════════

class TestZoomOperation:

    def test_zoom_default_scale(self):
        op, driver, locator, resolver = make_op(ZoomOperation)
        mock_element = MagicMock()
        locator.locate.return_value = mock_element
        result = op.execute({"定位器": "rid=img"})
        assert result.success is True
        assert result.data["scale"] == 2.0
        driver.zoom.assert_called_once_with(mock_element, 2.0)

    def test_zoom_custom_scale(self):
        op, driver, locator, resolver = make_op(ZoomOperation)
        mock_element = MagicMock()
        locator.locate.return_value = mock_element
        result = op.execute({"定位器": "rid=img", "scale": 3.0})
        assert result.success is True
        assert result.data["scale"] == 3.0

    def test_element_not_found(self):
        op, driver, locator, resolver = make_op(ZoomOperation)
        locator.locate.return_value = None
        result = op.execute({"定位器": "rid=missing"})
        assert result.success is False


# ════════════════════════════════════════════════════════════════
#  AssertOperation
# ════════════════════════════════════════════════════════════════

class TestAssertOperation:

    def test_assert_visible_true(self):
        op, driver, locator, resolver = make_op(AssertOperation)
        mock_el = MagicMock()
        locator.locate.return_value = mock_el
        driver.is_visible.return_value = True
        result = op.execute({"visible": True, "定位器": "rid=btn"})
        assert result.success is True
        assert result.data["visible"] is True

    def test_assert_visible_false_element_not_found(self):
        op, driver, locator, resolver = make_op(AssertOperation)
        locator.locate.return_value = None
        result = op.execute({"visible": False, "定位器": "rid=hidden"})
        assert result.success is True
        assert result.data["visible"] is False

    def test_assert_visible_fail(self):
        op, driver, locator, resolver = make_op(AssertOperation)
        mock_el = MagicMock()
        locator.locate.return_value = mock_el
        driver.is_visible.return_value = False
        result = op.execute({"visible": True, "定位器": "rid=btn"})
        assert result.success is False
        assert "不可见" in result.error

    def test_assert_visible_expected_false_but_visible(self):
        op, driver, locator, resolver = make_op(AssertOperation)
        mock_el = MagicMock()
        locator.locate.return_value = mock_el
        driver.is_visible.return_value = True
        result = op.execute({"visible": False, "定位器": "rid=btn"})
        assert result.success is False

    def test_assert_visible_not_found_expected_true_fails(self):
        op, driver, locator, resolver = make_op(AssertOperation)
        locator.locate.return_value = None
        result = op.execute({"visible": True, "定位器": "rid=missing"})
        assert result.success is False
        assert "不可见" in result.error

    def test_assert_text_match(self):
        op, driver, locator, resolver = make_op(AssertOperation)
        mock_el = MagicMock()
        locator.locate.return_value = mock_el
        driver.get_text.return_value = "Hello"
        result = op.execute({"text": "Hello", "定位器": "rid=label"})
        assert result.success is True
        assert result.data["text"] == "Hello"

    def test_assert_text_mismatch(self):
        op, driver, locator, resolver = make_op(AssertOperation)
        mock_el = MagicMock()
        locator.locate.return_value = mock_el
        driver.get_text.return_value = "World"
        result = op.execute({"text": "Hello", "定位器": "rid=label"})
        assert result.success is False
        assert "不匹配" in result.error

    def test_assert_text_chinese_key(self):
        op, driver, locator, resolver = make_op(AssertOperation)
        mock_el = MagicMock()
        locator.locate.return_value = mock_el
        driver.get_text.return_value = "你好"
        result = op.execute({"文本": "你好", "定位器": "rid=label"})
        assert result.success is True

    def test_assert_text_element_not_found(self):
        op, driver, locator, resolver = make_op(AssertOperation)
        locator.locate.return_value = None
        result = op.execute({"text": "Hello", "定位器": "rid=missing"})
        assert result.success is False

    def test_assert_attribute_match(self):
        op, driver, locator, resolver = make_op(AssertOperation)
        mock_el = MagicMock()
        locator.locate.return_value = mock_el
        driver.get_attribute.return_value = "checked"
        result = op.execute({"attribute": "state", "value": "checked", "定位器": "rid=cb"})
        assert result.success is True
        assert result.data["state"] == "checked"

    def test_assert_attribute_mismatch(self):
        op, driver, locator, resolver = make_op(AssertOperation)
        mock_el = MagicMock()
        locator.locate.return_value = mock_el
        driver.get_attribute.return_value = "unchecked"
        result = op.execute({"attribute": "state", "value": "checked", "定位器": "rid=cb"})
        assert result.success is False

    def test_assert_attribute_chinese_key(self):
        op, driver, locator, resolver = make_op(AssertOperation)
        mock_el = MagicMock()
        locator.locate.return_value = mock_el
        driver.get_attribute.return_value = "yes"
        result = op.execute({"属性": "checked", "值": "yes", "定位器": "rid=cb"})
        assert result.success is True

    def test_assert_attribute_element_not_found(self):
        op, driver, locator, resolver = make_op(AssertOperation)
        locator.locate.return_value = None
        result = op.execute({"attribute": "state", "value": "v", "定位器": "rid=missing"})
        assert result.success is False

    def test_assert_exists_true(self):
        op, driver, locator, resolver = make_op(AssertOperation)
        mock_el = MagicMock()
        locator.locate.return_value = mock_el
        result = op.execute({"exists": True, "定位器": "rid=btn"})
        assert result.success is True
        assert result.data["exists"] is True

    def test_assert_exists_false(self):
        op, driver, locator, resolver = make_op(AssertOperation)
        locator.locate.return_value = None
        result = op.execute({"exists": False, "定位器": "rid=btn"})
        assert result.success is True
        assert result.data["exists"] is False

    def test_assert_exists_expected_true_but_not(self):
        op, driver, locator, resolver = make_op(AssertOperation)
        locator.locate.return_value = None
        result = op.execute({"exists": True, "定位器": "rid=missing"})
        assert result.success is False
        assert "不存在" in result.error

    def test_assert_exists_expected_false_but_exists(self):
        op, driver, locator, resolver = make_op(AssertOperation)
        locator.locate.return_value = MagicMock()
        result = op.execute({"exists": False, "定位器": "rid=btn"})
        assert result.success is False
        assert "不应存在" in result.error

    def test_assert_default_visible(self):
        """无特定断言 key 时默认断言 visible"""
        op, driver, locator, resolver = make_op(AssertOperation)
        mock_el = MagicMock()
        locator.locate.return_value = mock_el
        driver.is_visible.return_value = True
        result = op.execute({"定位器": "rid=btn"})
        assert result.success is True

    def test_assert_visible_chinese_key(self):
        op, driver, locator, resolver = make_op(AssertOperation)
        mock_el = MagicMock()
        locator.locate.return_value = mock_el
        driver.is_visible.return_value = True
        result = op.execute({"可见": True, "定位器": "rid=btn"})
        assert result.success is True

    def test_assert_exists_chinese_key(self):
        op, driver, locator, resolver = make_op(AssertOperation)
        mock_el = MagicMock()
        locator.locate.return_value = mock_el
        result = op.execute({"存在": True, "定位器": "rid=btn"})
        assert result.success is True


# ════════════════════════════════════════════════════════════════
#  WaitOperation
# ════════════════════════════════════════════════════════════════

class TestWaitOperation:

    def test_wait_default(self):
        op, driver, locator, resolver = make_op(WaitOperation)
        start = time.time()
        result = op.execute({"seconds": 0.01})
        elapsed = time.time() - start
        assert result.success is True
        assert result.data["seconds"] == 0.01
        assert elapsed >= 0.01

    def test_wait_chinese_key(self):
        op, driver, locator, resolver = make_op(WaitOperation)
        result = op.execute({"秒": 0.01})
        assert result.success is True
        assert result.data["seconds"] == 0.01

    def test_wait_capped_at_60(self):
        op, driver, locator, resolver = make_op(WaitOperation)
        with patch("operations.wait.time.sleep") as mock_sleep:
            result = op.execute({"seconds": 120})
            assert result.success is True
            assert result.data["seconds"] == 60.0
            mock_sleep.assert_called_once_with(60.0)

    def test_wait_default_one_second(self):
        op, driver, locator, resolver = make_op(WaitOperation)
        with patch("operations.wait.time.sleep") as mock_sleep:
            result = op.execute({})
            assert result.success is True
            assert result.data["seconds"] == 1.0
            mock_sleep.assert_called_once_with(1.0)


# ════════════════════════════════════════════════════════════════
#  WaitForElementOperation
# ════════════════════════════════════════════════════════════════

class TestWaitForElementOperation:

    def test_element_found(self):
        op, driver, locator, resolver = make_op(WaitForElementOperation)
        mock_el = MagicMock()
        driver.wait_for_element.return_value = mock_el
        result = op.execute({"定位器": "rid=btn", "timeout": 5000})
        assert result.success is True
        assert result.data["found"] is True

    def test_element_not_found_timeout(self):
        op, driver, locator, resolver = make_op(WaitForElementOperation)
        driver.wait_for_element.return_value = None
        result = op.execute({"定位器": "rid=missing", "timeout": 1000})
        assert result.success is False
        assert "超时" in result.error

    def test_missing_locator_config(self):
        op, driver, locator, resolver = make_op(WaitForElementOperation)
        result = op.execute({"timeout": 5000})
        assert result.success is False
        assert "未指定" in result.error

    def test_default_timeout(self):
        op, driver, locator, resolver = make_op(WaitForElementOperation)
        mock_el = MagicMock()
        driver.wait_for_element.return_value = mock_el
        result = op.execute({"定位器": "rid=btn"})
        assert result.success is True
        call_args = driver.wait_for_element.call_args
        assert call_args[0][1] == 10000  # default timeout

    def test_chinese_timeout_key(self):
        op, driver, locator, resolver = make_op(WaitForElementOperation)
        mock_el = MagicMock()
        driver.wait_for_element.return_value = mock_el
        result = op.execute({"定位器": "rid=btn", "超时": 3000})
        assert result.success is True

    def test_element_key(self):
        op, driver, locator, resolver = make_op(WaitForElementOperation)
        mock_el = MagicMock()
        driver.wait_for_element.return_value = mock_el
        result = op.execute({"元素": "login_btn"})
        assert result.success is True


# ════════════════════════════════════════════════════════════════
#  ScreenshotOperation
# ════════════════════════════════════════════════════════════════

class TestScreenshotOperation:

    def test_screenshot_with_path(self):
        op, driver, locator, resolver = make_op(ScreenshotOperation)
        with patch("os.makedirs"):
            result = op.execute({"path": "/tmp/test_shot.png"})
        assert result.success is True
        assert result.data["path"] == "/tmp/test_shot.png"
        driver.screenshot.assert_called_once_with("/tmp/test_shot.png")

    def test_screenshot_with_chinese_path(self):
        op, driver, locator, resolver = make_op(ScreenshotOperation)
        with patch("os.makedirs"):
            result = op.execute({"路径": "/tmp/cn_shot.png"})
        assert result.success is True
        assert result.data["path"] == "/tmp/cn_shot.png"

    def test_screenshot_auto_path(self):
        op, driver, locator, resolver = make_op(ScreenshotOperation)
        with patch("os.makedirs"):
            result = op.execute({})
        assert result.success is True
        assert "screenshot_" in result.data["path"]
        assert result.data["path"].endswith(".png")

    def test_screenshot_creates_directory(self):
        op, driver, locator, resolver = make_op(ScreenshotOperation)
        with patch("os.makedirs") as mock_mkdir:
            result = op.execute({"path": "deep/nested/dir/shot.png"})
        assert result.success is True
        mock_mkdir.assert_called_once_with("deep/nested/dir", exist_ok=True)


# ════════════════════════════════════════════════════════════════
#  GetDeviceInfoOperation
# ════════════════════════════════════════════════════════════════

class TestGetDeviceInfoOperation:

    def test_get_device_info(self):
        op, driver, locator, resolver = make_op(GetDeviceInfoOperation)
        driver.get_device_info.return_value = {"model": "Pixel 7", "os": "Android 14"}
        result = op.execute({})
        assert result.success is True
        assert result.data["model"] == "Pixel 7"
        driver.get_device_info.assert_called_once()

    def test_get_device_info_ignores_params(self):
        op, driver, locator, resolver = make_op(GetDeviceInfoOperation)
        driver.get_device_info.return_value = {}
        result = op.execute({"extra": "ignored"})
        assert result.success is True


# ════════════════════════════════════════════════════════════════
#  RotateDeviceOperation
# ════════════════════════════════════════════════════════════════

class TestRotateDeviceOperation:

    def test_rotate_portrait(self):
        op, driver, locator, resolver = make_op(RotateDeviceOperation)
        result = op.execute({"orientation": "portrait"})
        assert result.success is True
        driver.rotate_device.assert_called_once_with("portrait")

    def test_rotate_landscape(self):
        op, driver, locator, resolver = make_op(RotateDeviceOperation)
        result = op.execute({"orientation": "landscape"})
        assert result.success is True

    def test_rotate_left(self):
        op, driver, locator, resolver = make_op(RotateDeviceOperation)
        result = op.execute({"orientation": "left"})
        assert result.success is True

    def test_rotate_right(self):
        op, driver, locator, resolver = make_op(RotateDeviceOperation)
        result = op.execute({"orientation": "right"})
        assert result.success is True

    def test_rotate_chinese_key(self):
        op, driver, locator, resolver = make_op(RotateDeviceOperation)
        result = op.execute({"方向": "portrait"})
        assert result.success is True

    def test_missing_orientation_raises(self):
        op, driver, locator, resolver = make_op(RotateDeviceOperation)
        result = op.execute({})
        assert result.success is False
        assert "orientation" in result.error or "缺少" in result.error

    def test_invalid_orientation_raises(self):
        op, driver, locator, resolver = make_op(RotateDeviceOperation)
        result = op.execute({"orientation": "upside_down"})
        assert result.success is False
        assert "无效方向" in result.error


# ════════════════════════════════════════════════════════════════
#  HardwareKeyOperation
# ════════════════════════════════════════════════════════════════

class TestHardwareKeyOperation:

    def test_hardware_key(self):
        op, driver, locator, resolver = make_op(HardwareKeyOperation)
        result = op.execute({"key": "volume_up"})
        assert result.success is True
        assert result.data["key"] == "volume_up"
        driver.press_key.assert_called_once_with("volume_up")

    def test_hardware_key_chinese(self):
        op, driver, locator, resolver = make_op(HardwareKeyOperation)
        result = op.execute({"按键": "home"})
        assert result.success is True
        assert result.data["key"] == "home"

    def test_missing_key_raises(self):
        op, driver, locator, resolver = make_op(HardwareKeyOperation)
        result = op.execute({})
        assert result.success is False
        assert "key" in result.error or "缺少" in result.error


# ════════════════════════════════════════════════════════════════
#  LaunchAppOperation
# ════════════════════════════════════════════════════════════════

class TestLaunchAppOperation:

    def test_launch_app(self):
        op, driver, locator, resolver = make_op(LaunchAppOperation)
        result = op.execute({"package": "com.example.app"})
        assert result.success is True
        assert result.data["package"] == "com.example.app"
        driver.launch_app.assert_called_once_with("com.example.app", None)

    def test_launch_app_with_activity(self):
        op, driver, locator, resolver = make_op(LaunchAppOperation)
        result = op.execute({"package": "com.example.app", "activity": ".MainActivity"})
        assert result.success is True
        assert result.data["activity"] == ".MainActivity"
        driver.launch_app.assert_called_once_with("com.example.app", ".MainActivity")

    def test_launch_app_chinese_params(self):
        op, driver, locator, resolver = make_op(LaunchAppOperation)
        result = op.execute({"包名": "com.example.app", "活动": ".Main"})
        assert result.success is True

    def test_missing_package_raises(self):
        op, driver, locator, resolver = make_op(LaunchAppOperation)
        result = op.execute({})
        assert result.success is False
        assert "package" in result.error or "缺少" in result.error


# ════════════════════════════════════════════════════════════════
#  CloseAppOperation
# ════════════════════════════════════════════════════════════════

class TestCloseAppOperation:

    def test_close_app(self):
        op, driver, locator, resolver = make_op(CloseAppOperation)
        result = op.execute({"package": "com.example.app"})
        assert result.success is True
        driver.close_app.assert_called_once_with("com.example.app")

    def test_close_app_chinese(self):
        op, driver, locator, resolver = make_op(CloseAppOperation)
        result = op.execute({"包名": "com.example.app"})
        assert result.success is True

    def test_missing_package_raises(self):
        op, driver, locator, resolver = make_op(CloseAppOperation)
        result = op.execute({})
        assert result.success is False


# ════════════════════════════════════════════════════════════════
#  InstallAppOperation
# ════════════════════════════════════════════════════════════════

class TestInstallAppOperation:

    def test_install_app(self):
        op, driver, locator, resolver = make_op(InstallAppOperation)
        result = op.execute({"path": "/tmp/app.apk"})
        assert result.success is True
        assert result.data["path"] == "/tmp/app.apk"
        driver.install_app.assert_called_once_with("/tmp/app.apk")

    def test_install_app_chinese(self):
        op, driver, locator, resolver = make_op(InstallAppOperation)
        result = op.execute({"路径": "/tmp/app.apk"})
        assert result.success is True

    def test_missing_path_raises(self):
        op, driver, locator, resolver = make_op(InstallAppOperation)
        result = op.execute({})
        assert result.success is False


# ════════════════════════════════════════════════════════════════
#  UninstallAppOperation
# ════════════════════════════════════════════════════════════════

class TestUninstallAppOperation:

    def test_uninstall_app(self):
        op, driver, locator, resolver = make_op(UninstallAppOperation)
        result = op.execute({"package": "com.example.app"})
        assert result.success is True
        driver.uninstall_app.assert_called_once_with("com.example.app")

    def test_uninstall_app_chinese(self):
        op, driver, locator, resolver = make_op(UninstallAppOperation)
        result = op.execute({"包名": "com.example.app"})
        assert result.success is True

    def test_missing_package_raises(self):
        op, driver, locator, resolver = make_op(UninstallAppOperation)
        result = op.execute({})
        assert result.success is False


# ════════════════════════════════════════════════════════════════
#  PullFileOperation
# ════════════════════════════════════════════════════════════════

class TestPullFileOperation:

    def test_pull_file(self):
        op, driver, locator, resolver = make_op(PullFileOperation)
        result = op.execute({"remote": "/data/file.txt", "local": "/tmp/file.txt"})
        assert result.success is True
        assert result.data["remote"] == "/data/file.txt"
        assert result.data["local"] == "/tmp/file.txt"
        driver.pull_file.assert_called_once_with("/data/file.txt", "/tmp/file.txt")

    def test_pull_file_chinese(self):
        op, driver, locator, resolver = make_op(PullFileOperation)
        result = op.execute({"远程路径": "/sdcard/a.txt", "本地路径": "/tmp/a.txt"})
        assert result.success is True

    def test_missing_remote_raises(self):
        op, driver, locator, resolver = make_op(PullFileOperation)
        result = op.execute({"local": "/tmp/a.txt"})
        assert result.success is False
        assert "remote" in result.error or "缺少" in result.error

    def test_missing_local_raises(self):
        op, driver, locator, resolver = make_op(PullFileOperation)
        result = op.execute({"remote": "/sdcard/a.txt"})
        assert result.success is False
        assert "local" in result.error or "缺少" in result.error

    def test_missing_all_params_raises(self):
        op, driver, locator, resolver = make_op(PullFileOperation)
        result = op.execute({})
        assert result.success is False


# ════════════════════════════════════════════════════════════════
#  PushFileOperation
# ════════════════════════════════════════════════════════════════

class TestPushFileOperation:

    def test_push_file(self):
        op, driver, locator, resolver = make_op(PushFileOperation)
        result = op.execute({"local": "/tmp/file.txt", "remote": "/sdcard/file.txt"})
        assert result.success is True
        assert result.data["local"] == "/tmp/file.txt"
        assert result.data["remote"] == "/sdcard/file.txt"
        driver.push_file.assert_called_once_with("/tmp/file.txt", "/sdcard/file.txt")

    def test_push_file_chinese(self):
        op, driver, locator, resolver = make_op(PushFileOperation)
        result = op.execute({"本地路径": "/tmp/a.txt", "远程路径": "/sdcard/a.txt"})
        assert result.success is True

    def test_missing_local_raises(self):
        op, driver, locator, resolver = make_op(PushFileOperation)
        result = op.execute({"remote": "/sdcard/a.txt"})
        assert result.success is False

    def test_missing_remote_raises(self):
        op, driver, locator, resolver = make_op(PushFileOperation)
        result = op.execute({"local": "/tmp/a.txt"})
        assert result.success is False

    def test_missing_all_params_raises(self):
        op, driver, locator, resolver = make_op(PushFileOperation)
        result = op.execute({})
        assert result.success is False


# ════════════════════════════════════════════════════════════════
#  OperationBase execute() error handling
# ════════════════════════════════════════════════════════════════

class TestOperationBaseErrorHandling:

    def test_execute_catches_operation_error(self):
        op, driver, locator, resolver = make_op(TapOperation)
        locator.locate.return_value = None
        result = op.execute({"定位器": "text=missing"})
        assert result.success is False
        assert result.error is not None
        assert result.duration >= 0

    def test_execute_catches_generic_exception(self):
        op, driver, locator, resolver = make_op(TapOperation)
        driver.tap_coordinate.side_effect = RuntimeError("device disconnected")
        result = op.execute({"x": 10, "y": 20})
        assert result.success is False
        assert "RuntimeError" in result.error
        assert "device disconnected" in result.error

    def test_execute_returns_duration(self):
        op, driver, locator, resolver = make_op(GetDeviceInfoOperation)
        driver.get_device_info.return_value = {}
        result = op.execute({})
        assert result.success is True
        assert isinstance(result.duration, float)


# ════════════════════════════════════════════════════════════════
#  Variable resolution integration with operations
# ════════════════════════════════════════════════════════════════

class TestVariableResolutionWithOperations:

    def test_input_resolves_variable(self):
        op, driver, locator, resolver = make_op(InputOperation)
        resolver.set_variable("search_query", "mobile testing")
        mock_el = MagicMock()
        locator.locate.return_value = mock_el
        result = op.execute({"value": "${search_query}", "定位器": "rid=search"})
        assert result.success is True
        assert result.data["text"] == "mobile testing"

    def test_launch_app_resolves_package(self):
        op, driver, locator, resolver = make_op(LaunchAppOperation)
        resolver.set_variable("pkg", "com.resolved.app")
        result = op.execute({"package": "${pkg}"})
        assert result.success is True
        assert result.data["package"] == "com.resolved.app"

    def test_pull_file_resolves_paths(self):
        op, driver, locator, resolver = make_op(PullFileOperation)
        resolver.set_variable("rmt", "/sdcard/dynamic.txt")
        resolver.set_variable("lcl", "/tmp/dynamic.txt")
        result = op.execute({"remote": "${rmt}", "local": "${lcl}"})
        assert result.success is True
        assert result.data["remote"] == "/sdcard/dynamic.txt"
        assert result.data["local"] == "/tmp/dynamic.txt"

    def test_swipe_resolves_direction(self):
        op, driver, locator, resolver = make_op(SwipeOperation)
        resolver.set_variable("dir", "up")
        result = op.execute({"direction": "${dir}"})
        assert result.success is True
        assert result.data["direction"] == "up"
