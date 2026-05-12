from typing import List
from mitmproxy import http
import yaml
from pathlib import Path
import json
from configparser import ConfigParser
import logging
import ruamel


class RecoderHTTP:
    """
       代理录制接口，基于 mitmproxy 库拦截获取网络请求
       将接口请求数据转换成 yaml 测试用例
    """
    def __init__(self, filter_host: List,
                 ignore_cookies=False,
                 save_base_url=False,
                 save_case_dir="cases"):
        """
           设置抓取的环境地址
        :param filter_host: 抓取的环境地址，可以是多个
        :param ignore_cookies: 是否忽略掉cookies，默认False
        :param save_base_url: 是否在 pytest.ini 保存全局base_url环境地址
        :param save_case_dir: 设置用例保存目录，默认cases
        """
        self.counter = 1
        self.filter_hosts = filter_host
        self.ignore_cookies = ignore_cookies
        self.save_base_url = save_base_url
        self.save_case_dir = save_case_dir


    def is_filter_hosts(self, url: str) -> bool:
        """筛选出符合条件的 url """
        for filter_url in self.filter_hosts:
            # 判断当前拦截的 url 地址，是否是 addons 中配置的 host
            if filter_url in url:
                return True
        return False

    def response(self, flow: http.HTTPFlow) -> None:
        """
            筛选符合条件的接口，转成 yaml 格式用例
        :param flow:
        :return:
        """
        # 需要过滤掉的类型
        filter_url_type = ['.css', '.js', '.map', '.ico', '.png', '.woff', '.map3', '.jpeg', '.jpg']
        url = flow.request.url
        # 判断 url 地址是否是过滤的类型
        if any(url_type in url for url_type in filter_url_type) is False:
            # 判断 filter_url
            if self.is_filter_hosts(url) and flow.request.scheme in ['http', 'https']:
                logging.info("=" * 40 + "录制接口，转 yaml 用例" + "=" * 40)
                self.parser_to_yaml_case(flow)
        self.counter += 1

    def parser_to_yaml_case(self, flow: http.HTTPFlow) -> None:
        """
            get请求:
              request:
                method: GET
                url: http://httpbin.org/get
              validate:
                - eq: [status_code, 200]
        :param flow:
        :return:
        """
        logging.info(f"接口地址path: {flow.request.path}")
        logging.info(f"接口地址method: {flow.request.method}")
        method = flow.request.method
        path = flow.request.path.split('?')[0]
        query = dict(flow.request.query)
        headers = dict(flow.request.headers)
        body = flow.request.text
        case_name = f"{method.lower()}{path.replace('/', '_')}"
        request_info = {}
        request_info.update(method=method)
        request_info.update(url=path)
        # 添加请求头部
        request_headers = dict()
        for key, value in headers.items():
            if str(key).lower() not in ['host', 'proxy-connection', 'content-length', 'cache-control',
                                        'accept-language', 'accept', 'user-agent', 'connection',
                                        'origin', 'referer', 'accept-encoding', 'cookie']:
                if 'multipart/form-data' not in value:
                    request_headers[key] = value
            else:
                pass
        request_info.update(headers=request_headers)
        request_cookies = {key: value for key, value in flow.request.cookies.items() if '{' not in value}
        if request_cookies and not self.ignore_cookies:
            request_info.update(cookies=request_cookies)
        if method.lower() in ['get', 'post', 'put', 'delete', 'head']:
            if query:
                request_info.update(params=query)
            content_type = headers.get('Content-Type')
            if content_type:
                if 'application/json' in content_type:
                    request_info.update(json=json.loads(body))
                elif 'application/x-www-form-urlencoded' in content_type:
                    request_info.update(data=dict(flow.request.urlencoded_form))
                elif 'multipart/form-data' in content_type:
                    form_body = [(i[0].decode(), i[1].decode()) for i in flow.request.multipart_form.items()]
                    request_info.update(files=dict(form_body))
                else:
                    logging.info(f'录制格式不支持：Content-Type: {content_type}')
        validate = list()
        status_code = flow.response.status_code
        if status_code in [301, 302]:
            validate.append({'eq': ['status_code', 200]})
        else:
            validate.append({'eq': ['status_code', status_code]})
        # 校验返回头部
        res_headers_content_type = flow.response.headers.get('Content-Type')
        if res_headers_content_type:
            validate.append({'eq': ['headers."Content-Type"', res_headers_content_type]})
        # 校验返回结果
        try:
            response_json = flow.response.json()
            for key, value in response_json.items():
                if isinstance(value, (int, float, str)):
                    if 'token' in key:
                        validate.append({'len_eq': [f'$.{key}', len(value) if isinstance(value, str) else value]})
                    else:
                        validate.append({'eq': [f'$.{key}', value]})
        except Exception as msg:
            logging.info(f'json 解析异常: {msg}')
        case_info = dict()
        case_info.update(request=request_info)
        case_info.update(validate=validate)
        yaml_format = dict()
        p = Path('./')
        if flow.request.scheme == 'http' and str(flow.request.port) == '80':
            base_url = f'{flow.request.scheme}://{flow.request.host}'
        elif flow.request.scheme == 'https' and str(flow.request.port) == '443':
            base_url = f'{flow.request.scheme}://{flow.request.host}'
        else:
            base_url = f'{flow.request.scheme}://{flow.request.host}:{flow.request.port}'
        if not self.save_base_url:
            yaml_format['config'] = {"base_url": base_url}
        else:
            self.create_path(p, base_url=base_url, folder_name=self.save_case_dir)
        yaml_format[case_name] = case_info
        case_dir = p.joinpath(self.save_case_dir)
        if not case_dir.exists():
            case_dir.mkdir()
        # 写入 yaml
        yaml_path = p.joinpath(self.save_case_dir, f'test_{case_name}.yml')
        if not yaml_path.exists():
            yaml_data = ruamel.yaml.comments.CommentedMap(yaml_format)
            # validate 校验数据写一行
            for index in range(len(yaml_data[case_name]['validate'])):
                for key, value in yaml_data[case_name]['validate'][index].items():
                    yaml_data[case_name]['validate'][index][key] = ruamel.yaml.util.load_yaml_guess_indent(str(value))[0]
            with open(yaml_path, 'w', encoding="utf-8") as fp:
                ruamel.yaml.dump(
                    yaml_data, fp, allow_unicode=True, Dumper=ruamel.yaml.RoundTripDumper
                )

    @staticmethod
    def create_path(p: Path,  base_url: str, folder_name='cases') -> None:
        """
          创建文件路径
        :param p: s
        :param base_url: s
        :param folder_name: s
        :return:
        """
        case_folder = p.joinpath(folder_name)
        if not case_folder.exists():
            case_folder.mkdir()
        ini_path = p.joinpath('pytest.ini')
        if not ini_path.exists():
            ini_path.touch()
            ini = ConfigParser()
            ini.add_section("pytest")
            ini.set("pytest", "log_cli", "true")
            ini.set("pytest", "base_url", base_url)
            ini.write(ini_path.open('w'))


# addons = [RecoderHTTP(['http://127.0.0.1'])]