"""
Tests for hui_core/extract.py
- JSONPath extraction $.data.name
- JMESPath extraction body.data.name
- Regex extraction with groups
- Header extraction
- Nonexistent paths return empty/None

Uses plain dicts to mock responses (no real HTTP calls).
"""
import pytest
from unittest.mock import MagicMock
from hui_core.extract import (
    extract_by_jsonpath,
    extract_by_jmespath,
    extract_by_regex,
    extract_by_object,
    extract_by_ws,
)


# ── extract_by_jsonpath ──────────────────────────────────────

class TestExtractByJsonpath:
    def test_simple_key(self):
        data = {"code": 200, "msg": "ok"}
        assert extract_by_jsonpath(data, "$.code") == 200

    def test_nested_key(self):
        data = {"data": {"name": "Alice"}}
        assert extract_by_jsonpath(data, "$.data.name") == "Alice"

    def test_array_element(self):
        data = {"items": [10, 20, 30]}
        assert extract_by_jsonpath(data, "$.items[0]") == 10

    def test_deeply_nested(self):
        data = {"a": {"b": {"c": "deep"}}}
        assert extract_by_jsonpath(data, "$.a.b.c") == "deep"

    def test_multiple_matches_returns_list(self):
        data = {"items": [{"id": 1}, {"id": 2}, {"id": 3}]}
        result = extract_by_jsonpath(data, "$.items[*].id")
        assert result == [1, 2, 3]

    def test_nonexistent_path_returns_none(self):
        data = {"code": 200}
        result = extract_by_jsonpath(data, "$.missing_key")
        assert result is None

    def test_non_string_expression_returned_as_is(self):
        result = extract_by_jsonpath({"a": 1}, 42)
        assert result == 42


# ── extract_by_jmespath ──────────────────────────────────────

class TestExtractByJmespath:
    def test_body_dot_name(self):
        data = {"body": {"name": "Bob"}}
        assert extract_by_jmespath(data, "body.name") == "Bob"

    def test_body_nested(self):
        data = {"body": {"data": {"id": 99}}}
        assert extract_by_jmespath(data, "body.data.id") == 99

    def test_headers_extraction(self):
        data = {"headers": {"ContentType": "application/json"}}
        assert extract_by_jmespath(data, "headers.ContentType") == "application/json"

    def test_cookies_extraction(self):
        data = {"cookies": {"session_id": "abc123"}}
        assert extract_by_jmespath(data, "cookies.session_id") == "abc123"

    def test_nonexistent_path_returns_none(self):
        data = {"body": {"name": "Bob"}}
        result = extract_by_jmespath(data, "body.missing")
        assert result is None

    def test_non_string_expression_returned_as_is(self):
        result = extract_by_jmespath({"body": {}}, 42)
        assert result == 42

    def test_jmespath_array_projection(self):
        data = {"body": {"people": [{"name": "A"}, {"name": "B"}]}}
        result = extract_by_jmespath(data, "body.people[*].name")
        assert result == ["A", "B"]


# ── extract_by_regex ─────────────────────────────────────────

class TestExtractByRegex:
    def test_simple_regex(self):
        text = "token: abc123xyz"
        result = extract_by_regex(text, r"token: (\w+)")
        assert result == "abc123xyz"

    def test_regex_with_multiple_groups(self):
        text = "name=alice age=30"
        result = extract_by_regex(text, r"(\w+)=(\w+)")
        assert isinstance(result, list)
        assert ('name', 'alice') in result

    def test_regex_no_match_returns_empty_string(self):
        text = "nothing here"
        result = extract_by_regex(text, r"token: (\w+)")
        assert result == ""

    def test_regex_single_match_returns_string(self):
        text = "id=42"
        result = extract_by_regex(text, r"id=(\d+)")
        assert result == "42"
        assert isinstance(result, str)

    def test_non_string_expression_returned_as_is(self):
        result = extract_by_regex("text", 42)
        assert result == 42


# ── extract_by_object (mocked Response) ──────────────────────

class TestExtractByObject:
    def _make_mock_response(self, json_body=None, text="", headers=None,
                            status_code=200, url="http://test", ok=True,
                            encoding="utf-8"):
        """Create a mock requests.Response object."""
        resp = MagicMock()
        resp.json.return_value = json_body or {}
        resp.text = text
        resp.headers = headers or {}
        resp.cookies = {}
        resp.status_code = status_code
        resp.url = url
        resp.ok = ok
        resp.encoding = encoding
        return resp

    def test_status_code(self):
        resp = self._make_mock_response(status_code=201)
        assert extract_by_object(resp, "status_code") == 201

    def test_url(self):
        resp = self._make_mock_response(url="http://example.com/api")
        assert extract_by_object(resp, "url") == "http://example.com/api"

    def test_ok(self):
        resp = self._make_mock_response(ok=True)
        assert extract_by_object(resp, "ok") is True

    def test_encoding(self):
        resp = self._make_mock_response(encoding="utf-8")
        assert extract_by_object(resp, "encoding") == "utf-8"

    def test_text_attribute(self):
        resp = self._make_mock_response(text="raw body text")
        assert extract_by_object(resp, "text") == "raw body text"

    def test_jsonpath_extraction(self):
        resp = self._make_mock_response(json_body={"data": {"name": "Carol"}})
        assert extract_by_object(resp, "$.data.name") == "Carol"

    def test_body_jmespath_extraction(self):
        resp = self._make_mock_response(json_body={"name": "Dave", "age": 28})
        assert extract_by_object(resp, "body.name") == "Dave"

    def test_content_jmespath_extraction(self):
        resp = self._make_mock_response(json_body={"count": 5})
        assert extract_by_object(resp, "body.count") == 5

    def test_header_extraction(self):
        resp = self._make_mock_response(headers={"XToken": "tok123"})
        assert extract_by_object(resp, "headers.XToken") == "tok123"

    def test_regex_extraction(self):
        resp = self._make_mock_response(text='{"token": "abc123"}')
        result = extract_by_object(resp, r'"token":\s*"(.+?)"')
        assert result == "abc123"

    def test_nonexistent_jsonpath_returns_none(self):
        resp = self._make_mock_response(json_body={"data": {}})
        result = extract_by_object(resp, "$.data.missing")
        assert result is None

    def test_nonexistent_body_path_returns_none(self):
        resp = self._make_mock_response(json_body={"data": {}})
        result = extract_by_object(resp, "body.data.missing")
        assert result is None

    def test_non_string_expression_returned_as_is(self):
        resp = self._make_mock_response()
        assert extract_by_object(resp, 42) == 42

    def test_unknown_expression_returned_as_is(self):
        resp = self._make_mock_response()
        assert extract_by_object(resp, "something_plain") == "something_plain"


# ── extract_by_ws (websocket dict) ──────────────────────────

class TestExtractByWs:
    def test_status_code(self):
        ws_resp = {"status": 101, "recv": "hello"}
        assert extract_by_ws(ws_resp, "status_code") == 101

    def test_status_alias(self):
        ws_resp = {"status": 101, "recv": "hello"}
        assert extract_by_ws(ws_resp, "status") == 101

    def test_text_extraction(self):
        ws_resp = {"status": 101, "recv": "some message"}
        assert extract_by_ws(ws_resp, "text") == "some message"

    def test_body_extraction(self):
        ws_resp = {"status": 101, "recv": "some message"}
        assert extract_by_ws(ws_resp, "body") == "some message"

    def test_jsonpath_from_recv(self):
        ws_resp = {"status": 101, "recv": '{"name": "Eve"}'}
        assert extract_by_ws(ws_resp, "$.name") == "Eve"

    def test_regex_from_recv(self):
        ws_resp = {"status": 101, "recv": "token=abc123 end"}
        result = extract_by_ws(ws_resp, r"token=(.+?) end")
        assert result == "abc123"

    def test_body_jmespath_from_recv(self):
        ws_resp = {"status": 101, "recv": '{"name": "Frank"}'}
        assert extract_by_ws(ws_resp, "body.name") == "Frank"

    def test_non_string_expression_returned_as_is(self):
        ws_resp = {"status": 101, "recv": "msg"}
        assert extract_by_ws(ws_resp, 42) == 42

    def test_unknown_expression_returned_as_is(self):
        ws_resp = {"status": 101, "recv": "msg"}
        assert extract_by_ws(ws_resp, "unknown_key") == "unknown_key"
