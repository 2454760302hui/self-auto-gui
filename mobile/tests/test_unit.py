"""
Mobile 单元测试 — 错误体系、变量解析、配置加载验证
"""
import os
import tempfile
import pytest
from core.errors import (
    MobileError, ConfigError, LocatorError, OperationError,
    AssertFailError, DeviceError, ErrorCode,
)
from core.variable import VariableResolver
from core.config import (
    ConfigLoader, ConfigValidator,
    PlatformConfig, GlobalConfig,
    RESERVED_KEYS,
)


# ════════════════════════════════════════════════════════════════
#  Error hierarchy
# ════════════════════════════════════════════════════════════════
class TestErrors:

    def test_mobile_error_base(self):
        err = MobileError("something wrong", error_code="TEST_001", details={"k": "v"})
        assert "[TEST_001]" in str(err)
        assert err.to_dict()["error_code"] == "TEST_001"

    def test_config_error_file_not_found(self):
        err = ConfigError.file_not_found("/path/to/config.yml")
        assert "不存在" in str(err)
        assert err.error_code == ErrorCode.CONFIG_FILE_NOT_FOUND

    def test_config_error_parse_error(self):
        err = ConfigError.parse_error("/path.yml", "bad yaml")
        assert "解析失败" in str(err)

    def test_config_error_missing_required(self):
        err = ConfigError.missing_required("platform", "config")
        assert "platform" in str(err)

    def test_config_error_invalid_platform(self):
        err = ConfigError.invalid_platform("windows", ["android", "ios", "harmony"])
        assert "windows" in str(err)

    def test_locator_error_not_found(self):
        err = LocatorError.not_found("登录按钮", ["text", "id"])
        assert "登录按钮" in str(err)
        assert err.error_code == ErrorCode.LOCATOR_NOT_FOUND

    def test_locator_error_multiple_match(self):
        err = LocatorError.multiple_match("按钮", 5)
        assert "5" in str(err)

    def test_locator_error_timeout(self):
        err = LocatorError.timeout("元素", 10000)
        assert "10000" in str(err)

    def test_operation_error_failed(self):
        err = OperationError.failed("tap", "element not clickable", "按钮")
        assert "tap" in str(err)

    def test_operation_error_not_supported(self):
        err = OperationError.not_supported("fly")
        assert "fly" in str(err)

    def test_assert_fail_value_mismatch(self):
        err = AssertFailError.value_mismatch("hello", "world", "text_field")
        assert "期望值" in str(err)

    def test_assert_fail_not_visible(self):
        err = AssertFailError.element_not_visible("button")
        assert "不可见" in str(err)

    def test_assert_fail_not_exists(self):
        err = AssertFailError.element_not_exists("icon")
        assert "不存在" in str(err)

    def test_device_error_not_connected(self):
        err = DeviceError.not_connected("emulator-5554")
        assert "未连接" in str(err)

    def test_device_error_app_crash(self):
        err = DeviceError.app_crash("com.example.app")
        assert "崩溃" in str(err)

    def test_error_suggestions_in_message(self):
        err = ConfigError.file_not_found("missing.yml")
        assert "建议" in str(err) or len(err.suggestions) > 0


# ════════════════════════════════════════════════════════════════
#  VariableResolver
# ════════════════════════════════════════════════════════════════
class TestVariableResolver:

    def test_simple_variable(self):
        vr = VariableResolver(variables={"name": "Alice"})
        assert vr.resolve("${name}") == "Alice"

    def test_variable_in_string(self):
        vr = VariableResolver(variables={"name": "Bob"})
        assert vr.resolve("Hello ${name}!") == "Hello Bob!"

    def test_missing_variable_kept(self):
        vr = VariableResolver()
        assert vr.resolve("${unknown}") == "${unknown}"

    def test_int_variable_preserves_type(self):
        vr = VariableResolver(variables={"count": 42})
        result = vr.resolve("${count}")
        assert result == 42
        assert isinstance(result, int)

    def test_dict_variable_preserves_type(self):
        vr = VariableResolver(variables={"data": {"k": "v"}})
        result = vr.resolve("${data}")
        assert result == {"k": "v"}

    def test_resolve_dict(self):
        vr = VariableResolver(variables={"x": "a", "y": "b"})
        result = vr.resolve({"key1": "${x}", "key2": "${y}"})
        assert result == {"key1": "a", "key2": "b"}

    def test_resolve_list(self):
        vr = VariableResolver(variables={"a": 1, "b": 2})
        result = vr.resolve(["${a}", "${b}"])
        assert result == [1, 2]

    def test_resolve_nested(self):
        vr = VariableResolver(variables={"x": "val"})
        result = vr.resolve({"outer": {"inner": "${x}"}})
        assert result["outer"]["inner"] == "val"

    def test_non_string_passthrough(self):
        vr = VariableResolver()
        assert vr.resolve(42) == 42
        assert vr.resolve(None) is None
        assert vr.resolve(True) is True

    def test_builtin_date(self):
        vr = VariableResolver()
        result = vr.resolve("${date}")
        assert isinstance(result, str)
        assert len(result) == 10  # YYYY-MM-DD

    def test_builtin_datetime(self):
        vr = VariableResolver()
        result = vr.resolve("${datetime}")
        assert isinstance(result, str)
        assert len(result) == 19  # YYYY-MM-DD HH:MM:SS

    def test_builtin_timestamp(self):
        vr = VariableResolver()
        result = vr.resolve("${timestamp}")
        assert isinstance(result, int)
        assert result > 0

    def test_builtin_random(self):
        vr = VariableResolver()
        result = vr.resolve("${random}")
        assert isinstance(result, str)
        assert len(result) == 4

    def test_test_data_string(self):
        vr = VariableResolver(test_data={"env": "staging"})
        result = vr.resolve("@{env}")
        assert result == "staging"

    def test_test_data_list_random_choice(self):
        vr = VariableResolver(test_data={"names": ["Alice", "Bob"]})
        result = vr.resolve("@{names}")
        assert result in ["Alice", "Bob"]

    def test_set_get_variable(self):
        vr = VariableResolver()
        vr.set_variable("token", "abc123")
        assert vr.get_variable("token") == "abc123"
        assert vr.get_variable("missing", "default") == "default"

    def test_resolve_element_name_alias(self):
        vr = VariableResolver(aliases={"登录按钮": "com.app:id/login_btn"})
        assert vr.resolve_element_name("登录按钮") == "com.app:id/login_btn"
        assert vr.resolve_element_name("未定义") == "未定义"

    def test_properties(self):
        vr = VariableResolver(
            variables={"a": 1},
            test_data={"b": 2},
            aliases={"c": "d"},
        )
        assert vr.variables == {"a": 1}
        assert vr.test_data == {"b": 2}
        assert vr.aliases == {"c": "d"}


# ════════════════════════════════════════════════════════════════
#  ConfigValidator
# ════════════════════════════════════════════════════════════════
class TestConfigValidator:

    def test_valid_config(self):
        v = ConfigValidator()
        config = {
            "config": {"platform": "android", "device": "emulator-5554"},
            "登录流程": [{"点击": {"名称": "登录"}}],
        }
        assert v.validate(config) is True
        assert not v.get_errors()

    def test_invalid_platform(self):
        v = ConfigValidator()
        config = {
            "config": {"platform": "windows"},
            "流程": [{"点击": {"名称": "x"}}],
        }
        assert v.validate(config) is False
        assert any("平台" in str(e) for e in v.get_errors())

    def test_unknown_operation_warning(self):
        v = ConfigValidator()
        config = {"流程": [{"飞行": {"参数": "值"}}]}
        v.validate(config)
        assert v.get_warnings()

    def test_step_not_dict_error(self):
        v = ConfigValidator()
        config = {"流程": ["not a dict"]}
        assert v.validate(config) is False

    def test_empty_step_error(self):
        v = ConfigValidator()
        config = {"流程": [{"name": "step without operation"}]}
        assert v.validate(config) is False

    def test_no_flows_warning(self):
        v = ConfigValidator()
        config = {"config": {"platform": "android"}}
        v.validate(config)
        assert any("流程" in str(w) for w in v.get_warnings())

    def test_valid_locator(self):
        v = ConfigValidator()
        config = {
            "locators": {"按钮": {"primary": "id=btn", "fallback": ["text=按钮"]}},
            "流程": [{"点击": {"名称": "x"}}],
        }
        assert v.validate(config) is True

    def test_locator_missing_primary_warning(self):
        v = ConfigValidator()
        config = {
            "locators": {"按钮": {"fallback": ["text=按钮"]}},
            "流程": [{"点击": {"名称": "x"}}],
        }
        v.validate(config)
        assert any("primary" in str(w) for w in v.get_warnings())

    def test_validation_report(self):
        v = ConfigValidator()
        v.validate({})
        report = v.get_report()
        assert isinstance(report, str) and len(report) > 0

    def test_detect_flows_excludes_reserved(self):
        config = {
            "config": {},
            "locators": {},
            "aliases": {},
            "test_data": {},
            "登录流程": [{"点击": {"名称": "x"}}],
            "其他流程": [{"输入": {"值": "v"}}],
        }
        flows = ConfigValidator._detect_flows(config)
        assert len(flows) == 2
        assert "登录流程" in flows
        assert "config" not in flows


# ════════════════════════════════════════════════════════════════
#  ConfigLoader
# ════════════════════════════════════════════════════════════════
class TestConfigLoader:

    def test_load_from_dict(self):
        config = {"config": {"platform": "android"}, "流程": [{"点击": {"名称": "x"}}]}
        loader = ConfigLoader(config=config)
        result = loader.load()
        assert "config" in result

    def test_load_nonexistent_file(self):
        loader = ConfigLoader(config_path="/nonexistent/config.yml")
        with pytest.raises(ConfigError):
            loader.load()

    def test_load_from_yaml_file(self):
        yaml_content = """
config:
  platform: android
  device: emulator-5554
登录:
  - 启动应用:
      包名: com.example
"""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.yml', delete=False, encoding='utf-8'
        ) as f:
            f.write(yaml_content)
            f.flush()
            try:
                loader = ConfigLoader(config_path=f.name)
                config = loader.load()
                assert config["config"]["platform"] == "android"
                assert "登录" in config
            finally:
                try: os.unlink(f.name)
                except PermissionError: pass

    def test_get_flows(self):
        loader = ConfigLoader(config={
            "config": {},
            "流程A": [{"点击": {"名称": "x"}}],
            "流程B": [{"输入": {"值": "v"}}],
        })
        loader.load(validate=False)
        flows = loader.get_flows()
        assert len(flows) == 2

    def test_get_global_config(self):
        loader = ConfigLoader(config={"config": {"platform": "ios", "device": "iPhone"}})
        loader.load(validate=False)
        gc = loader.get_global_config()
        assert isinstance(gc, GlobalConfig)
        assert gc.platform.platform == "ios"

    def test_get_locators(self):
        loader = ConfigLoader(config={
            "locators": {"按钮": {"primary": "id=btn"}},
        })
        loader.load(validate=False)
        locs = loader.get_locators()
        assert "按钮" in locs

    def test_get_aliases(self):
        loader = ConfigLoader(config={"aliases": {"别名": "真名"}})
        loader.load(validate=False)
        assert loader.get_aliases()["别名"] == "真名"

    def test_get_test_data(self):
        loader = ConfigLoader(config={"test_data": {"user": "admin"}})
        loader.load(validate=False)
        assert loader.get_test_data()["user"] == "admin"

    def test_no_config_or_path_raises(self):
        loader = ConfigLoader()
        with pytest.raises(ConfigError):
            loader.load()

    def test_validate_returns_bool(self):
        loader = ConfigLoader(config={"config": {"platform": "android"}, "流程": [{"点击": {"名称": "x"}}]})
        assert loader.validate() is True


# ════════════════════════════════════════════════════════════════
#  Pydantic models
# ════════════════════════════════════════════════════════════════
class TestPydanticModels:

    def test_platform_config_defaults(self):
        pc = PlatformConfig()
        assert pc.platform == "android"
        assert pc.device == ""

    def test_global_config_defaults(self):
        gc = GlobalConfig()
        assert gc.platform.platform == "android"
        assert gc.retry.max_count == 3
        assert gc.wait.timeout == 10000

    def test_platform_config_custom(self):
        pc = PlatformConfig(platform="ios", device="iPhone 15")
        assert pc.platform == "ios"
