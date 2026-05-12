"""
认证处理器
使用 Selenium 登录获取 Cookie，用于认证扫描
"""
import time
from typing import Any, Dict, List, Optional

from loguru import logger

from .config import AuthConfig
from .errors import AuthError


def login_with_selenium(auth: AuthConfig) -> Dict[str, str]:
    """
    使用 Selenium 登录获取 Cookie

    Args:
        auth: 认证配置

    Returns:
        Cookie 字典 {name: value}
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
    except ImportError:
        raise AuthError.browser_not_available()

    if not auth.login_url:
        raise AuthError.login_failed("", "未配置登录 URL")

    logger.info(f"Selenium 登录: {auth.login_url}")

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        driver.get(auth.login_url)

        # 等待页面加载
        time.sleep(2)

        # 输入用户名
        if auth.username_selector and auth.username:
            username_el = driver.find_element(By.CSS_SELECTOR, auth.username_selector)
            username_el.clear()
            username_el.send_keys(auth.username)

        # 输入密码
        if auth.password_selector and auth.password:
            password_el = driver.find_element(By.CSS_SELECTOR, auth.password_selector)
            password_el.clear()
            password_el.send_keys(auth.password)

        # 点击提交
        if auth.submit_selector:
            submit_el = driver.find_element(By.CSS_SELECTOR, auth.submit_selector)
            submit_el.click()
        else:
            # 尝试按 Enter 提交
            from selenium.webdriver.common.keys import Keys
            if auth.password_selector:
                password_el = driver.find_element(By.CSS_SELECTOR, auth.password_selector)
                password_el.send_keys(Keys.RETURN)

        # 等待登录完成
        time.sleep(3)

        # 获取 Cookie
        cookies = {}
        for cookie in driver.get_cookies():
            cookies[cookie["name"]] = cookie["value"]

        if not cookies:
            raise AuthError.no_cookie(auth.login_url)

        logger.info(f"登录成功，获取 {len(cookies)} 个 Cookie")
        return cookies

    except AuthError:
        raise
    except Exception as e:
        raise AuthError.login_failed(auth.login_url, str(e))
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


def get_auth_headers(cookies: Dict[str, str]) -> Dict[str, str]:
    """将 Cookie 转为请求头"""
    cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
    return {"Cookie": cookie_str}


def login_with_requests(
    login_url: str,
    username: str = "",
    password: str = "",
    username_field: str = "username",
    password_field: str = "password",
    method: str = "post",
    extra_data: Dict[str, Any] = None,
) -> Dict[str, str]:
    """
    使用 requests 登录获取 Cookie（适用于 API 登录）

    Args:
        login_url: 登录接口 URL
        username: 用户名
        password: 密码
        username_field: 用户名字段名
        password_field: 密码字段名
        method: 请求方法
        extra_data: 额外数据

    Returns:
        Cookie 字典
    """
    import requests

    data = {username_field: username, password_field: password}
    if extra_data:
        data.update(extra_data)

    try:
        if method.lower() == "post":
            resp = requests.post(login_url, data=data, allow_redirects=True)
        else:
            resp = requests.get(login_url, params=data, allow_redirects=True)

        # 验证 HTTP 状态码
        if resp.status_code >= 400:
            raise AuthError.login_failed(
                login_url, f"HTTP {resp.status_code}: {resp.text[:200]}"
            )

        cookies = dict(resp.cookies)
        if not cookies:
            # 尝试从 Set-Cookie 头解析
            logger.warning("响应中无 Cookie，尝试从 header 解析")

        logger.info(f"requests 登录: {login_url}, 获取 {len(cookies)} 个 Cookie")
        return cookies

    except Exception as e:
        raise AuthError.login_failed(login_url, str(e))
