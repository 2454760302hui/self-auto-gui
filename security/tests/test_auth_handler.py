"""
auth_handler 单元测试
测试 login_with_requests, login_with_selenium, get_auth_headers
"""
import time
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from core.auth_handler import login_with_requests, login_with_selenium, get_auth_headers
from core.config import AuthConfig
from core.errors import AuthError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def auth_config():
    """返回一个带合理默认值的 AuthConfig"""
    return AuthConfig(
        enabled=True,
        login_url="https://example.com/login",
        username="admin",
        password="secret123",
        username_selector="#username",
        password_selector="#password",
        submit_selector="#submit",
        cookie_domain="example.com",
    )


@pytest.fixture
def auth_config_no_url():
    """login_url 为空的配置"""
    return AuthConfig(
        enabled=True,
        login_url="",
        username="admin",
        password="secret123",
        username_selector="#username",
        password_selector="#password",
        submit_selector="#submit",
    )


# ---------------------------------------------------------------------------
# get_auth_headers
# ---------------------------------------------------------------------------

class TestGetAuthHeaders:

    def test_single_cookie(self):
        headers = get_auth_headers({"sid": "abc"})
        assert headers == {"Cookie": "sid=abc"}

    def test_multiple_cookies(self):
        headers = get_auth_headers({"sid": "abc", "token": "xyz"})
        assert "sid=abc" in headers["Cookie"]
        assert "token=xyz" in headers["Cookie"]
        # cookies joined with "; "
        assert "; " in headers["Cookie"]

    def test_empty_cookies(self):
        headers = get_auth_headers({})
        assert headers == {"Cookie": ""}

    def test_cookie_with_special_chars(self):
        headers = get_auth_headers({"session": "a=b&c=d"})
        assert "session=a=b&c=d" in headers["Cookie"]


# ---------------------------------------------------------------------------
# login_with_requests
# ---------------------------------------------------------------------------

class TestLoginWithRequests:

    @patch("requests.post")
    def test_post_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.cookies = {"session": "abc123"}
        mock_post.return_value = mock_resp

        cookies = login_with_requests(
            "https://example.com/api/login",
            username="admin",
            password="secret",
        )
        mock_post.assert_called_once()
        assert cookies == {"session": "abc123"}

    @patch("requests.post")
    def test_post_http_error_status(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        mock_post.return_value = mock_resp

        with pytest.raises(AuthError):
            login_with_requests(
                "https://example.com/api/login",
                username="admin",
                password="wrong",
            )

    @patch("requests.post")
    def test_post_exception(self, mock_post):
        mock_post.side_effect = ConnectionError("network down")

        with pytest.raises(AuthError):
            login_with_requests(
                "https://example.com/api/login",
                username="admin",
                password="secret",
            )

    @patch("requests.get")
    def test_get_method(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.cookies = {"token": "xyz"}
        mock_get.return_value = mock_resp

        cookies = login_with_requests(
            "https://example.com/api/login",
            username="admin",
            password="secret",
            method="get",
        )
        mock_get.assert_called_once()
        assert cookies == {"token": "xyz"}

    @patch("requests.post")
    def test_extra_data_merged(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.cookies = {}
        mock_post.return_value = mock_resp

        login_with_requests(
            "https://example.com/api/login",
            username="admin",
            password="secret",
            extra_data={"csrf_token": "abc", "remember": "true"},
        )
        call_args = mock_post.call_args
        data = call_args[1]["data"]
        assert "csrf_token" in data
        assert "remember" in data
        assert "username" in data
        assert "password" in data

    @patch("requests.post")
    def test_custom_field_names(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.cookies = {"sid": "val"}
        mock_post.return_value = mock_resp

        login_with_requests(
            "https://example.com/api/login",
            username="admin",
            password="secret",
            username_field="email",
            password_field="passwd",
        )
        call_args = mock_post.call_args
        data = call_args[1]["data"]
        assert "email" in data
        assert "passwd" in data

    @patch("requests.post")
    def test_no_cookies_returns_empty_dict(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.cookies = {}
        mock_post.return_value = mock_resp

        cookies = login_with_requests(
            "https://example.com/api/login",
            username="admin",
            password="secret",
        )
        assert cookies == {}

    @patch("requests.post")
    def test_http_500_raises(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_post.return_value = mock_resp

        with pytest.raises(AuthError):
            login_with_requests(
                "https://example.com/api/login",
                username="admin",
                password="secret",
            )

    @patch("requests.post")
    def test_status_code_399_ok(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 302
        mock_resp.cookies = {"redirect_cookie": "yes"}
        mock_post.return_value = mock_resp

        cookies = login_with_requests(
            "https://example.com/api/login",
                username="admin",
                password="secret",
            )
        assert cookies == {"redirect_cookie": "yes"}


# ---------------------------------------------------------------------------
# login_with_selenium
# ---------------------------------------------------------------------------

class TestLoginWithSelenium:

    @patch("core.auth_handler.time.sleep")
    def test_import_error_raises(self, mock_sleep):
        """selenium 未安装时应抛出 AuthError"""
        with patch.dict("sys.modules", {"selenium": None}):
            with pytest.raises(AuthError) as exc_info:
                login_with_selenium(AuthConfig())
            assert "Selenium" in str(exc_info.value) or "不可用" in str(exc_info.value) or "browser" in str(exc_info.value).lower()

    def test_login_url_missing_raises(self):
        """login_url 为空时应抛出 AuthError"""
        with patch.dict("sys.modules", {
            "selenium": MagicMock(),
            "selenium.webdriver": MagicMock(),
            "selenium.webdriver.chrome.options": MagicMock(),
            "selenium.webdriver.common.by": MagicMock(),
            "selenium.webdriver.support.ui": MagicMock(),
            "selenium.webdriver.support": MagicMock(),
            "selenium.webdriver.common.keys": MagicMock(),
        }):
            cfg = AuthConfig(login_url="")
            with pytest.raises(AuthError) as exc_info:
                login_with_selenium(cfg)
            assert "URL" in str(exc_info.value) or "未配置" in str(exc_info.value) or "登录" in str(exc_info.value)

    @patch("core.auth_handler.time.sleep")
    def test_success_path(self, mock_sleep, auth_config):
        mock_driver = MagicMock()
        mock_driver.get_cookies.return_value = [
            {"name": "session", "value": "sess123"},
            {"name": "token", "value": "tok456"},
        ]

        # Mock selenium imports
        mock_selenium = MagicMock()
        mock_selenium.webdriver.Chrome.return_value = mock_driver
        mock_options_cls = MagicMock()
        mock_selenium.webdriver.chrome.options.Options.return_value = MagicMock()
        mock_selenium.webdriver.common.by.By.CSS_SELECTOR = "css selector"
        mock_selenium.webdriver.support.ui.WebDriverWait = MagicMock()
        mock_selenium.webdriver.support.expected_conditions = MagicMock()

        with patch.dict("sys.modules", {
            "selenium": mock_selenium,
            "selenium.webdriver": mock_selenium.webdriver,
            "selenium.webdriver.chrome": mock_selenium.webdriver.chrome,
            "selenium.webdriver.chrome.options": mock_selenium.webdriver.chrome.options,
            "selenium.webdriver.common.by": mock_selenium.webdriver.common.by,
            "selenium.webdriver.support": mock_selenium.webdriver.support,
            "selenium.webdriver.support.ui": mock_selenium.webdriver.support.ui,
            "selenium.webdriver.common.keys": MagicMock(),
        }):
            cookies = login_with_selenium(auth_config)

        assert cookies == {"session": "sess123", "token": "tok456"}
        mock_driver.quit.assert_called_once()

    @patch("core.auth_handler.time.sleep")
    def test_no_cookies_raises_auth_error(self, mock_sleep, auth_config):
        mock_driver = MagicMock()
        mock_driver.get_cookies.return_value = []

        mock_selenium = MagicMock()
        mock_selenium.webdriver.Chrome.return_value = mock_driver
        mock_selenium.webdriver.chrome.options.Options.return_value = MagicMock()
        mock_selenium.webdriver.common.by.By.CSS_SELECTOR = "css selector"

        with patch.dict("sys.modules", {
            "selenium": mock_selenium,
            "selenium.webdriver": mock_selenium.webdriver,
            "selenium.webdriver.chrome": mock_selenium.webdriver.chrome,
            "selenium.webdriver.chrome.options": mock_selenium.webdriver.chrome.options,
            "selenium.webdriver.common.by": mock_selenium.webdriver.common.by,
            "selenium.webdriver.support": mock_selenium.webdriver.support,
            "selenium.webdriver.support.ui": mock_selenium.webdriver.support.ui,
            "selenium.webdriver.common.keys": MagicMock(),
        }):
            with pytest.raises(AuthError) as exc_info:
                login_with_selenium(auth_config)
            assert "Cookie" in str(exc_info.value) or "cookie" in str(exc_info.value).lower()

        mock_driver.quit.assert_called_once()

    @patch("core.auth_handler.time.sleep")
    def test_webdriver_exception_raises(self, mock_sleep, auth_config):
        mock_selenium = MagicMock()
        mock_selenium.webdriver.Chrome.side_effect = RuntimeError("Chrome not found")
        mock_selenium.webdriver.chrome.options.Options.return_value = MagicMock()

        with patch.dict("sys.modules", {
            "selenium": mock_selenium,
            "selenium.webdriver": mock_selenium.webdriver,
            "selenium.webdriver.chrome": mock_selenium.webdriver.chrome,
            "selenium.webdriver.chrome.options": mock_selenium.webdriver.chrome.options,
            "selenium.webdriver.common.by": mock_selenium.webdriver.common.by,
            "selenium.webdriver.support": mock_selenium.webdriver.support,
            "selenium.webdriver.support.ui": mock_selenium.webdriver.support.ui,
            "selenium.webdriver.common.keys": MagicMock(),
        }):
            with pytest.raises(AuthError):
                login_with_selenium(auth_config)

    @patch("core.auth_handler.time.sleep")
    def test_no_submit_selector_uses_enter(self, mock_sleep):
        """当 submit_selector 为空时，应尝试按 Enter 提交"""
        cfg = AuthConfig(
            login_url="https://example.com/login",
            username="admin",
            password="secret",
            username_selector="#user",
            password_selector="#pass",
            submit_selector="",  # empty -> use Enter
        )

        mock_driver = MagicMock()
        mock_driver.get_cookies.return_value = [
            {"name": "sid", "value": "val"},
        ]

        mock_selenium = MagicMock()
        mock_selenium.webdriver.Chrome.return_value = mock_driver
        mock_selenium.webdriver.chrome.options.Options.return_value = MagicMock()

        mock_by = MagicMock()
        mock_by.CSS_SELECTOR = "css selector"
        mock_selenium.webdriver.common.by.By = mock_by

        mock_keys = MagicMock()
        mock_keys.RETURN = "\n"
        mock_selenium.webdriver.common.keys.Keys = mock_keys

        with patch.dict("sys.modules", {
            "selenium": mock_selenium,
            "selenium.webdriver": mock_selenium.webdriver,
            "selenium.webdriver.chrome": mock_selenium.webdriver.chrome,
            "selenium.webdriver.chrome.options": mock_selenium.webdriver.chrome.options,
            "selenium.webdriver.common.by": mock_selenium.webdriver.common.by,
            "selenium.webdriver.support": mock_selenium.webdriver.support,
            "selenium.webdriver.support.ui": mock_selenium.webdriver.support.ui,
            "selenium.webdriver.common.keys": mock_keys,
        }):
            cookies = login_with_selenium(cfg)

        assert cookies == {"sid": "val"}

    @patch("core.auth_handler.time.sleep")
    def test_driver_quit_called_on_error(self, mock_sleep, auth_config):
        """即使发生异常，driver.quit() 也应被调用"""
        mock_driver = MagicMock()
        mock_driver.get.side_effect = RuntimeError("page load failed")

        mock_selenium = MagicMock()
        mock_selenium.webdriver.Chrome.return_value = mock_driver
        mock_selenium.webdriver.chrome.options.Options.return_value = MagicMock()

        with patch.dict("sys.modules", {
            "selenium": mock_selenium,
            "selenium.webdriver": mock_selenium.webdriver,
            "selenium.webdriver.chrome": mock_selenium.webdriver.chrome,
            "selenium.webdriver.chrome.options": mock_selenium.webdriver.chrome.options,
            "selenium.webdriver.common.by": mock_selenium.webdriver.common.by,
            "selenium.webdriver.support": mock_selenium.webdriver.support,
            "selenium.webdriver.support.ui": mock_selenium.webdriver.support.ui,
            "selenium.webdriver.common.keys": MagicMock(),
        }):
            with pytest.raises(AuthError):
                login_with_selenium(auth_config)

        mock_driver.quit.assert_called_once()

    @patch("core.auth_handler.time.sleep")
    def test_auth_error_not_wrapped(self, mock_sleep, auth_config):
        """AuthError 应直接抛出，不被包装"""
        mock_driver = MagicMock()
        mock_driver.get_cookies.return_value = []  # no cookies -> AuthError

        mock_selenium = MagicMock()
        mock_selenium.webdriver.Chrome.return_value = mock_driver
        mock_selenium.webdriver.chrome.options.Options.return_value = MagicMock()

        with patch.dict("sys.modules", {
            "selenium": mock_selenium,
            "selenium.webdriver": mock_selenium.webdriver,
            "selenium.webdriver.chrome": mock_selenium.webdriver.chrome,
            "selenium.webdriver.chrome.options": mock_selenium.webdriver.chrome.options,
            "selenium.webdriver.common.by": mock_selenium.webdriver.common.by,
            "selenium.webdriver.support": mock_selenium.webdriver.support,
            "selenium.webdriver.support.ui": mock_selenium.webdriver.support.ui,
            "selenium.webdriver.common.keys": MagicMock(),
        }):
            with pytest.raises(AuthError) as exc_info:
                login_with_selenium(auth_config)
            # Should be the no_cookie error, not wrapped in another AuthError
            assert "Cookie" in exc_info.value.message or "cookie" in exc_info.value.message.lower()
