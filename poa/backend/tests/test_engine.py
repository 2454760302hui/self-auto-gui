"""Tests for core.engine — variable rendering, extraction, assertions, execution"""
import pytest
import re
import time
import json
from unittest.mock import patch, AsyncMock, MagicMock
from backend.core.engine import (
    render,
    _render_str,
    _eval_builtin,
    extract_variable,
    run_assertion,
    run_script,
    execute_request,
    execute_suite,
)


# ════════════════════════════════════════════════════════════════
#  Variable Rendering
# ════════════════════════════════════════════════════════════════
class TestRenderString:
    """Test _render_str and render for string templates."""

    def test_double_brace_variable(self):
        result = render("Hello {{name}}", {"name": "World"})
        assert result == "Hello World"

    def test_dollar_brace_variable(self):
        result = render("Hello ${name}", {"name": "World"})
        assert result == "Hello World"

    def test_mixed_brace_styles(self):
        result = render("{{greeting}} ${name}", {"greeting": "Hi", "name": "Alice"})
        assert result == "Hi Alice"

    def test_multiple_same_variable(self):
        result = render("{{x}}-{{x}}-{{x}}", {"x": "val"})
        assert result == "val-val-val"

    def test_missing_variable_kept_as_is(self):
        result = render("{{unknown}}", {})
        assert result == "{{unknown}}"

    def test_full_match_returns_native_type_int(self):
        result = render("{{count}}", {"count": 42})
        assert result == 42
        assert isinstance(result, int)

    def test_full_match_returns_native_type_float(self):
        result = render("{{ratio}}", {"ratio": 3.14})
        assert result == 3.14
        assert isinstance(result, float)

    def test_full_match_returns_native_type_bool(self):
        result = render("{{flag}}", {"flag": True})
        assert result is True

    def test_partial_match_returns_string(self):
        result = render("count={{count}}", {"count": 42})
        assert result == "count=42"
        assert isinstance(result, str)

    def test_empty_string_template(self):
        result = render("", {"x": 1})
        assert result == ""

    def test_no_variables_in_template(self):
        result = render("plain text", {"x": 1})
        assert result == "plain text"

    def test_whitespace_in_expression(self):
        result = render("{{ name }}", {"name": "Bob"})
        assert result == "Bob"


class TestRenderDict:
    """Test recursive rendering in dictionaries."""

    def test_dict_values_rendered(self):
        template = {"key": "{{val}}", "num": "{{n}}"}
        result = render(template, {"val": "hello", "n": 10})
        assert result == {"key": "hello", "num": 10}

    def test_nested_dict(self):
        template = {"outer": {"inner": "{{x}}"}}
        result = render(template, {"x": "deep"})
        assert result == {"outer": {"inner": "deep"}}

    def test_dict_with_list_value(self):
        template = {"items": ["{{a}}", "{{b}}"]}
        result = render(template, {"a": "1", "b": "2"})
        assert result == {"items": ["1", "2"]}

    def test_dict_keys_not_rendered(self):
        template = {"{{key}}": "value"}
        result = render(template, {"key": "real_key"})
        assert "{{key}}" in result


class TestRenderList:
    """Test recursive rendering in lists."""

    def test_list_items_rendered(self):
        template = ["{{a}}", "{{b}}", "{{c}}"]
        result = render(template, {"a": "x", "b": "y", "c": "z"})
        assert result == ["x", "y", "z"]

    def test_nested_list(self):
        template = [["{{a}}"], ["{{b}}"]]
        result = render(template, {"a": "1", "b": "2"})
        assert result == [["1"], ["2"]]

    def test_list_with_dict_items(self):
        template = [{"name": "{{n}}"}, {"name": "{{m}}"}]
        result = render(template, {"n": "Alice", "m": "Bob"})
        assert result == [{"name": "Alice"}, {"name": "Bob"}]


class TestRenderPassthrough:
    """Non-string/dict/list types pass through unchanged."""

    def test_int_passthrough(self):
        assert render(42, {"x": 1}) == 42

    def test_none_passthrough(self):
        assert render(None, {"x": 1}) is None

    def test_bool_passthrough(self):
        assert render(True, {"x": 1}) is True

    def test_float_passthrough(self):
        assert render(3.14, {"x": 1}) == 3.14


# ════════════════════════════════════════════════════════════════
#  Built-in Functions
# ════════════════════════════════════════════════════════════════
class TestBuiltinFunctions:

    def test_timestamp(self):
        before = int(time.time())
        result = _eval_builtin("timestamp()", {})
        after = int(time.time())
        assert before <= result <= after

    def test_timestamp_ms(self):
        before = int(time.time() * 1000)
        result = _eval_builtin("timestamp_ms()", {})
        after = int(time.time() * 1000)
        assert before <= result <= after

    def test_uuid(self):
        result = _eval_builtin("uuid()", {})
        assert isinstance(result, str)
        assert len(result) == 32

    def test_uuid_uniqueness(self):
        a = _eval_builtin("uuid()", {})
        b = _eval_builtin("uuid()", {})
        assert a != b

    def test_rand_str_default(self):
        result = _eval_builtin("rand_str()", {})
        assert isinstance(result, str)
        assert len(result) == 16

    def test_rand_str_with_length(self):
        result = _eval_builtin("rand_str(8)", {})
        assert isinstance(result, str)
        assert len(result) == 8

    def test_rand_int_default(self):
        result = _eval_builtin("rand_int()", {})
        assert isinstance(result, int)
        assert 0 <= result <= 9999

    def test_rand_int_with_range(self):
        result = _eval_builtin("rand_int(100, 200)", {})
        assert isinstance(result, int)
        assert 100 <= result <= 200

    def test_builtin_via_render(self):
        result = render("ts={{timestamp()}}", {})
        assert result.startswith("ts=")
        assert int(result.split("=")[1]) > 0

    def test_fake_name(self):
        result = _eval_builtin("fake.name()", {})
        assert isinstance(result, str)
        assert len(result) > 0

    def test_fake_phone(self):
        result = _eval_builtin("fake.phone()", {})
        assert isinstance(result, str)
        assert len(result) > 0

    def test_fake_email(self):
        result = _eval_builtin("fake.email()", {})
        assert isinstance(result, str)
        assert "@" in result

    def test_unknown_expression_returns_none(self):
        result = _eval_builtin("unknown_func()", {})
        assert result is None


# ════════════════════════════════════════════════════════════════
#  Variable Extraction
# ════════════════════════════════════════════════════════════════
class TestExtractVariable:

    @pytest.fixture
    def sample_response(self):
        return {
            "status_code": 200,
            "headers": {
                "Content-Type": "application/json",
                "X-Request-Id": "abc-123",
            },
            "json": {
                "user": {
                    "id": 42,
                    "name": "Alice",
                    "tags": ["admin", "vip"],
                },
                "items": [1, 2, 3],
            },
            "text": '{"user": {"id": 42, "name": "Alice"}}',
        }

    def test_extract_status_code(self, sample_response):
        assert extract_variable(sample_response, "status_code") == 200

    def test_extract_status_alias(self, sample_response):
        assert extract_variable(sample_response, "status") == 200

    def test_extract_header(self, sample_response):
        assert extract_variable(sample_response, "headers.Content-Type") == "application/json"

    def test_extract_header_case_sensitive(self, sample_response):
        assert extract_variable(sample_response, "headers.X-Request-Id") == "abc-123"

    def test_extract_header_missing(self, sample_response):
        assert extract_variable(sample_response, "headers.X-Missing") is None

    def test_extract_jsonpath_simple(self, sample_response):
        result = extract_variable(sample_response, "$.user.id")
        assert result == 42

    def test_extract_jsonpath_nested(self, sample_response):
        result = extract_variable(sample_response, "$.user.name")
        assert result == "Alice"

    def test_extract_jsonpath_array(self, sample_response):
        result = extract_variable(sample_response, "$.items")
        assert result == [1, 2, 3]

    def test_extract_jsonpath_missing(self, sample_response):
        result = extract_variable(sample_response, "$.nonexistent.path")
        assert result is None

    def test_extract_jmespath(self, sample_response):
        result = extract_variable(sample_response, "user.name")
        assert result == "Alice"

    def test_extract_jmespath_nested(self, sample_response):
        result = extract_variable(sample_response, "user.id")
        assert result == 42

    def test_extract_regex_with_group(self, sample_response):
        result = extract_variable(sample_response, r're:"id":\s*(\d+)')
        assert result == "42"

    def test_extract_regex_no_group(self, sample_response):
        result = extract_variable(sample_response, r're:"id":\s*\d+')
        assert result == '"id": 42'

    def test_extract_regex_no_match(self, sample_response):
        result = extract_variable(sample_response, r're:not_found_pattern')
        assert result is None

    def test_extract_empty_text(self):
        resp = {"text": "", "json": None}
        result = extract_variable(resp, r're:something')
        assert result is None


# ════════════════════════════════════════════════════════════════
#  Assertions
# ════════════════════════════════════════════════════════════════
class TestRunAssertion:

    @pytest.fixture
    def resp_data(self):
        return {
            "status_code": 200,
            "elapsed_ms": 150.5,
            "headers": {"Content-Type": "application/json"},
            "json": {"name": "Alice", "age": 30, "tags": ["admin"]},
        }

    def _assert(self, a_type, expected="", source="body", path="",
                resp=None, variables=None):
        assertion = {
            "type": a_type,
            "source": source,
            "path": path,
            "expected": expected,
        }
        return run_assertion(assertion, resp or {}, variables or {})

    # -- eq --
    def test_eq_pass(self, resp_data):
        result = self._assert("eq", expected=200, source="status", resp=resp_data)
        assert result["passed"] is True

    def test_eq_fail(self, resp_data):
        result = self._assert("eq", expected=404, source="status", resp=resp_data)
        assert result["passed"] is False

    # -- ne --
    def test_ne_pass(self, resp_data):
        result = self._assert("ne", expected=404, source="status", resp=resp_data)
        assert result["passed"] is True

    def test_ne_fail(self, resp_data):
        result = self._assert("ne", expected=200, source="status", resp=resp_data)
        assert result["passed"] is False

    # -- gt --
    def test_gt_pass(self, resp_data):
        result = self._assert("gt", expected=100, source="response_time", resp=resp_data)
        assert result["passed"] is True

    def test_gt_fail(self, resp_data):
        result = self._assert("gt", expected=200, source="response_time", resp=resp_data)
        assert result["passed"] is False

    # -- lt --
    def test_lt_pass(self, resp_data):
        result = self._assert("lt", expected=200, source="response_time", resp=resp_data)
        assert result["passed"] is True

    def test_lt_fail(self, resp_data):
        result = self._assert("lt", expected=100, source="response_time", resp=resp_data)
        assert result["passed"] is False

    # -- contains --
    def test_contains_pass(self, resp_data):
        result = self._assert("contains", expected="json",
                              source="header", path="Content-Type",
                              resp=resp_data)
        assert result["passed"] is True

    def test_contains_fail(self, resp_data):
        result = self._assert("contains", expected="xml",
                              source="header", path="Content-Type",
                              resp=resp_data)
        assert result["passed"] is False

    # -- not_contains --
    def test_not_contains_pass(self, resp_data):
        result = self._assert("not_contains", expected="xml",
                              source="header", path="Content-Type",
                              resp=resp_data)
        assert result["passed"] is True

    def test_not_contains_fail(self, resp_data):
        result = self._assert("not_contains", expected="json",
                              source="header", path="Content-Type",
                              resp=resp_data)
        assert result["passed"] is False

    # -- exists --
    def test_exists_pass(self, resp_data):
        result = self._assert("exists", source="body",
                              path="$.name", resp=resp_data)
        assert result["passed"] is True

    def test_exists_fail(self, resp_data):
        result = self._assert("exists", source="body",
                              path="$.missing_field", resp=resp_data)
        assert result["passed"] is False

    # -- not_exists --
    def test_not_exists_pass(self, resp_data):
        result = self._assert("not_exists", source="body",
                              path="$.missing_field", resp=resp_data)
        assert result["passed"] is True

    def test_not_exists_fail(self, resp_data):
        result = self._assert("not_exists", source="body",
                              path="$.name", resp=resp_data)
        assert result["passed"] is False

    # -- regex --
    def test_regex_pass(self, resp_data):
        result = self._assert("regex", expected="^application/",
                              source="header", path="Content-Type",
                              resp=resp_data)
        assert result["passed"] is True

    def test_regex_fail(self, resp_data):
        result = self._assert("regex", expected="^text/",
                              source="header", path="Content-Type",
                              resp=resp_data)
        assert result["passed"] is False

    # -- len_eq --
    def test_len_eq_pass(self, resp_data):
        result = self._assert("len_eq", expected=1,
                              source="body", path="$.tags",
                              resp=resp_data)
        assert result["passed"] is True

    def test_len_eq_fail(self, resp_data):
        result = self._assert("len_eq", expected=3,
                              source="body", path="$.tags",
                              resp=resp_data)
        assert result["passed"] is False

    # -- len_gt --
    def test_len_gt_pass(self, resp_data):
        result = self._assert("len_gt", expected=0,
                              source="body", path="$.tags",
                              resp=resp_data)
        assert result["passed"] is True

    # -- len_lt --
    def test_len_lt_pass(self, resp_data):
        result = self._assert("len_lt", expected=5,
                              source="body", path="$.tags",
                              resp=resp_data)
        assert result["passed"] is True

    # -- type coercion --
    def test_type_coercion_str_to_int(self):
        resp = {"status_code": "200"}
        result = self._assert("eq", expected=200, source="status", resp=resp)
        assert result["passed"] is True

    def test_type_coercion_int_to_str(self):
        resp = {
            "status_code": 200,
            "json": {"id": 42},
        }
        result = self._assert("eq", expected="42", source="body",
                              path="$.id", resp=resp)
        assert result["passed"] is True

    # -- default assertion type falls back to eq --
    def test_default_type_is_eq(self, resp_data):
        assertion = {"source": "status", "path": "", "expected": 200}
        result = run_assertion(assertion, resp_data, {})
        assert result["passed"] is True

    # -- assertion result structure --
    def test_result_has_all_keys(self, resp_data):
        result = self._assert("eq", expected=200, source="status", resp=resp_data)
        for key in ("passed", "message", "actual", "expected", "type"):
            assert key in result


# ════════════════════════════════════════════════════════════════
#  Script Execution
# ════════════════════════════════════════════════════════════════
class TestRunScript:

    def test_set_variable(self):
        context = {}
        script = "poa.setVariable('token', 'abc123')"
        updated = run_script(script, context)
        assert updated["token"] == "abc123"
        assert context["token"] == "abc123"

    def test_get_variable(self):
        context = {"existing": "value"}
        script = "poa.setVariable('copy', poa.getVariable('existing'))"
        updated = run_script(script, context)
        assert updated["copy"] == "value"

    def test_set_env_variable(self):
        context = {}
        script = "poa.setEnvVariable('host', 'http://example.com')"
        updated = run_script(script, context)
        assert updated["__env__host"] == "http://example.com"
        assert context["host"] == "http://example.com"

    def test_empty_script_returns_context(self):
        context = {"x": 1}
        updated = run_script("", context)
        assert updated == context

    def test_none_script_returns_context(self):
        context = {"x": 1}
        updated = run_script(None, context)
        assert updated == context

    def test_whitespace_script_returns_context(self):
        context = {"x": 1}
        updated = run_script("   \n  ", context)
        assert updated == context

    def test_script_error_does_not_raise(self):
        context = {}
        updated = run_script("raise RuntimeError('boom')", context)
        assert updated == {}

    def test_response_available_in_script(self):
        context = {"__response__": {"status_code": 200}}
        script = "poa.setVariable('code', response['status_code'])"
        updated = run_script(script, context)
        assert updated["code"] == 200


# ════════════════════════════════════════════════════════════════
#  HTTP Request Execution (mocked httpx)
# ════════════════════════════════════════════════════════════════
import httpx


class TestExecuteRequest:

    @pytest.fixture
    def mock_response(self):
        resp = MagicMock()
        resp.status_code = 200
        resp.headers = {"Content-Type": "application/json"}
        resp.text = '{"message": "ok"}'
        resp.json.return_value = {"message": "ok"}
        resp.content = b'{"message": "ok"}'
        return resp

    @pytest.mark.asyncio
    async def test_basic_get_request(self, mock_response):
        with patch("backend.core.engine.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.request = AsyncMock(return_value=mock_response)
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            api_config = {
                "method": "GET",
                "url": "https://api.example.com/users",
                "headers": {},
                "params": {},
                "body_type": "none",
                "assertions": [],
                "extractions": [],
            }
            result = await execute_request(api_config, {})

            assert result["response"]["status_code"] == 200
            assert result["passed"] is True

    @pytest.mark.asyncio
    async def test_variable_substitution_in_request(self, mock_response):
        with patch("backend.core.engine.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.request = AsyncMock(return_value=mock_response)
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            api_config = {
                "method": "GET",
                "url": "{{base_url}}/users",
                "headers": {"Authorization": "Bearer {{token}}"},
                "params": {},
                "body_type": "none",
                "assertions": [],
                "extractions": [],
            }
            variables = {"base_url": "https://api.example.com", "token": "secret123"}
            result = await execute_request(api_config, variables)

            assert result["request"]["url"] == "https://api.example.com/users"
            assert result["request"]["headers"]["Authorization"] == "Bearer secret123"

    @pytest.mark.asyncio
    async def test_json_body_request(self, mock_response):
        with patch("backend.core.engine.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.request = AsyncMock(return_value=mock_response)
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            api_config = {
                "method": "POST",
                "url": "https://api.example.com/users",
                "headers": {},
                "params": {},
                "body_type": "json",
                "body": '{"name": "{{username}}"}',
                "assertions": [],
                "extractions": [],
            }
            result = await execute_request(api_config, {"username": "Alice"})
            assert result["passed"] is True

    @pytest.mark.asyncio
    async def test_extraction_from_response(self, mock_response):
        with patch("backend.core.engine.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.request = AsyncMock(return_value=mock_response)
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            api_config = {
                "method": "GET",
                "url": "https://api.example.com/users",
                "headers": {},
                "params": {},
                "body_type": "none",
                "assertions": [],
                "extractions": [
                    {"key": "msg", "expression": "message", "enabled": True},
                ],
            }
            result = await execute_request(api_config, {})
            assert result["extracted"]["msg"] == "ok"

    @pytest.mark.asyncio
    async def test_assertion_pass(self, mock_response):
        with patch("backend.core.engine.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.request = AsyncMock(return_value=mock_response)
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            api_config = {
                "method": "GET",
                "url": "https://api.example.com/users",
                "headers": {},
                "params": {},
                "body_type": "none",
                "assertions": [
                    {"type": "eq", "source": "status", "path": "", "expected": 200, "enabled": True},
                ],
                "extractions": [],
            }
            result = await execute_request(api_config, {})
            assert result["passed"] is True
            assert len(result["assertions"]) == 1

    @pytest.mark.asyncio
    async def test_assertion_fail(self, mock_response):
        with patch("backend.core.engine.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.request = AsyncMock(return_value=mock_response)
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            api_config = {
                "method": "GET",
                "url": "https://api.example.com/users",
                "headers": {},
                "params": {},
                "body_type": "none",
                "assertions": [
                    {"type": "eq", "source": "status", "path": "", "expected": 404, "enabled": True},
                ],
                "extractions": [],
            }
            result = await execute_request(api_config, {})
            assert result["passed"] is False

    @pytest.mark.asyncio
    async def test_disabled_assertion_skipped(self, mock_response):
        with patch("backend.core.engine.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.request = AsyncMock(return_value=mock_response)
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            api_config = {
                "method": "GET",
                "url": "https://api.example.com/users",
                "headers": {},
                "params": {},
                "body_type": "none",
                "assertions": [
                    {"type": "eq", "source": "status", "path": "", "expected": 999, "enabled": False},
                ],
                "extractions": [],
            }
            result = await execute_request(api_config, {})
            assert result["passed"] is True
            assert len(result["assertions"]) == 0

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        with patch("backend.core.engine.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.request = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            api_config = {
                "method": "GET",
                "url": "https://slow.example.com",
                "headers": {},
                "params": {},
                "body_type": "none",
                "assertions": [],
                "extractions": [],
            }
            result = await execute_request(api_config, {})
            assert result["response"]["error"] == "Request timeout"
            assert result["response"]["status_code"] == 0


# ════════════════════════════════════════════════════════════════
#  Test Suite Execution (mocked execute_request)
# ════════════════════════════════════════════════════════════════
class TestExecuteSuite:

    @pytest.mark.asyncio
    async def test_all_steps_pass(self):
        mock_result = {
            "passed": True,
            "request": {"method": "GET", "url": "http://example.com",
                        "headers": {}, "params": {}, "body_type": "none", "body": ""},
            "response": {"status_code": 200},
            "assertions": [],
            "extracted": {"token": "abc"},
        }
        with patch("backend.core.engine.execute_request", new_callable=AsyncMock, return_value=mock_result):
            steps = [
                {"name": "Step 1", "enabled": True},
                {"name": "Step 2", "enabled": True},
            ]
            result = await execute_suite(steps, {})
            assert result["total"] == 2
            assert result["passed"] == 2
            assert result["failed"] == 0
            assert result["status"] == "passed"

    @pytest.mark.asyncio
    async def test_step_failure(self):
        fail_result = {
            "passed": False,
            "request": {"method": "GET", "url": "http://example.com",
                        "headers": {}, "params": {}, "body_type": "none", "body": ""},
            "response": {"status_code": 500},
            "assertions": [{"passed": False}],
            "extracted": {},
        }
        with patch("backend.core.engine.execute_request", new_callable=AsyncMock, return_value=fail_result):
            steps = [{"name": "Failing Step", "enabled": True}]
            result = await execute_suite(steps, {})
            assert result["total"] == 1
            assert result["failed"] == 1
            assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_disabled_steps_skipped(self):
        with patch("backend.core.engine.execute_request", new_callable=AsyncMock) as mock_exec:
            steps = [
                {"name": "Active", "enabled": True},
                {"name": "Disabled", "enabled": False},
            ]
            mock_result = {
                "passed": True,
                "request": {"method": "GET", "url": "",
                            "headers": {}, "params": {}, "body_type": "none", "body": ""},
                "response": {},
                "assertions": [],
                "extracted": {},
            }
            mock_exec.return_value = mock_result
            result = await execute_suite(steps, {})
            assert result["total"] == 1
            assert mock_exec.call_count == 1

    @pytest.mark.asyncio
    async def test_extracted_variables_carry_forward(self):
        step1_result = {
            "passed": True,
            "request": {"method": "GET", "url": "",
                        "headers": {}, "params": {}, "body_type": "none", "body": ""},
            "response": {},
            "assertions": [],
            "extracted": {"session_id": "sess-xyz"},
        }
        step2_result = {
            "passed": True,
            "request": {"method": "GET", "url": "",
                        "headers": {}, "params": {}, "body_type": "none", "body": ""},
            "response": {},
            "assertions": [],
            "extracted": {},
        }
        with patch("backend.core.engine.execute_request", new_callable=AsyncMock) as mock_exec:
            mock_exec.side_effect = [step1_result, step2_result]
            steps = [
                {"name": "Login", "enabled": True},
                {"name": "Use session", "enabled": True},
            ]
            result = await execute_suite(steps, {})
            second_call_vars = mock_exec.call_args_list[1][0][1]
            assert "session_id" in second_call_vars

    @pytest.mark.asyncio
    async def test_stop_on_failure(self):
        fail_result = {
            "passed": False,
            "request": {"method": "GET", "url": "",
                        "headers": {}, "params": {}, "body_type": "none", "body": ""},
            "response": {},
            "assertions": [{"passed": False}],
            "extracted": {},
        }
        with patch("backend.core.engine.execute_request", new_callable=AsyncMock, return_value=fail_result):
            steps = [
                {"name": "Fails", "enabled": True, "stop_on_failure": True},
                {"name": "Should not run", "enabled": True},
            ]
            result = await execute_suite(steps, {})
            assert result["total"] == 1
