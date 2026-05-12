"""Tests for routers.auth — JWT token, password hashing, token expiration"""
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import patch

from jose import jwt, JWTError

from backend.routers.auth import (
    hash_password,
    verify_password,
    create_token,
    SECRET_KEY,
    ALGORITHM,
    TOKEN_EXPIRE_DAYS,
)


# ════════════════════════════════════════════════════════════════
#  Password Hashing
# ════════════════════════════════════════════════════════════════
class TestPasswordHashing:

    def test_hash_password_returns_string(self):
        result = hash_password("mypassword")
        assert isinstance(result, str)

    def test_hash_password_not_plaintext(self):
        plain = "mypassword"
        hashed = hash_password(plain)
        assert hashed != plain

    def test_hash_password_bcrypt_format(self):
        """bcrypt hashes start with $2b$"""
        hashed = hash_password("test123")
        assert hashed.startswith("$2b$")

    def test_verify_password_correct(self):
        plain = "correct_password"
        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True

    def test_verify_password_incorrect(self):
        hashed = hash_password("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_verify_password_empty_string(self):
        hashed = hash_password("")
        assert verify_password("", hashed) is True
        assert verify_password("notempty", hashed) is False

    def test_different_passwords_different_hashes(self):
        hash1 = hash_password("password1")
        hash2 = hash_password("password2")
        assert hash1 != hash2

    def test_same_password_different_hashes(self):
        """bcrypt generates different salts each time"""
        hash1 = hash_password("same_password")
        hash2 = hash_password("same_password")
        assert hash1 != hash2  # different salt

    def test_same_password_both_verify(self):
        """Even with different hashes, same password still verifies"""
        hash1 = hash_password("same_password")
        hash2 = hash_password("same_password")
        assert verify_password("same_password", hash1) is True
        assert verify_password("same_password", hash2) is True


# ════════════════════════════════════════════════════════════════
#  JWT Token Creation
# ════════════════════════════════════════════════════════════════
class TestCreateToken:

    def test_create_token_returns_string(self):
        token = create_token(1, "testuser")
        assert isinstance(token, str)

    def test_create_token_not_empty(self):
        token = create_token(1, "testuser")
        assert len(token) > 0

    def test_create_token_decodable(self):
        user_id = 42
        username = "alice"
        token = create_token(user_id, username)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert int(payload["sub"]) == user_id
        assert payload["username"] == username

    def test_create_token_contains_exp(self):
        token = create_token(1, "testuser")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert "exp" in payload

    def test_create_token_expiry_is_future(self):
        before = datetime.utcnow()
        token = create_token(1, "testuser")
        after = datetime.utcnow()
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp_time = datetime.utcfromtimestamp(payload["exp"])
        expected_min = before + timedelta(days=TOKEN_EXPIRE_DAYS) - timedelta(seconds=2)
        expected_max = after + timedelta(days=TOKEN_EXPIRE_DAYS) + timedelta(seconds=2)
        assert expected_min <= exp_time <= expected_max

    def test_create_token_sub_is_string(self):
        """The sub claim is stored as string of the user_id"""
        token = create_token(123, "bob")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "123"

    def test_create_token_different_users(self):
        token1 = create_token(1, "user1")
        token2 = create_token(2, "user2")
        assert token1 != token2

        payload1 = jwt.decode(token1, SECRET_KEY, algorithms=[ALGORITHM])
        payload2 = jwt.decode(token2, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload1["sub"] != payload2["sub"]
        assert payload1["username"] != payload2["username"]


# ════════════════════════════════════════════════════════════════
#  JWT Token Verification
# ════════════════════════════════════════════════════════════════
class TestTokenVerification:

    def test_valid_token_decodes_successfully(self):
        token = create_token(1, "testuser")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload is not None

    def test_invalid_token_raises_jwt_error(self):
        with pytest.raises(JWTError):
            jwt.decode("invalid.token.string", SECRET_KEY, algorithms=[ALGORITHM])

    def test_tampered_token_raises_jwt_error(self):
        token = create_token(1, "testuser")
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(JWTError):
            jwt.decode(tampered, SECRET_KEY, algorithms=[ALGORITHM])

    def test_wrong_secret_raises_jwt_error(self):
        token = create_token(1, "testuser")
        with pytest.raises(JWTError):
            jwt.decode(token, "wrong-secret-key", algorithms=[ALGORITHM])

    def test_expired_token_raises_jwt_error(self):
        """Manually craft a token that has already expired"""
        expired_payload = {
            "sub": "1",
            "username": "testuser",
            "exp": datetime.utcnow() - timedelta(hours=1),
        }
        expired_token = jwt.encode(expired_payload, SECRET_KEY, algorithm=ALGORITHM)
        with pytest.raises(JWTError):
            jwt.decode(expired_token, SECRET_KEY, algorithms=[ALGORITHM])


# ════════════════════════════════════════════════════════════════
#  Token Expiration Handling
# ════════════════════════════════════════════════════════════════
class TestTokenExpiration:

    def test_default_expiry_is_7_days(self):
        assert TOKEN_EXPIRE_DAYS == 7

    def test_token_not_expired_immediately(self):
        token = create_token(1, "testuser")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload is not None

    def test_token_expiry_calculation(self):
        before_create = datetime.utcnow()
        token = create_token(1, "testuser")
        after_create = datetime.utcnow()

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp_timestamp = payload["exp"]
        exp_dt = datetime.utcfromtimestamp(exp_timestamp)

        # JWT exp uses integer seconds, so allow 1s tolerance
        min_expected = before_create + timedelta(days=TOKEN_EXPIRE_DAYS) - timedelta(seconds=2)
        max_expected = after_create + timedelta(days=TOKEN_EXPIRE_DAYS, seconds=2)
        assert min_expected <= exp_dt <= max_expected


# ════════════════════════════════════════════════════════════════
#  API Key Hashing
# ════════════════════════════════════════════════════════════════
class TestAPIKeyHashing:

    def test_hash_api_key(self):
        from backend.routers.auth import hash_api_key
        key = "poa_testkey123"
        hashed = hash_api_key(key)
        assert isinstance(hashed, str)
        assert hashed != key

    def test_hash_api_key_deterministic(self):
        from backend.routers.auth import hash_api_key
        key = "poa_testkey123"
        hash1 = hash_api_key(key)
        hash2 = hash_api_key(key)
        assert hash1 == hash2  # SHA-256 is deterministic

    def test_hash_api_key_different_keys(self):
        from backend.routers.auth import hash_api_key
        hash1 = hash_api_key("key1")
        hash2 = hash_api_key("key2")
        assert hash1 != hash2

    def test_hash_api_key_sha256_length(self):
        from backend.routers.auth import hash_api_key
        hashed = hash_api_key("test")
        # SHA-256 hex digest is 64 characters
        assert len(hashed) == 64
