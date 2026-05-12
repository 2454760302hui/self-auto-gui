import requests
import re
from requests import Response
from . import exceptions
import urllib3
from .log import log


class HttpSession(requests.Session):

    def __init__(self, base_url: str = None, timeout=10):
        super().__init__()
        self.base_url = base_url
        self.timeout = timeout

    @staticmethod
    def check_url(base_url: str, url: str) -> str:
        """ 拼接base_url 和 url 地址"""
        if re.compile(r"(http)(s?)(://)").match(url):
            return url
        elif base_url:
            if re.compile(r"(http)(s?)(://)").match(base_url):
                return f"{base_url.rstrip('/')}/{url.lstrip('/')}"
            else:
                log.error(f'{base_url} -->  base url do yo mean http:// or https://!')
                raise exceptions.ParserError("base url do yo mean http:// or https://!")
        else:
            log.error(f'{url} --> url invalid or base url missed!')
            raise exceptions.ParserError("url invalid or base url missed!")

    def send_request(self, method, url, base_url=None, **kwargs) -> Response:
        """
            发送 request 请求
        :param method: 请求方式
        :param url: url 地址
        :param base_url: 环境地址
        :param kwargs: 其它参数
        :return: Response
        """
        url = self.check_url(base_url, url) if base_url else self.check_url(self.base_url, url)
        try:
            return self.request(method, url, timeout=self.timeout, **kwargs)
        except requests.exceptions.ConnectTimeout as msg:
            log.error(f'{method} {url} --> {str(msg)}')
            raise exceptions.ConnectTimeout(msg) from None
        except urllib3.exceptions.MaxRetryError as msg:
            log.error(f'{method} {url} --> {str(msg)}')
            raise exceptions.MaxRetryError(msg) from None
        except requests.exceptions.ConnectionError as msg:
            log.error(f'{method} {url} --> {str(msg)}')
            raise exceptions.ConnectError(msg) from None
