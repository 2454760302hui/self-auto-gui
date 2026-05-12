"""
Tests for hui_core/validate.py
- eq, ne, gt, lt, ge, le comparators
- contains, not_contains
- regex_match
- len_eq, len_gt, len_lt
- type_check (str, int, list, dict) via equals
- response_time validator
"""
import pytest
from hui_core.validate import (
    equals,
    not_equals,
    greater_than,
    greater_than_or_equals,
    less_than,
    less_than_or_equals,
    string_equals,
    length_equals,
    length_greater_than,
    length_greater_than_or_equals,
    length_less_than,
    length_less_than_or_equals,
    contains,
    not_contains,
    contained_by,
    regex_match,
    startswith,
    endswith,
    bool_equals,
    response_time_less_than,
    response_time_less_than_or_equals,
)


# ── equals / not_equals ──────────────────────────────────────

class TestEquals:
    def test_equal_integers(self):
        equals(1, 1)

    def test_equal_strings(self):
        equals("hello", "hello")

    def test_equal_none(self):
        equals(None, None)

    def test_equal_none_string(self):
        """'None' string is treated as None"""
        equals('None', 'None')

    def test_equal_dicts(self):
        equals({"a": 1}, {"a": 1})

    def test_unequal_raises(self):
        with pytest.raises(AssertionError):
            equals(1, 2)

    def test_unequal_types_raises(self):
        with pytest.raises(AssertionError):
            equals(1, "1")


class TestNotEquals:
    def test_not_equal_values(self):
        not_equals(1, 2)

    def test_not_equal_strings(self):
        not_equals("a", "b")

    def test_equal_values_raises(self):
        with pytest.raises(AssertionError):
            not_equals(5, 5)


class TestStringEquals:
    def test_same_strings(self):
        string_equals("abc", "abc")

    def test_int_to_string(self):
        string_equals(42, "42")

    def test_different_strings_raises(self):
        with pytest.raises(AssertionError):
            string_equals("abc", "def")


# ── gt, ge, lt, le ──────────────────────────────────────────

class TestGreaterThan:
    def test_gt_true(self):
        greater_than(5, 3)

    def test_gt_equal_raises(self):
        with pytest.raises(AssertionError):
            greater_than(3, 3)

    def test_gt_less_raises(self):
        with pytest.raises(AssertionError):
            greater_than(1, 5)


class TestGreaterThanOrEquals:
    def test_ge_greater(self):
        greater_than_or_equals(5, 3)

    def test_ge_equal(self):
        greater_than_or_equals(3, 3)

    def test_ge_less_raises(self):
        with pytest.raises(AssertionError):
            greater_than_or_equals(2, 3)


class TestLessThan:
    def test_lt_true(self):
        less_than(1, 5)

    def test_lt_equal_raises(self):
        with pytest.raises(AssertionError):
            less_than(3, 3)

    def test_lt_greater_raises(self):
        with pytest.raises(AssertionError):
            less_than(5, 1)


class TestLessThanOrEquals:
    def test_le_less(self):
        less_than_or_equals(1, 5)

    def test_le_equal(self):
        less_than_or_equals(3, 3)

    def test_le_greater_raises(self):
        with pytest.raises(AssertionError):
            less_than_or_equals(5, 3)


# ── contains / not_contains ─────────────────────────────────

class TestContains:
    def test_string_contains(self):
        contains("hello world", "world")

    def test_list_contains(self):
        contains([1, 2, 3], 2)

    def test_dict_contains_key(self):
        contains({"a": 1}, "a")

    def test_tuple_contains(self):
        contains((1, 2, 3), 2)

    def test_missing_raises(self):
        with pytest.raises(AssertionError):
            contains("hello", "xyz")

    def test_list_missing_raises(self):
        with pytest.raises(AssertionError):
            contains([1, 2], 5)


class TestNotContains:
    def test_string_not_contains(self):
        not_contains("hello", "xyz")

    def test_list_not_contains(self):
        not_contains([1, 2, 3], 5)

    def test_present_raises(self):
        with pytest.raises(AssertionError):
            not_contains("hello", "ell")


class TestContainedBy:
    def test_string_in_list(self):
        contained_by("a", ["a", "b", "c"])

    def test_key_in_dict(self):
        contained_by("key", {"key": 1})

    def test_missing_raises(self):
        with pytest.raises(AssertionError):
            contained_by("z", ["a", "b"])


# ── length assertions ───────────────────────────────────────

class TestLengthEquals:
    def test_list_length(self):
        length_equals([1, 2, 3], 3)

    def test_string_length(self):
        length_equals("abc", 3)

    def test_dict_length(self):
        length_equals({"a": 1, "b": 2}, 2)

    def test_int_length(self):
        """Integers are converted to str first"""
        length_equals(12345, 5)

    def test_wrong_length_raises(self):
        with pytest.raises(AssertionError):
            length_equals([1, 2], 3)

    def test_string_length_value(self):
        length_equals("4444", 4)


class TestLengthGreaterThan:
    def test_gt(self):
        length_greater_than([1, 2, 3], 2)

    def test_equal_raises(self):
        with pytest.raises(AssertionError):
            length_greater_than([1, 2, 3], 3)

    def test_less_raises(self):
        with pytest.raises(AssertionError):
            length_greater_than([1], 3)


class TestLengthGreaterThanOrEquals:
    def test_gt(self):
        length_greater_than_or_equals([1, 2, 3], 2)

    def test_equal(self):
        length_greater_than_or_equals([1, 2, 3], 3)

    def test_less_raises(self):
        with pytest.raises(AssertionError):
            length_greater_than_or_equals([1], 3)


class TestLengthLessThan:
    def test_lt(self):
        length_less_than([1], 3)

    def test_equal_raises(self):
        with pytest.raises(AssertionError):
            length_less_than([1, 2, 3], 3)


class TestLengthLessThanOrEquals:
    def test_lt(self):
        length_less_than_or_equals([1], 3)

    def test_equal(self):
        length_less_than_or_equals([1, 2, 3], 3)

    def test_greater_raises(self):
        with pytest.raises(AssertionError):
            length_less_than_or_equals([1, 2, 3, 4], 3)


# ── regex / startswith / endswith ───────────────────────────

class TestRegexMatch:
    def test_full_match(self):
        regex_match("hello123", r"hello\d+")

    def test_no_match_raises(self):
        with pytest.raises(AssertionError):
            regex_match("world", r"^hello")

    def test_non_string_check_raises(self):
        with pytest.raises(AssertionError):
            regex_match(123, r"\d+")


class TestStartswith:
    def test_startswith_true(self):
        startswith("hello world", "hello")

    def test_startswith_false_raises(self):
        with pytest.raises(AssertionError):
            startswith("hello", "world")


class TestEndswith:
    def test_endswith_true(self):
        endswith("hello world", "world")

    def test_endswith_false_raises(self):
        with pytest.raises(AssertionError):
            endswith("hello", "world")


# ── bool_equals ─────────────────────────────────────────────

class TestBoolEquals:
    def test_true_true(self):
        bool_equals(1, True)

    def test_false_false(self):
        bool_equals(0, False)

    def test_truthy_both(self):
        bool_equals("yes", [1])

    def test_mismatch_raises(self):
        with pytest.raises(AssertionError):
            bool_equals(1, False)


# ── response_time validators ────────────────────────────────

class TestResponseTimeLessThan:
    def test_faster(self):
        response_time_less_than(100, 200)

    def test_slower_raises(self):
        with pytest.raises(AssertionError):
            response_time_less_than(300, 200)

    def test_equal_raises(self):
        with pytest.raises(AssertionError):
            response_time_less_than(200, 200)

    def test_string_values(self):
        response_time_less_than("100", "200")


class TestResponseTimeLessThanOrEquals:
    def test_less(self):
        response_time_less_than_or_equals(100, 200)

    def test_equal(self):
        response_time_less_than_or_equals(200, 200)

    def test_greater_raises(self):
        with pytest.raises(AssertionError):
            response_time_less_than_or_equals(300, 200)
