import sys
from pathlib import Path
from configparser import ConfigParser


config_text = '''class Config:
    """多套环境的公共配置"""
    version = "v1.0"
    # 钉钉群机器人通知
    # DING_TALK = {
    #     "access_token": "****复制你的token****",
    # }


class TestConfig(Config):
    """测试环境"""
    BASE_URL = 'http://httpbin.org'
    BASE_URL2 = 'http://www.example.com'
    USERNAME = "test"


class UatConfig(Config):
    """联调环境"""
    BASE_URL = 'http://www.baidu.com'


# 环境关系映射
env = {
    "test": TestConfig,
    "uat": UatConfig
}
'''

case1_text = '''test_get1:
  name: 简单 get 请求
  request:
    method: GET
    url: /get
  validate:
    - eq: [status_code, 200]

test_get2:
-
  name: 用例也可以写的 list 下
  request:
    method: GET
    url: /get
  validate:
    - eq: [status_code, 200]
'''

case2_text = '''config:
  name: post示例
  variables:
    username: test
    password: YOUR_PASSWORD_HERE

test_post:
  name: post
  request:
    method: POST
    url: /post
    json:
      username: ${username}
      password: ${password}
  validate:
  - eq: [status_code, 200]
  - eq: [headers.Server, gunicorn/19.9.0]
  - eq: [$..username, test]
  - eq: [body.json.username, test]
'''

case3_text = '''config:
  name: 参数关联-用例a提取结果给到用例b

test_a:
  name: extract提取结果
  request:
    method: POST
    url: /post
    json:
      username: test
      password: "YOUR_PASSWORD_HERE"
  extract:
      url:  body.url
  validate:
  - eq: [status_code, 200]
  - eq: [headers.Server, gunicorn/19.9.0]
  - eq: [$..username, test]
  - eq: [body.json.username, test]

test_b:
  name: 引用上个接口返回
  request:
    method: GET
    url: http://httpbin.org/get
    headers:
      url: ${url}
  validate:
  - eq: [status_code, 200]
'''


def create_start_project(config):
    root_path = Path(config.rootpath)
    ini_path = root_path.joinpath('pytest.ini')
    # 创建 pytest.ini
    if not ini_path.exists():
        ini_path.touch()
        ini = ConfigParser()
        ini.add_section("pytest")
        ini.set("pytest", "log_cli", "true")
        ini.set("pytest", "env", "test")
        ini.write(ini_path.open('w'))  # 一定要写入才生效
        sys.stdout.write(f"create ini file: {ini_path}\n")
    config_path = root_path.joinpath('config.py')
    if not config_path.exists():
        config_path.touch()
        config_path.write_text(config_text, encoding='utf-8')
        sys.stdout.write(f"create config file: {config_path}\n")
    case_demo = root_path.joinpath('case_demo')
    if not case_demo.exists():
        case_demo.mkdir()
        sys.stdout.write(f"create folder: {case_demo}\n")
        case1 = case_demo.joinpath('test_get.yml')
        if not case1.exists():
            case1.touch()
            case1.write_text(case1_text, encoding='utf-8')
            sys.stdout.write(f"create yaml file: {case1}\n")
        case2 = case_demo.joinpath('test_post.yml')
        if not case2.exists():
            case2.touch()
            case2.write_text(case2_text, encoding='utf-8')
            sys.stdout.write(f"create yaml file: {case2}\n")
        case3 = case_demo.joinpath('test_extract.yml')
        if not case3.exists():
            case3.touch()
            case3.write_text(case3_text, encoding='utf-8')
            sys.stdout.write(f"create yaml file: {case3}\n")
