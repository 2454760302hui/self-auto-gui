"""
OperationRegistry 单元测试 — 测试注册、查找、单例行为
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from operations.registry import OperationRegistry, operation


# ════════════════════════════════════════════════════════════════
#  Setup / Teardown — 清理全局注册表状态
# ════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def clean_registry():
    """每个测试前后清理注册表"""
    # 保存当前状态
    saved = dict(OperationRegistry._operations)
    OperationRegistry._operations.clear()
    yield
    # 恢复
    OperationRegistry._operations.clear()
    OperationRegistry._operations.update(saved)


# ════════════════════════════════════════════════════════════════
#  Singleton behavior
# ════════════════════════════════════════════════════════════════

class TestSingleton:

    def test_same_instance(self):
        r1 = OperationRegistry()
        r2 = OperationRegistry()
        assert r1 is r2

    def test_instance_type(self):
        r = OperationRegistry()
        assert isinstance(r, OperationRegistry)


# ════════════════════════════════════════════════════════════════
#  register() decorator
# ════════════════════════════════════════════════════════════════

class TestRegister:

    def test_register_single_name(self):
        @OperationRegistry.register("test_op")
        class FakeOp:
            pass

        assert OperationRegistry.get_handler("test_op") is FakeOp

    def test_register_multiple_names(self):
        @OperationRegistry.register("点击", "tap")
        class FakeTap:
            pass

        assert OperationRegistry.get_handler("点击") is FakeTap
        assert OperationRegistry.get_handler("tap") is FakeTap

    def test_register_chinese_name(self):
        @OperationRegistry.register("输入文本")
        class FakeInput:
            pass

        assert OperationRegistry.get_handler("输入文本") is FakeInput

    def test_register_returns_class(self):
        """装饰器应返回原类"""
        @OperationRegistry.register("some_op")
        class FakeOp:
            pass

        assert FakeOp.__name__ == "FakeOp"

    def test_register_overwrites_existing(self):
        @OperationRegistry.register("dup")
        class FirstOp:
            pass

        @OperationRegistry.register("dup")
        class SecondOp:
            pass

        assert OperationRegistry.get_handler("dup") is SecondOp

    def test_register_three_names(self):
        @OperationRegistry.register("断言", "assert", "验证")
        class FakeAssert:
            pass

        assert OperationRegistry.get_handler("断言") is FakeAssert
        assert OperationRegistry.get_handler("assert") is FakeAssert
        assert OperationRegistry.get_handler("验证") is FakeAssert


# ════════════════════════════════════════════════════════════════
#  operation() shortcut decorator
# ════════════════════════════════════════════════════════════════

class TestOperationShortcut:

    def test_operation_decorator(self):
        @operation("shortcut_op")
        class FakeShortcut:
            pass

        assert OperationRegistry.get_handler("shortcut_op") is FakeShortcut

    def test_operation_multi_names(self):
        @operation("en_op", "zh_op")
        class FakeMulti:
            pass

        assert OperationRegistry.get_handler("en_op") is FakeMulti
        assert OperationRegistry.get_handler("zh_op") is FakeMulti


# ════════════════════════════════════════════════════════════════
#  get_handler()
# ════════════════════════════════════════════════════════════════

class TestGetHandler:

    def test_get_handler_returns_none_for_unknown(self):
        result = OperationRegistry.get_handler("nonexistent")
        assert result is None

    def test_get_handler_returns_registered_class(self):
        @OperationRegistry.register("my_op")
        class MyOp:
            pass

        assert OperationRegistry.get_handler("my_op") is MyOp

    def test_get_handler_case_sensitive(self):
        @OperationRegistry.register("Tap")
        class TapOp:
            pass

        assert OperationRegistry.get_handler("Tap") is TapOp
        assert OperationRegistry.get_handler("tap") is None


# ════════════════════════════════════════════════════════════════
#  has_operation()
# ════════════════════════════════════════════════════════════════

class TestHasOperation:

    def test_has_operation_false(self):
        assert OperationRegistry.has_operation("missing") is False

    def test_has_operation_true(self):
        @OperationRegistry.register("existing")
        class ExistingOp:
            pass

        assert OperationRegistry.has_operation("existing") is True

    def test_has_operation_after_clear(self):
        @OperationRegistry.register("temp_op")
        class TempOp:
            pass

        assert OperationRegistry.has_operation("temp_op") is True
        OperationRegistry.clear()
        assert OperationRegistry.has_operation("temp_op") is False


# ════════════════════════════════════════════════════════════════
#  get_operation_names()
# ════════════════════════════════════════════════════════════════

class TestGetOperationNames:

    def test_empty_registry(self):
        assert OperationRegistry.get_operation_names() == set()

    def test_returns_set(self):
        result = OperationRegistry.get_operation_names()
        assert isinstance(result, set)

    def test_single_registration(self):
        @OperationRegistry.register("op1")
        class Op1:
            pass

        assert OperationRegistry.get_operation_names() == {"op1"}

    def test_multiple_names_in_set(self):
        @OperationRegistry.register("op_a", "op_b")
        class OpAB:
            pass

        assert OperationRegistry.get_operation_names() == {"op_a", "op_b"}

    def test_multiple_registrations(self):
        @OperationRegistry.register("op1")
        class Op1:
            pass

        @OperationRegistry.register("op2")
        class Op2:
            pass

        names = OperationRegistry.get_operation_names()
        assert names == {"op1", "op2"}


# ════════════════════════════════════════════════════════════════
#  clear()
# ════════════════════════════════════════════════════════════════

class TestClear:

    def test_clear_empties_registry(self):
        @OperationRegistry.register("clearable")
        class ClearableOp:
            pass

        assert OperationRegistry.has_operation("clearable") is True
        OperationRegistry.clear()
        assert OperationRegistry.has_operation("clearable") is False
        assert OperationRegistry.get_operation_names() == set()

    def test_clear_on_already_empty(self):
        OperationRegistry.clear()
        assert OperationRegistry.get_operation_names() == set()

    def test_clear_allows_reregistration(self):
        @OperationRegistry.register("reg")
        class Reg1:
            pass

        OperationRegistry.clear()

        @OperationRegistry.register("reg")
        class Reg2:
            pass

        assert OperationRegistry.get_handler("reg") is Reg2


# ════════════════════════════════════════════════════════════════
#  Integration: import all operations and verify registration
# ════════════════════════════════════════════════════════════════

class TestRegisteredOperations:

    def test_all_operations_registered(self):
        """Verify operations get registered when decorators execute"""
        # The autouse fixture clears, but re-importing triggers @operation decorators
        import importlib
        import operations.tap as m1
        importlib.reload(m1)
        import operations.input as m2
        importlib.reload(m2)
        import operations.wait as m3
        importlib.reload(m3)
        names = OperationRegistry.get_operation_names()
        assert len(names) >= 6  # at least 3 operations with CN+EN names each

    def test_registered_handler_types(self):
        """Verify handlers are proper classes"""
        import importlib
        import operations as ops_module
        importlib.reload(ops_module)

        from operations.base import OperationBase

        for name in OperationRegistry.get_operation_names():
            handler = OperationRegistry.get_handler(name)
            assert isinstance(handler, type), f"'{name}' handler is not a class"
            assert issubclass(handler, OperationBase), f"'{name}' is not an OperationBase subclass"
