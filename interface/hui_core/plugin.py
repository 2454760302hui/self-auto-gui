import types
import yaml
from pathlib import Path
from _pytest.python import Module
import pytest
from requests.adapters import HTTPAdapter
from . import http_session
from . import runner
from .log import set_log_format, log
from .report_notify import ding_ding_notify, fei_shu_notify, wecom_notify
from .create_funtion import import_from_file
import os
import platform
import time
from . import g  # 全局 g 对象，获取项目配置
from .start_project import create_start_project
from .db import connect_redis


@pytest.fixture(scope="session")
def requests_session(request):
    """全局session 全部用例仅执行一次"""
    s = http_session.HttpSession()
    # max_retries=2 重试2次
    s.mount('http://', HTTPAdapter(max_retries=2))
    s.mount('https://', HTTPAdapter(max_retries=2))
    proxies_ip = request.config.getoption("--proxies-ip") or request.config.getini("proxies_ip")
    if proxies_ip:
        # 添加全局代理
        s.proxies = {
            "http": f"http://{proxies_ip}",
            "https": f"https://{proxies_ip}"
        }
    # 添加全局base_url
    s.base_url = request.config.option.base_url
    yield s
    s.close()


@pytest.fixture()
def requests_function(request):
    """用例级别 session， 每个用例都会执行一次"""
    s = http_session.HttpSession()
    # max_retries=2 重试2次
    s.mount('http://', HTTPAdapter(max_retries=2))
    s.mount('https://', HTTPAdapter(max_retries=2))
    proxies_ip = request.config.getoption("--proxies-ip") or request.config.getini("proxies_ip")
    if proxies_ip:
        # 添加全局代理
        s.proxies = {
            "http": f"http://{proxies_ip}",
            "https": f"https://{proxies_ip}"
        }
    # 添加全局base_url
    s.base_url = request.config.option.base_url
    yield s
    s.close()


@pytest.fixture(scope="module")
def requests_module(request):
    """模块级别 session， 每个模块仅执行一次"""
    s = http_session.HttpSession()
    # max_retries=2 重试2次
    s.mount('http://', HTTPAdapter(max_retries=2))
    s.mount('https://', HTTPAdapter(max_retries=2))
    proxies_ip = request.config.getoption("--proxies-ip") or request.config.getini("proxies_ip")
    if proxies_ip:
        # 添加全局代理
        s.proxies = {
            "http": f"http://{proxies_ip}",
            "https": f"https://{proxies_ip}"
        }
    # 添加全局base_url
    s.base_url = request.config.option.base_url
    yield s
    s.close()


@pytest.fixture(scope="session", autouse=True)
def environ(request):
    """Return a env object"""
    config = request.config
    env_name = config.getoption("--env") or config.getini("env")
    if env_name is not None:
        return g.get('env')


def pytest_collect_file(file_path: Path, parent):  # noqa
    """
        收集测试用例：
        1.测试文件以.yml 或 .yaml 后缀的文件
        2.并且以 test 开头或者 test 结尾
    """
    if file_path.suffix in [".yml", ".yaml"] and (file_path.name.startswith("test") or file_path.name.endswith("test")):
        py_module = Module.from_parent(parent, path=file_path)
        # 动态创建 module
        module = types.ModuleType(file_path.stem)
        # 解析 yaml 内容
        raw_dict = yaml.safe_load(file_path.open(encoding='utf-8'))
        if not raw_dict:
            return
        # 用例名称test_开头
        run = runner.RunYaml(raw_dict, module, g)
        run.run()  # 执行用例
        # 重写属性
        py_module._getobj = lambda: module  # noqa
        return py_module


def pytest_generate_tests(metafunc):  # noqa
    """测试用例参数化功能实现
    :param metafunc:共有五个属性值
         metafunc.fixturenames:参数化收集时的参数名称
         metafunc.module:使用参数名称进行参数化的测试用例所在的模块d对象
         metafunc.config:测试用例会话
         metafunc.function:测试用例对象,即函数或方法对象
         metafunc.cls: 测试用例所属的类的类对象
    :return: none
    """
    # config 中对module 模块参数化
    if hasattr(metafunc.module, 'module_params_data'):
        module_params_fixtures = getattr(metafunc.module, 'module_params_fixtures')
        module_params_data = getattr(metafunc.module, 'module_params_data')
        if module_params_data:
            if isinstance(module_params_data, list):
                if isinstance(module_params_data[0], list):
                    module_params_len = len(module_params_data[0])
                elif isinstance(module_params_data[0], dict):
                    module_params_len = len(module_params_data[0].keys())
                else:
                    module_params_len = 1
                module_params_args = module_params_fixtures[-module_params_len:]
                metafunc.parametrize(','.join(module_params_args),
                                     module_params_data,
                                     ids=None,
                                     scope="module")
            # -----v1.3.8 兼容name: ["user1", "user2"] 格式参数化--------
            if isinstance(module_params_data, dict):
                for key, value in module_params_data.items():
                    module_params_args = key.replace('-', ',')
                    module_params_data = [value] if isinstance(value, str) else value
                    metafunc.parametrize(module_params_args,
                                         module_params_data,
                                         ids=None,
                                         scope="module")
            # -----      兼容name: ["user1", "user2"] 格式参数化  end  --------

    # case 用例参数化
    if hasattr(metafunc.module, f'{metafunc.function.__qualname__}_params_data'):
        params_data = getattr(metafunc.module, f'{metafunc.function.__qualname__}_params_data')
        params_fixtures = getattr(metafunc.module, f'{metafunc.function.__qualname__}_params_fixtures')
        if isinstance(params_data, list):
            if isinstance(params_data[0], list):
                params_len = len(params_data[0])
            elif isinstance(params_data[0], dict):
                params_len = len(params_data[0].keys())
            else:
                params_len = 1
            params_args = params_fixtures[-params_len:]
            metafunc.parametrize(
                ','.join(params_args),
                params_data,
                scope="function"
            )
        # -----v1.3.8 兼容name: ["user1", "user2"] 格式参数化--------
        if isinstance(params_data, dict):
            for key, value in params_data.items():
                params_args = key.replace('-', ',')
                params_data = [value] if isinstance(value, str) else value
                metafunc.parametrize(params_args,
                                     params_data,
                                     ids=None,
                                     scope="function")
        # -----      兼容name: ["user1", "user2"] 格式参数化  end  --------


def pytest_addoption(parser):   # noqa
    # run env
    parser.addini('env', default=None, help='run environment by test or uat ...')
    parser.addoption(
        "--env", action="store", default=None, help="run environment by test or uat ..."
    )
    # base url
    if 'base_url' not in parser._ininames:
        parser.addini("base_url", help="base url for the api test.")
        parser.addoption(
            "--base-url",
            metavar="url",
            default=os.getenv("PYTEST_BASE_URL", None),
            help="base url for the api test.",
        )
    # proxies_ip
    parser.addini("proxies_ip", default=None, help="proxies_ip for the  test.")
    parser.addoption(
        "--proxies-ip",
        action="store", default=None,
        help="proxies_ip for the  test.",
    )
    # 创建 demo
    parser.addoption(
        "--start-project", action="store_true", help="start demo project"
    )


def pytest_configure(config):  # noqa
    # 配置日志文件和格式
    g['root_path'] = config.rootpath  # 项目根路径
    run_current_time = set_log_format(config)
    g['run_current_time'] = run_current_time
    config.addinivalue_line(
        "filterwarnings", "ignore::DeprecationWarning"
    )
    config.addinivalue_line(
        "filterwarnings", "ignore::urllib3.exceptions.InsecureRequestWarning"
    )
    # 加载 项目 config 文件配置
    config_path = Path(config.rootdir).joinpath('config.py')
    if config_path.exists():
        # 如果有配置文件，加载当前运行环境的配置
        run_env_name = config.getoption('--env') or config.getini('env')
        if run_env_name:
            config_module = import_from_file(config_path)
            # config_module = __import__("config", globals(), locals(), [])
            if hasattr(config_module, 'env'):
                g["env"] = config_module.env.get(run_env_name)  # noqa
                g["env_name"] = run_env_name
    if g.get('env'):
        # 获取配置环境的 BASE_URL
        _base_url = g["env"].BASE_URL if hasattr(g.get('env'), 'BASE_URL') else None
        # 设置 env 环境属性
        config.env = g.get('env')
    else:
        _base_url = None
        config.env = None
    # base_url
    base_url = config.getoption("--base-url") or config.getini("base_url") or _base_url
    g["base_url"] = base_url
    if base_url is not None:
        config.option.base_url = base_url
        if hasattr(config, "_metadata"):
            config._metadata["base_url"] = base_url  # noqa
    # v1.4.1 添加 redis 连接对象到 g
    if g.get('env'):
        g.update(connect_redis(g.get('env')))
    # 获取 allure 报告的路径
    allure_dir = config.getoption('--alluredir')  # noqa
    if allure_dir:
        allure_report_path = Path(os.getcwd()).joinpath(allure_dir)
        if not allure_report_path.exists():
            allure_report_path.mkdir()
        allure_report_env = allure_report_path.joinpath('environment.properties')
        if not allure_report_env.exists():
            allure_report_env.touch()  # 创建
            # 写入环境信息
            root_dir = str(config.rootdir).replace("\\", "\\\\")
            allure_report_env.write_text(f'system={platform.system()}\n'
                                         f'systemVersion={platform.version()}\n'
                                         f'pythonVersion={platform.python_version()}\n'
                                         f'pytestVersion={pytest.__version__}\n'
                                         f'rootDir={root_dir}\n')


def pytest_terminal_summary(terminalreporter, exitstatus, config): # noqa
    """收集测试结果"""
    total = terminalreporter._numcollected  # noqa
    status = {
        0: "pass",
        1: "failed",
        2: "pytest 执行过程被中断",
        3: "pytest 内部错误",
        4: "pytest 用法错误",
        5: "没有收集到测试用例"
    }
    if exitstatus in [0, 1]:
        passed = len([i for i in terminalreporter.stats.get('passed', []) if i.when != 'teardown'])
        failed = len([i for i in terminalreporter.stats.get('failed', []) if i.when != 'teardown'])
        error = len([i for i in terminalreporter.stats.get('error', []) if i.when != 'teardown'])
        skipped = len([i for i in terminalreporter.stats.get('skipped', []) if i.when != 'teardown'])
        if terminalreporter._numcollected- skipped == 0:
            successful = 0
        else:
            successful = len(terminalreporter.stats.get('passed', [])) / (terminalreporter._numcollected- skipped) * 100    # noqa
        duration = time.time() - terminalreporter._sessionstarttime  # noqa
        markdown_text = f"""## 执行报告: 
- 运行环境: {g.get('env_name')} 
- 运行base_url: {g.get('base_url')} 
- 持续时间: {duration: .2f} 秒 

## 本次运行结果:
- 总用例数: {total} 
- 通过用例：{passed} 
- 跳过用例：{skipped} 
- 失败用例： {failed} 
- 异常用例： {error} 
- 通过率： {successful: .2f} % 
"""
        # 收集失败/异常用例列表
        failed_items = [i.nodeid for i in terminalreporter.stats.get('failed', []) if i.when != 'teardown']
        error_items  = [i.nodeid for i in terminalreporter.stats.get('error',  []) if i.when != 'teardown']
        all_failed   = failed_items + error_items
        if all_failed:
            fail_list = '\n'.join(f'  - {n}' for n in all_failed[:10])  # 最多展示10条
            more = f'\n  ... 共 {len(all_failed)} 条' if len(all_failed) > 10 else ''
            markdown_text += f'\n## 失败用例:\n{fail_list}{more}\n'
        if g.get('env'):
            if hasattr(g["env"], 'DING_TALK'):
                ding_text = markdown_text.replace('## 本次运行结果:', f'## 本次运行结果: {status.get(exitstatus)} ')
                ding_talk = g["env"].DING_TALK
                if ding_talk.get('text'):
                    ding_talk['text'] = ding_text + ding_talk['text']
                else:
                    ding_talk['text'] = ding_text
                ding_ding_notify(**ding_talk)
            if hasattr(g["env"], 'FEI_SHU'):
                color = 'green' if exitstatus == 0 else 'red'
                fei_shu_text = markdown_text.replace('## 执行报告:', '** 执行报告: ** ')
                fei_shu_text = fei_shu_text.replace(
                    '## 本次运行结果:',
                    f'** 本次运行结果: <font color="{color}">{status.get(exitstatus)}</font> **')
                fei_shu = g["env"].FEI_SHU
                if fei_shu.get('text'):
                    fei_shu['text'] = fei_shu_text+fei_shu['text']
                else:
                    fei_shu['text'] = fei_shu_text
                # 根据运行结果设置标题背景色
                fei_shu['color'] = color
                fei_shu_res = fei_shu_notify(**fei_shu)
                log.info(f"飞书通知结果: {fei_shu_res}")
            if hasattr(g["env"], 'WE_COM'):
                we_text = markdown_text.replace('## 本次运行结果:', f'## 本次运行结果: {status.get(exitstatus)} ')
                we_com = g["env"].WE_COM
                if we_com.get('text'):
                    we_com['text'] = we_text + we_com['text']
                else:
                    we_com['text'] = we_text
                res = wecom_notify(**we_com)
                log.info(f"企业微信通知结果: {res.text}")
    else:
        log.error(f"用例执行异常，失败原因: {status.get(exitstatus)}")


def pytest_cmdline_main(config):
    """`--start-project` 命令, 快速创建项目 demo 结构"""
    if config.option.start_project:
        create_start_project(config)
        return 0


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    """仅保存用例失败的信息和日志记录"""
    current_time = g.get('run_current_time')
    root_path: Path = g.get('root_path')
    log_error = root_path.joinpath('logs', f'{current_time}_error.log')
    out = yield  # 钩子函数的调用结果
    res = out.get_result()   # 获取用例执行结果
    if res.when == "call" and res.outcome not in ["passed", "skipped"]:
        log_info = ''
        for i in res.sections:
            _log = ''.join(i)
            log_info += _log

        text = f"""{'*'*25} {res.nodeid} {'*'*25}
测试结果 outcome：{res.outcome}   
用例耗时 duration：{res.duration}
异常 exception：{call.excinfo}
exception详细日志：{res.longrepr}
{log_info}\n\n
"""     # 用例失败，写入error.log
        with open(f'{log_error.resolve()}', 'a+', encoding="utf-8") as fp:
            fp.write(text)
