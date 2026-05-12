"""
Tests for hui_core/render_template_obj.py
- Simple variable replacement ${var}
- Nested dict/list rendering
- Built-in function calls ${timestamp()}, ${rand_str(5)}
"""
import pytest
from hui_core.render_template_obj import (
    rend_template_str,
    rend_template_obj,
    rend_template_array,
    rend_template_any,
)
from hui_core.hui_builtins import (
    timestamp,
    rand_str,
    rand_int,
    current_time,
    b64_encode,
)


# ── rend_template_str: simple variable replacement ─────────────

class TestRendTemplateStrSimple:
    def test_simple_var_replacement(self):
        result = rend_template_str("${name}", name="Alice")
        assert result == "Alice"

    def test_multiple_vars_in_string(self):
        result = rend_template_str("Hello ${name}, age ${age}", name="Bob", age=30)
        assert result == "Hello Bob, age 30"

    def test_single_var_returns_native_type_int(self):
        result = rend_template_str("${count}", count=42)
        assert result == 42
        assert isinstance(result, int)

    def test_single_var_returns_native_type_list(self):
        data = [1, 2, 3]
        result = rend_template_str("${items}", items=data)
        assert result == [1, 2, 3]
        assert isinstance(result, list)

    def test_single_var_returns_native_type_dict(self):
        data = {"k": "v"}
        result = rend_template_str("${data}", data=data)
        assert result == {"k": "v"}
        assert isinstance(result, dict)

    def test_non_template_string_unchanged(self):
        result = rend_template_str("plain text", name="Alice")
        assert result == "plain text"

    def test_numeric_var_in_template(self):
        result = rend_template_str("score: ${score}", score=100)
        assert result == "score: 100"

    def test_none_value_replacement(self):
        result = rend_template_str("${val}", val=None)
        assert result == "None" or result is None

    def test_boolean_value_replacement(self):
        result = rend_template_str("${flag}", flag=True)
        assert result is True


# ── rend_template_str: built-in function calls ────────────────

class TestRendTemplateStrBuiltins:
    def test_timestamp_call(self):
        result = rend_template_str("${timestamp()}", timestamp=timestamp)
        assert isinstance(result, int)
        assert result > 0

    def test_rand_str_call(self):
        result = rend_template_str("${rand_str(5)}", rand_str=rand_str)
        assert isinstance(result, str)
        assert len(result) == 5

    def test_rand_int_call(self):
        result = rend_template_str("${rand_int(1, 10)}", rand_int=rand_int)
        assert isinstance(result, int)
        assert 1 <= result <= 10

    def test_current_time_call(self):
        result = rend_template_str("${current_time()}", current_time=current_time)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_b64_encode_call(self):
        result = rend_template_str("${b64_encode('hello')}", b64_encode=b64_encode)
        assert result == "aGVsbG8="

    def test_add_filter(self):
        result = rend_template_str("${value|add(1)}", value=10)
        assert result == 11

    def test_str_filter(self):
        result = rend_template_str("${value|str}", value=42)
        assert result == "42"

    def test_nested_function_with_var_arg(self):
        """Function call referencing a variable inside ${}"""
        result = rend_template_str("${b64_encode(name)}", b64_encode=b64_encode, name="hello")
        assert result == "aGVsbG8="


# ── rend_template_obj: nested dict rendering ──────────────────

class TestRendTemplateObj:
    def test_simple_dict(self):
        data = {"greeting": "Hello ${name}"}
        result = rend_template_obj(data, name="World")
        assert result["greeting"] == "Hello World"

    def test_nested_dict(self):
        data = {"user": {"name": "${name}", "age": "${age}"}}
        result = rend_template_obj(data, name="Eve", age=25)
        assert result["user"]["name"] == "Eve"
        assert result["user"]["age"] == 25

    def test_dict_with_list_value(self):
        data = {"items": ["${a}", "${b}"]}
        result = rend_template_obj(data, a="x", b="y")
        assert result["items"] == ["x", "y"]

    def test_dict_with_non_string_values_unchanged(self):
        data = {"count": 10, "active": True}
        result = rend_template_obj(data)
        assert result["count"] == 10
        assert result["active"] is True

    def test_empty_dict(self):
        result = rend_template_obj({})
        assert result == {}


# ── rend_template_array: list rendering ───────────────────────

class TestRendTemplateArray:
    def test_simple_list(self):
        data = ["${x}", "${y}", "${z}"]
        result = rend_template_array(data, x="a", y="b", z="c")
        assert result == ["a", "b", "c"]

    def test_list_with_nested_dict(self):
        data = [{"name": "${name}"}]
        result = rend_template_array(data, name="Test")
        assert result == [{"name": "Test"}]

    def test_list_with_nested_list(self):
        data = [["${a}", "${b}"]]
        result = rend_template_array(data, a="1", b="2")
        assert result == [["1", "2"]]

    def test_list_with_non_string_items(self):
        data = [1, 2.5, True]
        result = rend_template_array(data)
        assert result == [1, 2.5, True]

    def test_non_list_input_returned_as_is(self):
        result = rend_template_array("not a list")
        assert result == "not a list"


# ── rend_template_any: dispatch ───────────────────────────────

class TestRendTemplateAny:
    def test_string_dispatch(self):
        result = rend_template_any("${name}", name="Any")
        assert result == "Any"

    def test_dict_dispatch(self):
        result = rend_template_any({"key": "${val}"}, val="dict")
        assert result == {"key": "dict"}

    def test_list_dispatch(self):
        result = rend_template_any(["${val}"], val="list")
        assert result == ["list"]

    def test_other_type_returned_as_is(self):
        result = rend_template_any(42)
        assert result == 42
