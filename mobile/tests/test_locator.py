"""
Locator 单元测试 — 测试所有定位策略和 SmartLocator
"""
import os
import sys
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.locator import (
    SmartLocator,
    LocatorStrategy,
    ResourceIDStrategy,
    AccessibilityIDStrategy,
    TextStrategy,
    TextContainsStrategy,
    DescriptionStrategy,
    ClassNameStrategy,
    XPathStrategy,
    PredicateStrategy,
    ClassChainStrategy,
    CoordinateStrategy,
    ImageStrategy,
)


def make_mock_driver():
    """创建 mock 驱动"""
    driver = MagicMock()
    driver.supported_strategies = [
        "resource_id", "accessibility_id", "text", "description",
        "class_name", "xpath", "predicate", "class_chain",
    ]
    return driver


# ════════════════════════════════════════════════════════════════
#  ResourceIDStrategy
# ════════════════════════════════════════════════════════════════

class TestResourceIDStrategy:

    def test_can_handle_rid_prefix(self):
        s = ResourceIDStrategy()
        assert s.can_handle("rid=com.app:id/btn") is True

    def test_cannot_handle_other_prefix(self):
        s = ResourceIDStrategy()
        assert s.can_handle("text=Login") is False
        assert s.can_handle("aid=btn") is False
        assert s.can_handle("rid") is False

    def test_name_and_priority(self):
        s = ResourceIDStrategy()
        assert s.name == "resource_id"
        assert s.priority == 5

    def test_locate_extracts_resource_id(self):
        s = ResourceIDStrategy()
        driver = make_mock_driver()
        driver.find_element.return_value = MagicMock()
        result = s.locate(driver, "rid=com.app:id/login")
        driver.find_element.assert_called_once_with(
            {"type": "resource_id", "value": "com.app:id/login"}
        )
        assert result is not None

    def test_locate_returns_none_on_miss(self):
        s = ResourceIDStrategy()
        driver = make_mock_driver()
        driver.find_element.return_value = None
        result = s.locate(driver, "rid=com.app:id/missing")
        assert result is None


# ════════════════════════════════════════════════════════════════
#  AccessibilityIDStrategy
# ════════════════════════════════════════════════════════════════

class TestAccessibilityIDStrategy:

    def test_can_handle_aid_prefix(self):
        s = AccessibilityIDStrategy()
        assert s.can_handle("aid=login_btn") is True

    def test_cannot_handle_others(self):
        s = AccessibilityIDStrategy()
        assert s.can_handle("rid=x") is False
        assert s.can_handle("aid") is False

    def test_name_and_priority(self):
        s = AccessibilityIDStrategy()
        assert s.name == "accessibility_id"
        assert s.priority == 10

    def test_locate_extracts_aid(self):
        s = AccessibilityIDStrategy()
        driver = make_mock_driver()
        driver.find_element.return_value = MagicMock()
        result = s.locate(driver, "aid=submit")
        driver.find_element.assert_called_once_with(
            {"type": "accessibility_id", "value": "submit"}
        )


# ════════════════════════════════════════════════════════════════
#  TextStrategy
# ════════════════════════════════════════════════════════════════

class TestTextStrategy:

    def test_can_handle_text_prefix(self):
        s = TextStrategy()
        assert s.can_handle("text=Login") is True

    def test_cannot_handle_textcontains(self):
        s = TextStrategy()
        assert s.can_handle("textContains=Log") is False

    def test_name_and_priority(self):
        s = TextStrategy()
        assert s.name == "text"
        assert s.priority == 15

    def test_locate_extracts_text(self):
        s = TextStrategy()
        driver = make_mock_driver()
        driver.find_element.return_value = MagicMock()
        result = s.locate(driver, "text=Settings")
        driver.find_element.assert_called_once_with(
            {"type": "text", "value": "Settings"}
        )


# ════════════════════════════════════════════════════════════════
#  TextContainsStrategy
# ════════════════════════════════════════════════════════════════

class TestTextContainsStrategy:

    def test_can_handle_textcontains_prefix(self):
        s = TextContainsStrategy()
        assert s.can_handle("textContains=Log") is True

    def test_cannot_handle_text_prefix(self):
        s = TextContainsStrategy()
        assert s.can_handle("text=Login") is False

    def test_name_and_priority(self):
        s = TextContainsStrategy()
        assert s.name == "textContains"
        assert s.priority == 16

    def test_locate_extracts_text(self):
        s = TextContainsStrategy()
        driver = make_mock_driver()
        driver.find_element.return_value = MagicMock()
        result = s.locate(driver, "textContains=Sett")
        driver.find_element.assert_called_once_with(
            {"type": "text", "value": "Sett"}
        )


# ════════════════════════════════════════════════════════════════
#  DescriptionStrategy
# ════════════════════════════════════════════════════════════════

class TestDescriptionStrategy:

    def test_can_handle_desc_prefix(self):
        s = DescriptionStrategy()
        assert s.can_handle("desc=Submit button") is True

    def test_cannot_handle_others(self):
        s = DescriptionStrategy()
        assert s.can_handle("text=Submit") is False

    def test_name_and_priority(self):
        s = DescriptionStrategy()
        assert s.name == "description"
        assert s.priority == 20

    def test_locate_extracts_desc(self):
        s = DescriptionStrategy()
        driver = make_mock_driver()
        driver.find_element.return_value = MagicMock()
        result = s.locate(driver, "desc=Close")
        driver.find_element.assert_called_once_with(
            {"type": "description", "value": "Close"}
        )


# ════════════════════════════════════════════════════════════════
#  ClassNameStrategy
# ════════════════════════════════════════════════════════════════

class TestClassNameStrategy:

    def test_can_handle_classname_prefix(self):
        s = ClassNameStrategy()
        assert s.can_handle("className=android.widget.Button") is True

    def test_cannot_handle_others(self):
        s = ClassNameStrategy()
        assert s.can_handle("rid=x") is False

    def test_name_and_priority(self):
        s = ClassNameStrategy()
        assert s.name == "class_name"
        assert s.priority == 25

    def test_locate_extracts_class(self):
        s = ClassNameStrategy()
        driver = make_mock_driver()
        driver.find_element.return_value = MagicMock()
        result = s.locate(driver, "className=android.widget.EditText")
        driver.find_element.assert_called_once_with(
            {"type": "class_name", "value": "android.widget.EditText"}
        )


# ════════════════════════════════════════════════════════════════
#  XPathStrategy
# ════════════════════════════════════════════════════════════════

class TestXPathStrategy:

    def test_can_handle_xpath_prefix(self):
        s = XPathStrategy()
        assert s.can_handle("xpath=//android.widget.Button") is True

    def test_cannot_handle_others(self):
        s = XPathStrategy()
        assert s.can_handle("text=x") is False

    def test_name_and_priority(self):
        s = XPathStrategy()
        assert s.name == "xpath"
        assert s.priority == 30

    def test_locate_extracts_xpath(self):
        s = XPathStrategy()
        driver = make_mock_driver()
        driver.find_element.return_value = MagicMock()
        result = s.locate(driver, "xpath=//Button[@text='OK']")
        driver.find_element.assert_called_once_with(
            {"type": "xpath", "value": "//Button[@text='OK']"}
        )


# ════════════════════════════════════════════════════════════════
#  PredicateStrategy
# ════════════════════════════════════════════════════════════════

class TestPredicateStrategy:

    def test_can_handle_predicate_prefix(self):
        s = PredicateStrategy()
        assert s.can_handle("predicate=label == 'OK'") is True

    def test_cannot_handle_others(self):
        s = PredicateStrategy()
        assert s.can_handle("xpath=x") is False

    def test_name_and_priority(self):
        s = PredicateStrategy()
        assert s.name == "predicate"
        assert s.priority == 35

    def test_locate_extracts_predicate(self):
        s = PredicateStrategy()
        driver = make_mock_driver()
        driver.find_element.return_value = MagicMock()
        result = s.locate(driver, "predicate=name == 'login'")
        driver.find_element.assert_called_once_with(
            {"type": "predicate", "value": "name == 'login'"}
        )


# ════════════════════════════════════════════════════════════════
#  ClassChainStrategy
# ════════════════════════════════════════════════════════════════

class TestClassChainStrategy:

    def test_can_handle_classchain_prefix(self):
        s = ClassChainStrategy()
        assert s.can_handle("classChain=**/Button") is True

    def test_cannot_handle_others(self):
        s = ClassChainStrategy()
        assert s.can_handle("predicate=x") is False

    def test_name_and_priority(self):
        s = ClassChainStrategy()
        assert s.name == "class_chain"
        assert s.priority == 36

    def test_locate_extracts_chain(self):
        s = ClassChainStrategy()
        driver = make_mock_driver()
        driver.find_element.return_value = MagicMock()
        result = s.locate(driver, "classChain=**/XCUIElementTypeButton")
        driver.find_element.assert_called_once_with(
            {"type": "class_chain", "value": "**/XCUIElementTypeButton"}
        )


# ════════════════════════════════════════════════════════════════
#  CoordinateStrategy
# ════════════════════════════════════════════════════════════════

class TestCoordinateStrategy:

    def test_can_handle_coord_prefix(self):
        s = CoordinateStrategy()
        assert s.can_handle("coord=100,200") is True

    def test_cannot_handle_others(self):
        s = CoordinateStrategy()
        assert s.can_handle("rid=x") is False

    def test_name_and_priority(self):
        s = CoordinateStrategy()
        assert s.name == "coordinate"
        assert s.priority == 40

    def test_locate_extracts_coordinates(self):
        s = CoordinateStrategy()
        driver = make_mock_driver()
        result = s.locate(driver, "coord=100,200")
        assert result == {"type": "coordinate", "x": 100, "y": 200}

    def test_locate_with_spaces(self):
        s = CoordinateStrategy()
        driver = make_mock_driver()
        result = s.locate(driver, "coord= 50 , 75 ")
        assert result == {"type": "coordinate", "x": 50, "y": 75}

    def test_locate_invalid_coord_returns_none(self):
        s = CoordinateStrategy()
        driver = make_mock_driver()
        result = s.locate(driver, "coord=abc,def")
        assert result is None

    def test_locate_missing_y_returns_none(self):
        s = CoordinateStrategy()
        driver = make_mock_driver()
        result = s.locate(driver, "coord=100")
        assert result is None


# ════════════════════════════════════════════════════════════════
#  ImageStrategy
# ════════════════════════════════════════════════════════════════

class TestImageStrategy:

    def test_can_handle_image_prefix(self):
        s = ImageStrategy()
        assert s.can_handle("image=/path/to/template.png") is True

    def test_cannot_handle_others(self):
        s = ImageStrategy()
        assert s.can_handle("coord=10,20") is False

    def test_name_and_priority(self):
        s = ImageStrategy()
        assert s.name == "image"
        assert s.priority == 50

    def test_locate_nonexistent_file_returns_none(self):
        s = ImageStrategy()
        driver = make_mock_driver()
        result = s.locate(driver, "image=/nonexistent/template.png")
        assert result is None


# ════════════════════════════════════════════════════════════════
#  Strategy priority sorting
# ════════════════════════════════════════════════════════════════

class TestStrategyPriority:

    def test_priorities_are_ordered(self):
        strategies = [
            ResourceIDStrategy(),
            AccessibilityIDStrategy(),
            TextStrategy(),
            TextContainsStrategy(),
            DescriptionStrategy(),
            ClassNameStrategy(),
            XPathStrategy(),
            PredicateStrategy(),
            ClassChainStrategy(),
            CoordinateStrategy(),
            ImageStrategy(),
        ]
        strategies.sort(key=lambda s: s.priority)
        priorities = [s.priority for s in strategies]
        assert priorities == sorted(priorities)

    def test_resource_id_highest_priority(self):
        """resource_id should have the lowest priority number (highest priority)"""
        all_strategies = [
            ResourceIDStrategy(), AccessibilityIDStrategy(), TextStrategy(),
            TextContainsStrategy(), DescriptionStrategy(), ClassNameStrategy(),
            XPathStrategy(), PredicateStrategy(), ClassChainStrategy(),
            CoordinateStrategy(), ImageStrategy(),
        ]
        min_priority = min(s.priority for s in all_strategies)
        assert min_priority == ResourceIDStrategy().priority


# ════════════════════════════════════════════════════════════════
#  SmartLocator
# ════════════════════════════════════════════════════════════════

class TestSmartLocator:

    def _make_locator(self):
        driver = make_mock_driver()
        locator = SmartLocator(driver)
        return locator, driver

    def test_init_registers_default_strategies(self):
        locator, _ = self._make_locator()
        # Should have strategies registered
        assert len(locator._strategies) > 0

    def test_strategies_sorted_by_priority(self):
        locator, _ = self._make_locator()
        priorities = [s.priority for s in locator._strategies]
        assert priorities == sorted(priorities)

    def test_register_custom_strategy(self):
        locator, _ = self._make_locator()
        initial_count = len(locator._strategies)

        class CustomStrategy(LocatorStrategy):
            name = "custom"
            priority = 1

            def can_handle(self, locator_str):
                return locator_str.startswith("custom=")

            def locate(self, driver, value):
                return {"custom": True}

        locator.register_strategy(CustomStrategy())
        assert len(locator._strategies) == initial_count + 1
        # Should still be sorted
        priorities = [s.priority for s in locator._strategies]
        assert priorities == sorted(priorities)

    def test_locate_with_locator_string(self):
        locator, driver = self._make_locator()
        mock_el = MagicMock()
        driver.find_element.return_value = mock_el
        result = locator.locate({"定位器": "rid=com.app:id/btn"})
        assert result is not None
        driver.find_element.assert_called()

    def test_locate_with_locator_english_key(self):
        locator, driver = self._make_locator()
        mock_el = MagicMock()
        driver.find_element.return_value = mock_el
        result = locator.locate({"locator": "rid=com.app:id/btn"})
        assert result is not None

    def test_locate_from_library_string(self):
        locator, driver = self._make_locator()
        mock_el = MagicMock()
        driver.find_element.return_value = mock_el
        locator.set_locators({"login_btn": "rid=com.app:id/login"})
        result = locator.locate({"元素": "login_btn"})
        assert result is not None

    def test_locate_from_library_dict_primary(self):
        locator, driver = self._make_locator()
        mock_el = MagicMock()
        driver.find_element.return_value = mock_el
        locator.set_locators({"btn": {"primary": "rid=com.app:id/btn", "fallback": ["text=OK"]}})
        result = locator.locate({"元素": "btn"})
        assert result is not None

    def test_locate_from_library_dict_fallback(self):
        locator, driver = self._make_locator()
        # Primary returns None, fallback succeeds
        call_count = [0]
        def mock_find(config):
            call_count[0] += 1
            if config.get("value") == "com.app:id/missing":
                return None
            return MagicMock()
        driver.find_element.side_effect = mock_find
        locator.set_locators({"btn": {"primary": "rid=com.app:id/missing", "fallback": ["text=OK"]}})
        result = locator.locate({"元素": "btn"})
        assert result is not None
        assert call_count[0] >= 2

    def test_locate_from_library_element_english_key(self):
        locator, driver = self._make_locator()
        mock_el = MagicMock()
        driver.find_element.return_value = mock_el
        locator.set_locators({"btn": "rid=com.app:id/btn"})
        result = locator.locate({"element": "btn"})
        assert result is not None

    def test_locate_by_name_text(self):
        locator, driver = self._make_locator()
        mock_el = MagicMock()
        driver.find_element.return_value = mock_el
        result = locator.locate({"名称": "Login"})
        assert result is not None

    def test_locate_by_name_english_key(self):
        locator, driver = self._make_locator()
        mock_el = MagicMock()
        driver.find_element.return_value = mock_el
        result = locator.locate({"name": "Login"})
        assert result is not None

    def test_locate_by_name_fallback_to_description(self):
        locator, driver = self._make_locator()
        call_count = [0]
        def mock_find(config):
            call_count[0] += 1
            if config.get("type") == "text":
                return None
            if config.get("type") == "description":
                return MagicMock()
            return None
        driver.find_element.side_effect = mock_find
        result = locator.locate({"名称": "Submit"})
        assert result is not None
        assert call_count[0] >= 2

    def test_locate_by_name_fallback_to_accessibility_id(self):
        locator, driver = self._make_locator()
        def mock_find(config):
            if config.get("type") in ("text", "description"):
                return None
            if config.get("type") == "accessibility_id":
                return MagicMock()
            return None
        driver.find_element.side_effect = mock_find
        result = locator.locate({"名称": "Icon"})
        assert result is not None

    def test_locate_returns_none_when_all_fail(self):
        locator, driver = self._make_locator()
        driver.find_element.return_value = None
        result = locator.locate({"名称": "Nothing"})
        assert result is None

    def test_locate_with_aliases(self):
        locator, driver = self._make_locator()
        mock_el = MagicMock()
        driver.find_element.return_value = mock_el
        locator.set_aliases({"Login Button": "login_btn"})
        locator.set_locators({"login_btn": "rid=com.app:id/login"})
        result = locator.locate({"元素": "Login Button"})
        assert result is not None

    def test_locate_empty_config_returns_none(self):
        locator, driver = self._make_locator()
        result = locator.locate({})
        assert result is None

    def test_locate_strategy_exception_continues(self):
        """When a strategy throws, the locator continues to try next strategies"""
        locator, driver = self._make_locator()
        # rid strategy's find_element will raise first, then succeed on text
        def mock_find(config):
            t = config.get("type", "")
            if t == "resource_id":
                raise RuntimeError("strategy error")
            return MagicMock()
        driver.find_element.side_effect = mock_find
        # Use a name-based locator which tries multiple strategies
        result = locator.locate({"名称": "Login"})
        # text strategy should succeed
        assert result is not None

    def test_coordinate_strategy_always_registered(self):
        """Coordinate and image strategies should always be registered"""
        driver = make_mock_driver()
        driver.supported_strategies = []  # No strategies supported
        locator = SmartLocator(driver)
        strategy_names = [s.name for s in locator._strategies]
        assert "coordinate" in strategy_names
        assert "image" in strategy_names

    def test_set_locators(self):
        locator, _ = self._make_locator()
        locs = {"btn": "rid=com.app:id/btn", "input": "rid=com.app:id/input"}
        locator.set_locators(locs)
        assert locator._locators == locs

    def test_set_aliases(self):
        locator, _ = self._make_locator()
        aliases = {"登录": "login_btn", "搜索": "search_field"}
        locator.set_aliases(aliases)
        assert locator._aliases == aliases

    def test_locate_priority_order(self):
        """定位器字符串 should be checked before library lookup"""
        locator, driver = self._make_locator()
        mock_el = MagicMock()
        driver.find_element.return_value = mock_el
        locator.set_locators({"btn": "rid=com.app:id/library_btn"})
        # Both locator string and element are provided; locator string wins
        result = locator.locate({"定位器": "rid=com.app:id/direct", "元素": "btn"})
        assert result is not None
        # Verify it was the direct locator that found it
        call_args = driver.find_element.call_args_list
        first_call = call_args[0]
        assert first_call[0][0]["value"] == "com.app:id/direct"
