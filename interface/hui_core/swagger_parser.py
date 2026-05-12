import jsonpath
import yaml
import json
from pathlib import Path
import requests


class SwaggerToYaml(object):
    """
    根据 swagger.json 文件自动解析出接口，转成 yaml 用例
    """

    def __init__(self, swagger='swagger.json'):
        """swagger 参数可以是本地./swagger.json 文件
        也可以从网络 http 获取
        """
        self.current_path = Path.cwd()   # 获取当前运行文件的父一级
        self.data = {}
        self.paths = {}
        if 'http' in swagger:
            res = requests.get(swagger)
            try:
                self.data = res.json()
            except Exception as msg:
                print(f"从网络地址 {swagger} 获取 json 数据解析错误: {msg}")
        elif self.current_path.joinpath(swagger).is_file():
            # 读取本地
            with open(self.current_path.joinpath(swagger), "r", encoding='utf-8') as fp:  # noqa
                swagger_data = json.load(fp)
            self.data = swagger_data
        else:
            print("{swagger} :未找到合法的swagger.json文件")
        self.paths = self.data.get('paths', {})

    def parse_params(self, parameters):
        if parameters:
            param_type_value = {  # 收集参数信息
                "body": {},
                "query": {},
                "headers": {}
            }
            for param in parameters:
                # 根据参数类型body/query/header/path 等，收集参数的内容
                type_in = jsonpath.jsonpath(param, '$..in')
                if type_in == ["body"]:
                    properties = jsonpath.jsonpath(param, '$..properties')
                    ref = jsonpath.jsonpath(param, '$..$ref')
                    # 解析 body 参数
                    body = {}
                    if properties:
                        for key, value in properties[0].items():
                            body[key] = value['type']
                    if ref:
                        _properties_model = str(ref[0]).lstrip("#/").split('/')
                        properties_model = jsonpath.jsonpath(self.data, f'$.{".".join(_properties_model)}.properties')
                        for key, value in properties_model[0].items():
                            body[key] = value['type']
                    param_type_value["body"] = body
                elif type_in == ["query"]:
                    param_type_value["query"].update({param.get('name'): param.get('default', '')})
                elif type_in == ["header"]:
                    arg_value = param.get('default', param.get('type', ''))
                    param_type_value["headers"].update({param.get('name'): arg_value})
                else:
                    print(f"参数位 in 类型 未识别：{type_in}")
                    pass
            return param_type_value
        else:
            return {}

    def parse_json(self):
        """解析json文件，生成对应的API 信息"""
        for url_path, methods in self.paths.items():
            param_type_value = {  # 收集参数信息
                "path": {}
            }
            if 'parameters' in methods.keys():
                # 获取 path 路径参数
                for param in methods['parameters']:
                    args_value = param.get('default', param.get('type', ''))
                    args_value = 1 if args_value == 'integer' else args_value
                    param_type_value["path"].update({param.get('name'): args_value})

            for method, view in methods.items():
                # 获取 get/post/put/delete 路径参数path--parameters 跳过
                if method == "parameters":
                    continue

                tags = jsonpath.jsonpath(view, '$.tags')
                # 获取API 详细参数信息
                api_des = {
                    "module": tags[0][0] if tags else '',
                    "url": url_path,
                    "method": method,
                    "name": view.get('summary', '') if isinstance(view, dict) else '',
                    "desc": view.get('description', '') if isinstance(view, dict) else '',
                }
                parameters = view.get('parameters', {}) if isinstance(view, dict) else {}
                parameters_parser = self.parse_params(parameters)
                # 合并参数
                param_type_value.update(parameters_parser)
                api_des.update(param_type_value)
                # 转yaml
                self.api_to_yaml(api_des)

    def api_to_yaml(self, api_des: dict):
        """api 自动转 yaml 用例
        {'module': 'api/case',
        'url': '/api/case',
        'method': 'get',
        'name': '查询全部Case',
        'desc': '查询全部Case',
        'path': {},
        'body': {},
        'query': {'page': 1, 'size': 50, 'case_name': '', 'module': '', 'project': ''},
        'headers': {'X-Fields': 'string'}
        }
        """
        # 在当前目录下创建模块文件夹
        module_name = api_des.get('module', '').replace('/', '_')
        yaml_name = f"test_{api_des.get('url', '').replace('/', '_').lstrip('_')}_{api_des.get('method', '')}.yml"
        if module_name:
            module_dir = self.current_path.joinpath(module_name)
            if not module_dir.exists():
                # 如果模块文件夹不存在就创建
                module_dir.mkdir()
            yaml_file_name = str(module_dir.joinpath(yaml_name).resolve())
        else:
            # 没有模块名称，放项目根目录
            yaml_file_name = str(self.current_path.joinpath(yaml_name).resolve())

        # 写入yaml
        with open(yaml_file_name, 'w', encoding="utf-8") as fp:
            yaml_format = self.yaml_format(api_des)
            yaml.safe_dump(yaml_format, fp, indent=4,
                           default_flow_style=False,
                           encoding='utf-8',
                           allow_unicode=True,
                           sort_keys=False
                           )

    @staticmethod
    def yaml_format(api_des):
        """
        定义yaml文件输出的格式， 适用于 hui_core 插件的用例格式
        config:
          variables:
            x: 1
        get请求:
          name: GET请求示例
          sleep: ${x}
          skip: 原因-功能未实现
          request:
            method: GET
            url: http://httpbin.org/get
          validate:
            - eq: [status_code, 200]
        :return:
        """
        case_name = api_des.get('url', '').replace('/', '_').lstrip('_')+'_'+api_des.get('method', '')
        case_request = {
                "method": api_des['method'],
                "url": str(api_des['url']).replace('/{', '/${')
        }
        if api_des.get('headers'):
            case_request.update(headers=api_des['headers'])
        if api_des.get('query'):
            case_request.update(params=api_des['query'])
        if api_des.get('body'):
            case_request.update(json=api_des['body'])
        # 用例格式
        case_format = {
            "config": {
                "variables": api_des.get('path', {})
            },
            case_name: {
                "name": api_des.get('name', ''),
                "request": case_request,
                "validate": [
                    {"eq": ["status_code", 200]}
                ]
            }
        }
        return case_format


if __name__ == '__main__':
    s = SwaggerToYaml()
    s.parse_json()

