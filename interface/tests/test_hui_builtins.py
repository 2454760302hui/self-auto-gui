"""
Tests for hui_core/hui_builtins.py
- timestamp() returns int
- rand_int(min, max) returns in range
- rand_str(length) returns correct length
- current_time() returns string
- b64_encode/decode roundtrip
- md5 returns correct hash
- sha256 returns correct hash
- to_json / from_json roundtrip
- rand_value from list
"""
import pytest
import time
import hashlib
import base64
from hui_core.hui_builtins import (
    timestamp,
    rand_int,
    rand_str,
    current_time,
    b64_encode,
    b64_decode,
    md5,
    sha256,
    encrypt,
    decrypt,
    to_json,
    from_json,
    rand_value,
)


# ── timestamp ────────────────────────────────────────────────

class TestTimestamp:
    def test_returns_int(self):
        result = timestamp()
        assert isinstance(result, int)

    def test_seconds_timestamp(self):
        result = timestamp()
        now = int(time.time())
        assert abs(result - now) <= 2


class TestTimestampMs:
    def test_millisecond_timestamp(self):
        result = timestamp(ms=True)
        assert isinstance(result, int)
        now_ms = int(time.time() * 1000)
        assert abs(result - now_ms) <= 2000


class TestRandInt:
    def test_returns_int(self):
        result = rand_int(1, 100)
        assert isinstance(result, int)

    def test_within_range(self):
        for _ in range(50):
            result = rand_int(10, 20)
            assert 10 <= result <= 20

    def test_default_range(self):
        result = rand_int()
        assert 0 <= result <= 9999


class TestRandStr:
    def test_default_length_32(self):
        result = rand_str()
        assert isinstance(result, str)
        assert len(result) == 32

    def test_fixed_length(self):
        result = rand_str(5)
        assert isinstance(result, str)
        assert len(result) == 5

    def test_range_length(self):
        for _ in range(20):
            result = rand_str(3, 10)
            assert 3 <= len(result) <= 10

    def test_is_hex_chars(self):
        """rand_str is based on uuid4, so it returns hex chars"""
        result = rand_str(16)
        assert all(c in '0123456789abcdef' for c in result)


class TestCurrentTime:
    def test_returns_string(self):
        result = current_time()
        assert isinstance(result, str)

    def test_default_format(self):
        result = current_time()
        # Default format: %Y-%m-%d %H:%M:%S
        assert len(result) == 19
        assert result[4] == '-'
        assert result[7] == '-'
        assert result[10] == ' '

    def test_custom_format(self):
        result = current_time('%Y%m%d')
        assert len(result) == 8
        assert result.isdigit()


class TestRandValue:
    def test_from_list(self):
        lst = [10, 20, 30]
        result = rand_value(lst)
        assert result in lst

    def test_non_list_returned_as_is(self):
        assert rand_value("hello") == "hello"
        assert rand_value(42) == 42


class TestB64EncodeDecode:
    def test_encode(self):
        result = b64_encode("hello")
        assert result == "aGVsbG8="

    def test_decode(self):
        result = b64_decode("aGVsbG8=")
        assert result == "hello"

    def test_roundtrip(self):
        original = "test string 123!@#"
        encoded = b64_encode(original)
        decoded = b64_decode(encoded)
        assert decoded == original

    def test_encode_unicode(self):
        original = "你好世界"
        encoded = b64_encode(original)
        decoded = b64_decode(encoded)
        assert decoded == original


class TestMd5:
    def test_md5_hello(self):
        result = md5("hello")
        assert result == "5d41402abc4b2a76b9719d911017c592"

    def test_md5_empty(self):
        result = md5("")
        assert result == "d41d8cd98f00b204e9800998ecf8427e"

    def test_md5_returns_hex_string(self):
        result = md5("test")
        assert isinstance(result, str)
        assert len(result) == 32
        assert all(c in '0123456789abcdef' for c in result)


class TestSha256:
    def test_sha256_hello(self):
        result = sha256("hello")
        assert result == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"

    def test_sha256_returns_hex_string(self):
        result = sha256("test")
        assert isinstance(result, str)
        assert len(result) == 64


class TestEncryptDecrypt:
    def test_encrypt_base64(self):
        result = encrypt("hello", method="base64")
        assert result == "aGVsbG8="

    def test_encrypt_md5(self):
        result = encrypt("hello", method="md5")
        assert result == "5d41402abc4b2a76b9719d911017c592"

    def test_encrypt_sha256(self):
        result = encrypt("hello", method="sha256")
        assert result == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"

    def test_decrypt_base64(self):
        result = decrypt("aGVsbG8=", method="base64")
        assert result == "hello"

    def test_encrypt_unsupported_method_returns_original(self):
        result = encrypt("hello", method="unknown")
        assert result == "hello"

    def test_decrypt_unsupported_method_returns_original(self):
        result = decrypt("hello", method="unknown")
        assert result == "hello"


class TestToJsonFromJson:
    def test_to_json(self):
        result = to_json({"key": "value"})
        assert isinstance(result, str)
        assert '"key"' in result

    def test_from_json(self):
        result = from_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_roundtrip(self):
        original = {"name": "test", "count": 42, "items": [1, 2]}
        json_str = to_json(original)
        restored = from_json(json_str)
        assert restored == original

    def test_to_json_unicode(self):
        result = to_json({"name": "你好"})
        assert "你好" in result


class TestEncryptCaseInsensitive:
    def test_encrypt_Base64(self):
        result = encrypt("hello", method="Base64")
        assert result == "aGVsbG8="

    def test_encrypt_MD5(self):
        result = encrypt("hello", method="MD5")
        assert result == "5d41402abc4b2a76b9719d911017c592"
