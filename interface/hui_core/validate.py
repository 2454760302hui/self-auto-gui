"""
Built-in validate comparators.
"""
import re
from .log import log


# ── 基础比较 ──────────────────────────────────────────────────

def equals(check_value, expect_value):
    check_value = None if check_value == 'None' else check_value
    expect_value = None if expect_value == 'None' else expect_value
    assert check_value == expect_value, \
        f'{check_value!r} ({type(check_value).__name__}) == {expect_value!r} ({type(expect_value).__name__})'


def less_than(check_value, expect_value):
    assert check_value < expect_value, f'{check_value} < {expect_value}'


def less_than_or_equals(check_value, expect_value):
    assert check_value <= expect_value, f'{check_value} <= {expect_value}'


def greater_than(check_value, expect_value):
    assert check_value > expect_value, f'{check_value} > {expect_value}'


def greater_than_or_equals(check_value, expect_value):
    assert check_value >= expect_value, f'{check_value} >= {expect_value}'


def not_equals(check_value, expect_value):
    assert check_value != expect_value, f'{check_value} != {expect_value}'


def string_equals(check_value, expect_value):
    assert str(check_value) == str(expect_value), f'{check_value} == {expect_value}'


# ── 长度断言 ──────────────────────────────────────────────────

def length_equals(check_value, expect_value):
    expect_len = _cast_to_int(expect_value)
    actual_len = len(str(check_value)) if isinstance(check_value, (int, float)) else len(check_value)
    assert actual_len == expect_len, f'len({check_value!r}) == {expect_len}'


def length_greater_than(check_value, expect_value):
    assert len(check_value) > _cast_to_int(expect_value), \
        f'len({check_value!r}) > {expect_value}'


def length_greater_than_or_equals(check_value, expect_value):
    assert len(check_value) >= _cast_to_int(expect_value), \
        f'len({check_value!r}) >= {expect_value}'


def length_less_than(check_value, expect_value):
    assert len(check_value) < _cast_to_int(expect_value), \
        f'len({check_value!r}) < {expect_value}'


def length_less_than_or_equals(check_value, expect_value):
    assert len(check_value) <= _cast_to_int(expect_value), \
        f'len({check_value!r}) <= {expect_value}'


# ── 包含断言 ──────────────────────────────────────────────────

def contains(check_value, expect_value):
    if isinstance(check_value, (list, tuple, dict, str)):
        assert expect_value in check_value, f'{expect_value!r} in {check_value!r}'
    else:
        assert expect_value in str(check_value), f'{expect_value!r} in {check_value!r}'


def not_contains(check_value, expect_value):
    """断言 check_value 不包含 expect_value"""
    if isinstance(check_value, (list, tuple, dict, str)):
        assert expect_value not in check_value, \
            f'{expect_value!r} not in {check_value!r}'
    else:
        assert expect_value not in str(check_value), \
            f'{expect_value!r} not in {check_value!r}'


def contained_by(check_value, expect_value):
    if isinstance(expect_value, (list, tuple, dict, str)):
        assert check_value in expect_value, f'{check_value!r} in {expect_value!r}'
    else:
        assert str(check_value) in expect_value, f'{check_value!r} in {expect_value!r}'


# ── 正则 / 字符串 ─────────────────────────────────────────────

def regex_match(check_value, expect_value):
    assert isinstance(expect_value, str)
    assert isinstance(check_value, str)
    assert re.match(expect_value, check_value), \
        f'{check_value!r} 不匹配正则 {expect_value!r}'


def startswith(check_value, expect_value):
    assert str(check_value).startswith(str(expect_value)), \
        f'{check_value!r} startswith {expect_value!r}'


def endswith(check_value, expect_value):
    assert str(check_value).endswith(str(expect_value)), \
        f'{check_value!r} endswith {expect_value!r}'


# ── 布尔 ──────────────────────────────────────────────────────

def bool_equals(check_value, expect_value):
    assert bool(check_value) == bool(expect_value), \
        f'{check_value} -> {bool(check_value)} == {expect_value}'


# ── 响应时间断言 ──────────────────────────────────────────────

def response_time_less_than(elapsed_ms, expect_ms):
    """响应时间（毫秒）小于预期值
    yml 用法:
        validate:
          - response_time_lt: [elapsed, 2000]
    """
    elapsed_ms = _cast_to_float(elapsed_ms)
    expect_ms = _cast_to_float(expect_ms)
    assert elapsed_ms < expect_ms, \
        f'响应时间 {elapsed_ms:.0f}ms 超出预期 {expect_ms:.0f}ms'


def response_time_less_than_or_equals(elapsed_ms, expect_ms):
    elapsed_ms = _cast_to_float(elapsed_ms)
    expect_ms = _cast_to_float(expect_ms)
    assert elapsed_ms <= expect_ms, \
        f'响应时间 {elapsed_ms:.0f}ms 超出预期 {expect_ms:.0f}ms'


# ── JSON Schema 校验 ──────────────────────────────────────────

def json_schema(check_value, schema):
    """JSON Schema 结构校验
    yml 用法:
        validate:
          - json_schema:
              - body
              - type: object
                required: [code, data]
                properties:
                  code: {type: integer}
    """
    try:
        import jsonschema  # noqa
    except ImportError:
        log.error("json_schema 校验需要安装 jsonschema: pip install jsonschema")
        return
    try:
        jsonschema.validate(instance=check_value, schema=schema)
        log.info(f"json_schema 校验通过")
    except jsonschema.ValidationError as e:
        raise AssertionError(f"JSON Schema 校验失败: {e.message}") from None


# ── 内部工具 ──────────────────────────────────────────────────

def _cast_to_int(expect_value):
    try:
        return int(expect_value)
    except Exception:
        raise AssertionError(f"{expect_value!r} 无法转换为 int")


def _cast_to_float(value):
    try:
        return float(value)
    except Exception:
        raise AssertionError(f"{value!r} 无法转换为 float")
