from . import create_funtion
import ast
import operator
import types
from inspect import Parameter
from . import validate
from . import extract
from . import hui_builtins
from . import render_template_obj
from . import exceptions
import copy
import yaml
from pathlib import Path
import inspect
import allure
from .log import log
from .db import ConnectMysql
import mimetypes
from requests_toolbelt import MultipartEncoder
import time
import json
import pytest
import re
from websocket import create_connection


# ── 安全表达式解析器 ──────────────────────────────────────────────
_SAFE_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.Mod: operator.mod, ast.Pow: operator.pow,
    ast.Eq: operator.eq, ast.NotEq: operator.ne,
    ast.Lt: operator.lt, ast.LtE: operator.le,
    ast.Gt: operator.gt, ast.GtE: operator.ge,
    ast.And: lambda a, b: a and b,
    ast.Or: lambda a, b: a or b,
    ast.USub: operator.neg, ast.Not: operator.not_,
    ast.In: lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
    ast.Is: operator.is_, ast.IsNot: operator.is_not,
}


def _safe_eval(expr_str, context=None):
    """安全表达式求值 — 只允许字面量和比较/算术运算，禁止函数调用和属性访问"""
    node = ast.parse(expr_str, mode='eval').body

    def _resolve(n):
        if isinstance(n, ast.Constant):
            return n.value
        if isinstance(n, ast.Name):
            if context and n.id in context:
                return context[n.id]
            raise NameError(n.id)
        if isinstance(n, ast.UnaryOp):
            return _SAFE_OPS[type(n.op)](_resolve(n.operand))
        if isinstance(n, ast.BinOp):
            return _SAFE_OPS[type(n.op)](_resolve(n.left), _resolve(n.right))
        if isinstance(n, ast.BoolOp):
            result = _resolve(n.values[0])
            for v in n.values[1:]:
                result = _SAFE_OPS[type(n.op)](result, _resolve(v))
            return result
        if isinstance(n, ast.Compare):
            left = _resolve(n.left)
            for op, comp in zip(n.ops, n.comparators):
                left = _SAFE_OPS[type(op)](left, _resolve(comp))
            return left
        if isinstance(n, ast.IfExp):
            return _resolve(n.body) if _resolve(n.test) else _resolve(n.orelse)
        raise ValueError(f"unsupported expression: {ast.dump(n)}")

    return _resolve(node)


class RunYaml(object):
    """运行 yaml 用例"""

    def __init__(self, raw: dict, module: types.ModuleType, g: dict):
        self.raw = raw
        self.module = module
        self.module_variable = {}
        self.context = {}
        self.hooks = {}
        self.g = g

    # ─────────────────────────────────────────────────────────────
    # 主入口
    # ─────────────────────────────────────────────────────────────
    def run(self):
        if not self.raw.get('config'):
            self.raw['config'] = {}

        cfg = self.raw['config']
        base_url          = cfg.get('base_url', None)
        config_variables  = cfg.get('variables', {})
        config_fixtures   = cfg.get('fixtures', [])
        config_params     = cfg.get('parameters', [])
        config_hooks      = cfg.get('hooks', {})
        config_exports    = cfg.get('export', [])
        config_allure     = cfg.get('allure', {})
        # ── 新增：全局 headers / setup / teardown ──
        config_headers    = cfg.get('headers', {})
        config_setup      = cfg.get('setup', [])
        config_teardown   = cfg.get('teardown', [])

        if not isinstance(config_exports, list):
            config_exports = []
            log.error("export must be type of list")

        # 初始化上下文
        self.context.update(__builtins__)           # noqa
        self.context.update(hui_builtins.__dict__)
        db_obj = self.execute_mysql()
        self.context.update(**self.g)
        self.context.update(**db_obj)
        self.module_variable = render_template_obj.rend_template_any(
            config_variables, **self.context)
        if isinstance(self.module_variable, dict):
            self.context.update(self.module_variable)

        config_params    = render_template_obj.rend_template_any(config_params,   **self.context)
        config_fixtures  = render_template_obj.rend_template_any(config_fixtures, **self.context)
        config_fixtures, config_params = self.parameters_date(config_fixtures, config_params)

        if config_fixtures:
            setattr(self.module, 'module_params_data',     config_params)
            setattr(self.module, 'module_params_fixtures', config_fixtures)

        # mark
        case = {}
        config_mark = cfg.get('mark')
        if isinstance(config_mark, str):
            config_mark = [m.strip() for m in config_mark.split(',')]
        elif isinstance(config_mark, int):
            config_mark = [str(config_mark)]
        if config_mark:
            pytest_m = [
                pytest.Mark(
                    name=re.sub(r'\((.+)\)', '', mn),
                    args=(re.sub(r'.+\(', '', mn).rstrip(')'),),
                    kwargs={})
                for mn in config_mark
            ]
            setattr(self.module, 'pytestmark', pytest_m)

        # ── 遍历用例 ──
        for case_name, case_value in self.raw.items():
            case_fixtures = []
            case_params   = []
            case_mark     = []
            if case_name == 'config':
                continue
            if not str(case_name).startswith('test'):
                case_name = 'test_' + str(case_name)
            case[case_name] = case_value if isinstance(case_value, list) else [case_value]

            if len(case[case_name]) < 1:
                log.debug('test case not item to run !')
            else:
                first = case[case_name][0]
                if 'mark' in first:
                    case_mark = first.get('mark', [])
                    if isinstance(case_mark, str):
                        case_mark = [m.strip() for m in str(case_mark).split(',')]
                    elif isinstance(case_mark, int):
                        case_mark = [str(case_mark)]
                if 'fixtures' in first:
                    case_fixtures = render_template_obj.rend_template_any(
                        first.get('fixtures', []), **self.context)
                if 'parameters' in first:
                    case_params = render_template_obj.rend_template_any(
                        first.get('parameters', []), **self.context)
                case_fixtures, case_params = self.parameters_date(case_fixtures, case_params)
                if case_params:
                    setattr(self.module, f'{case_name}_params_data',     case_params)
                    setattr(self.module, f'{case_name}_params_fixtures', case_fixtures)
                if 'allure' not in first:
                    first['allure'] = {}

            # ── 用例执行体（闭包） ──
            def execute_yaml_case(args,
                                  _case_name=case_name,
                                  _base_url=base_url,
                                  _config_hooks=config_hooks,
                                  _config_exports=config_exports,
                                  _config_allure=config_allure,
                                  _config_headers=config_headers,
                                  _config_setup=config_setup,
                                  _config_teardown=config_teardown):

                log.info(f'执行文件-> {self.module.__name__}.yml')
                log.info(f'base_url-> {_base_url or args.get("request").config.option.base_url}')
                log.info(f'config variables-> {self.module_variable}')
                call_function_name = inspect.getframeinfo(inspect.currentframe().f_back)[2]
                log.info(f'运行用例-> {call_function_name}')

                self.context.update(args)
                request_config = args.get('request').config
                if not hasattr(request_config, 'export'):
                    request_config.export = {}
                self.context.update(request_config.export)
                case_exports = []
                self.context.update(self.module_variable)

                # ── 全局 headers 注入到 session ──
                if _config_headers:
                    rendered_headers = render_template_obj.rend_template_any(
                        copy.deepcopy(_config_headers), **self.context)
                    session = (args.get('requests_function')
                               or args.get('requests_module')
                               or args.get('requests_session'))
                    if session:
                        session.headers.update(rendered_headers)
                        log.info(f'全局 headers 注入-> {rendered_headers}')

                # ── 获取用例级 retry 次数 ──
                retry_count = 1
                if case[call_function_name]:
                    retry_count = case[call_function_name][0].get('retry', 1)
                    try:
                        retry_count = int(retry_count)
                    except (TypeError, ValueError):
                        retry_count = 1

                # ── setup ──
                if _config_setup:
                    log.info('执行 setup 步骤')
                    self._run_steps(_config_setup, args, _base_url,
                                    _config_hooks, self.context.copy())

                # ── 主体（含重试） ──
                last_exc = None
                for attempt in range(1, retry_count + 1):
                    try:
                        self._run_steps(
                            case[call_function_name], args, _base_url,
                            _config_hooks, self.context.copy(),
                            config_allure=_config_allure,
                            case_exports=case_exports,
                        )
                        last_exc = None
                        break
                    except Exception as e:
                        last_exc = e
                        if attempt < retry_count:
                            log.warning(f'用例 {call_function_name} 第 {attempt} 次失败，重试中...')
                            time.sleep(0.5)
                        else:
                            log.error(f'用例 {call_function_name} 重试 {retry_count} 次后仍失败')

                # ── teardown（无论成败都执行） ──
                if _config_teardown:
                    log.info('执行 teardown 步骤')
                    try:
                        self._run_steps(_config_teardown, args, _base_url,
                                        _config_hooks, self.context.copy())
                    except Exception as te:
                        log.error(f'teardown 执行异常: {te}')

                if last_exc:
                    raise last_exc

                # ── export ──
                for export_key in _config_exports:
                    request_config.export[export_key] = self.context.get(export_key)
                for export_key in case_exports:
                    request_config.export[export_key] = self.context.get(export_key)
                if request_config.export:
                    log.info(f'export 导出全局变量：{request_config.export}')

            fun_fixtures = list(config_fixtures)
            for fixt in case_fixtures:
                if fixt not in fun_fixtures:
                    fun_fixtures.append(fixt)

            f = create_funtion.create_function_from_parameters(
                func=execute_yaml_case,
                parameters=self.function_parameters(fun_fixtures),
                documentation=case_name,
                func_name=case_name,
                func_filename=f'{self.module.__name__}.py',
            )
            if case_mark:
                f.pytestmark = [
                    pytest.Mark(
                        name=re.sub(r'\((.+)\)', '', mn),
                        args=(re.sub(r'.+\(', '', mn).rstrip(')'),),
                        kwargs={})
                    for mn in case_mark
                ]
            setattr(self.module, str(case_name), f)

    # ─────────────────────────────────────────────────────────────
    # 步骤执行（抽取为独立方法，供主体/setup/teardown 复用）
    # ─────────────────────────────────────────────────────────────
    def _run_steps(self, steps, args, base_url, config_hooks,
                   step_ctx, config_allure=None, case_exports=None):
        """执行一组步骤列表"""
        if config_allure is None:
            config_allure = {}
        if case_exports is None:
            case_exports = []

        ws = None
        for step in steps:
            response    = None
            api_validate = []
            step_context = step_ctx.copy()

            step_name = step.get('name')
            if step_name:
                with allure.step(step_name):
                    pass

            if 'validate' not in step:
                step['validate'] = []

            for item, value in step.items():
                if item == 'name':
                    pass

                elif item == 'retry':
                    pass  # 已在外层处理

                elif item == 'ws':
                    value = render_template_obj.rend_template_any(value, **step_context)
                    ws_base = base_url or args.get('request').config.option.base_url
                    if ws_base and 'ws' in ws_base:
                        ws_url = value.get('url', '')
                        if not (ws_url.startswith('ws://') or ws_url.startswith('wss://')):
                            value['url'] = f"{ws_base.rstrip('/')}/{ws_url.lstrip('/')}"
                    ws = create_connection(**value)
                    log.info(f'创建 websocket 链接: {value.get("url")}')

                elif item == 'send':
                    value = render_template_obj.rend_template_any(value, **step_context)
                    log.info(f'websocket send: {value}')
                    if not isinstance(value, str):
                        value = json.dumps(value)
                    ws.send(value)
                    response = {'status': ws.getstatus(), 'recv': ws.recv()}
                    log.info(f'websocket recv: {response.get("recv")}')

                elif item in ('mark', 'parameters', 'fixtures'):
                    pass

                elif item == 'variables':
                    copy_value = copy.deepcopy(value)
                    if not isinstance(copy_value, dict):
                        log.error('step variables must be dict type!')
                    else:
                        step_context.update(
                            render_template_obj.rend_template_any(copy_value, **self.context))

                elif item == 'api':
                    root_dir = args.get('request').config.rootdir
                    raw_api  = yaml.safe_load(Path(root_dir).joinpath(value).open(encoding='utf-8'))
                    api_validate = raw_api.get('validate', [])
                    response = self.run_request(
                        args, copy.deepcopy(raw_api.get('request')),
                        config_hooks, base_url, context=step_context)
                    step_context['response'] = response

                elif item == 'request':
                    response = self.run_request(
                        args, copy.deepcopy(value),
                        copy.deepcopy(config_hooks), base_url, context=step_context)
                    step_context['response'] = response

                elif item == 'extract':
                    copy_value   = copy.deepcopy(value)
                    extract_val  = render_template_obj.rend_template_any(copy_value, **step_context)
                    extract_res  = self.extract_response(response, extract_val)
                    log.info(f'extract 提取变量-> {extract_res}')
                    self.module_variable.update(extract_res)
                    step_context.update(extract_res)
                    self.context.update(self.module_variable)

                elif item == 'export':
                    if isinstance(value, list):
                        for _exp in value:
                            if _exp not in case_exports:
                                case_exports.append(_exp)
                            if step_context.get(_exp):
                                self.context[_exp] = step_context[_exp]
                    else:
                        log.error('export must be list type')

                elif item == 'validate':
                    copy_value = copy.deepcopy(value)
                    copy_value.extend([v for v in api_validate if v not in copy_value])
                    validate_value = render_template_obj.rend_template_any(copy_value, **step_context)
                    if validate_value:
                        log.info(f'validate 校验内容-> {validate_value}')
                        self.validate_response(response, validate_value)

                elif item == 'sleep':
                    sv = render_template_obj.rend_template_any(value, **step_context)
                    try:
                        log.info(f'sleep time: {sv}')
                        time.sleep(sv)
                    except Exception as msg:
                        log.error(f'sleep value must be int or float: {msg}')

                elif item == 'skip':
                    pytest.skip(render_template_obj.rend_template_any(value, **step_context))

                elif item == 'skipif':
                    if_exp = render_template_obj.rend_template_any(value, **step_context)
                    try:
                        eval_result = bool(_safe_eval(str(if_exp)))
                    except Exception as e:
                        log.warning(f'skipif expression error: {e}, expression: {if_exp}')
                        eval_result = False
                    log.info(f'skipif: {eval_result}')
                    if eval_result:
                        pytest.skip(str(if_exp))

                elif item == 'allure':
                    value = render_template_obj.rend_template_any(value, **step_context)
                    value.update(config_allure)
                    if not value.get('feature'):
                        value['feature'] = f'{self.module.__name__}.yml'
                    for ak, av in value.items():
                        try:
                            getattr(allure.dynamic, ak)(av)
                        except Exception as msg:
                            log.error(f'allure.dynamic.{ak} error: {msg}')

                else:
                    value = render_template_obj.rend_template_any(value, **step_context)
                    try:
                        handler = self.g.get(item)
                        if callable(handler):
                            handler(value)
                        else:
                            log.warning(f'unknown step type: {item}')
                    except Exception as msg:
                        raise exceptions.ParserError(f'Parsers error: {msg}') from None

    # ─────────────────────────────────────────────────────────────
    # HTTP 请求
    # ─────────────────────────────────────────────────────────────
    def run_request(self, args, copy_value, config_hooks, base_url, context=None):
        """发送 HTTP 请求并返回 response"""
        request_session = (args.get('requests_function')
                           or args.get('requests_module')
                           or args.get('requests_session'))
        ctx = context if context is not None else self.context
        request_value = render_template_obj.rend_template_any(copy_value, **ctx)

        request_pre = self.request_hooks(config_hooks, request_value)
        if request_pre:
            ctx['req'] = request_value
            self.run_request_hooks(request_pre, request_value, context=ctx)
        self.response_hooks(config_hooks, request_value)

        root_dir      = args.get('request').config.rootdir
        request_value = self.multipart_encoder_request(request_value, root_dir)

        log.info('--------  request info ----------')
        log.info(f'method   -->: {request_value.get("method", "")}')
        log.info(f'url      -->: {request_value.get("url", "")}')
        req_headers = dict(request_session.headers)
        req_headers.update(request_value.get('headers', {}))
        log.info(f'headers  -->: {req_headers}')
        if request_value.get('json'):
            log.info(f'json     -->: {json.dumps(request_value.get("json", {}), ensure_ascii=False)}')
        else:
            log.info(f'data     -->: {request_value.get("data", {})}')

        response = request_session.send_request(base_url=base_url, **request_value)

        elapsed_ms = (response.elapsed.total_seconds() * 1000
                      if getattr(response, 'elapsed', None) else 0)
        log.info(f'------  response info  {response.status_code} {getattr(response, "reason", "")} ------')
        log.info(f'耗时     <--: {elapsed_ms:.0f}ms')
        log.info(f'url      <--: {getattr(response, "url", "")}')
        log.info(f'headers  <--: {dict(response.headers)}')
        log.info(f'cookies  <--: {dict(response.cookies)}')
        log.info(f'raw text <--: {response.text}')

        # 把 elapsed_ms 注入到 context，方便 validate 中使用
        self.context['elapsed'] = elapsed_ms
        if context is not None:
            context['elapsed'] = elapsed_ms

        return response

    # ─────────────────────────────────────────────────────────────
    # 断言
    # ─────────────────────────────────────────────────────────────
    @staticmethod
    def validate_response(response, validate_check: list) -> None:
        """执行所有断言"""
        for check in validate_check:
            for check_type, check_value in check.items():
                # json_schema 特殊处理：check_value[0] 是提取表达式，check_value[1] 是 schema dict
                actual_value = extract.extract_by_object(response, check_value[0])
                expect_value = check_value[1]
                log.info(f'validate 校验-> {check_type}: [{actual_value!r}, {expect_value!r}]')

                _map = {
                    ('eq', 'equals', 'equal'):                          validate.equals,
                    ('lt', 'less_than'):                                 validate.less_than,
                    ('le', 'less_or_equals'):                            validate.less_than_or_equals,
                    ('gt', 'greater_than'):                              validate.greater_than,
                    ('ge', 'greater_or_equals'):                         validate.greater_than_or_equals,
                    ('ne', 'not_equal', 'not_equals'):                   validate.not_equals,
                    ('str_eq', 'str_equals', 'string_equals'):           validate.string_equals,
                    ('len_eq', 'length_equal', 'length_equals'):         validate.length_equals,
                    ('len_gt', 'length_greater_than'):                   validate.length_greater_than,
                    ('len_ge', 'length_greater_or_equals'):              validate.length_greater_than_or_equals,
                    ('len_lt', 'length_less_than'):                      validate.length_less_than,
                    ('len_le', 'length_less_or_equals'):                 validate.length_less_than_or_equals,
                    ('contains', 'contain'):                             validate.contains,
                    ('not_contains', 'not_contain'):                     validate.not_contains,
                    ('contained_by',):                                   validate.contained_by,
                    ('bool_eq', 'bool_equal', 'bool_equals'):            validate.bool_equals,
                    ('regex_match',):                                    validate.regex_match,
                    ('startswith',):                                     validate.startswith,
                    ('endswith',):                                       validate.endswith,
                    # 响应时间断言
                    ('response_time_lt', 'rt_lt'):                       validate.response_time_less_than,
                    ('response_time_le', 'rt_le'):                       validate.response_time_less_than_or_equals,
                    # JSON Schema
                    ('json_schema', 'schema'):                           validate.json_schema,
                }
                matched = False
                for keys, func in _map.items():
                    if check_type in keys:
                        func(actual_value, expect_value)
                        matched = True
                        break
                if not matched:
                    if hasattr(validate, check_type):
                        getattr(validate, check_type)(actual_value, expect_value)
                    else:
                        log.error(f'{check_type} 不是有效的断言类型')

    # ─────────────────────────────────────────────────────────────
    # 提取
    # ─────────────────────────────────────────────────────────────
    @staticmethod
    def extract_response(response, extract_obj: dict):
        extract_result = {}
        if isinstance(extract_obj, dict):
            for var, expr in extract_obj.items():
                extract_result[var] = extract.extract_by_object(response, expr)
        return extract_result

    # ─────────────────────────────────────────────────────────────
    # Fixture 参数
    # ─────────────────────────────────────────────────────────────
    @staticmethod
    def function_parameters(config_fixtures) -> list:
        params = [Parameter('request', Parameter.POSITIONAL_OR_KEYWORD)]
        if isinstance(config_fixtures, str):
            config_fixtures = [f.strip() for f in config_fixtures.split(',')]
        if not config_fixtures:
            params.append(Parameter('requests_session', Parameter.POSITIONAL_OR_KEYWORD))
        else:
            if 'requests_function' in config_fixtures:
                params.append(Parameter('requests_function', Parameter.POSITIONAL_OR_KEYWORD))
            elif 'requests_module' in config_fixtures:
                params.append(Parameter('requests_module', Parameter.POSITIONAL_OR_KEYWORD))
            else:
                params.append(Parameter('requests_session', Parameter.POSITIONAL_OR_KEYWORD))
            for f in config_fixtures:
                if f not in ('requests_function', 'requests_module'):
                    params.append(Parameter(f, Parameter.POSITIONAL_OR_KEYWORD))
        return params

    # ─────────────────────────────────────────────────────────────
    # 参数化
    # ─────────────────────────────────────────────────────────────
    @staticmethod
    def parameters_date(fixtures, parameters):
        if isinstance(fixtures, str):
            fixtures = [f.strip() for f in fixtures.split(',')]
        if isinstance(parameters, list) and len(parameters) >= 1:
            if isinstance(parameters[0], dict):
                params = list(parameters[0].keys())
                new_params = [list(item.values()) for item in parameters]
                for p in params:
                    if p not in fixtures:
                        fixtures.append(p)
                return fixtures, new_params
            return fixtures, parameters
        elif isinstance(parameters, dict):
            for args in parameters.keys():
                if ',' in args:
                    fixtures.extend(args.split(','))
                elif '-' in args:
                    fixtures.extend(args.split('-'))
                else:
                    fixtures.append(args)
            return fixtures, parameters
        return fixtures, []

    # ─────────────────────────────────────────────────────────────
    # Hooks
    # ─────────────────────────────────────────────────────────────
    def hooks_event(self, hooks):
        for event in ('response', 'request'):
            raw = hooks.get(event, [])
            if isinstance(raw, str):
                raw = [r.strip() for r in raw.split(',')]
            hooks[event] = [self.context.get(f) for f in raw if self.context.get(f)]
        return hooks

    def request_hooks(self, config_hooks: dict, request_value: dict) -> dict:
        config_req_hooks = []
        if 'request' in config_hooks:
            h = config_hooks['request']
            config_req_hooks = [x.strip() for x in h.split(',')] if isinstance(h, str) else h
        req_hooks_raw = request_value.get('hooks', {})
        if 'request' in req_hooks_raw:
            rh = req_hooks_raw.pop('request')
            extra = [x.strip() for x in rh.split(',')] if isinstance(rh, str) else rh
            config_req_hooks.extend(extra)
        if config_req_hooks:
            hooks = self.hooks_event({'request': config_req_hooks})
            return {k: v for k, v in hooks.items() if v}
        return {'request': []}

    def run_request_hooks(self, request_pre: dict, request_value, context=None):
        for fun in request_pre.get('request', []):
            ars = list(inspect.signature(fun).parameters.keys())
            if 'req' in ars:
                src = context if context else self.context
                fun(*[src.get(a) for a in ars])
            else:
                fun()
        return request_value

    def response_hooks(self, config_hooks: dict, request_value: dict) -> dict:
        config_resp_hooks = []
        if 'response' in config_hooks:
            h = config_hooks['response']
            config_resp_hooks = [x.strip() for x in h.split(',')] if isinstance(h, str) else h
        req_hooks_raw = request_value.get('hooks', {})
        if 'response' in req_hooks_raw:
            rh = req_hooks_raw.get('response')
            extra = [x.strip() for x in rh.split(',')] if isinstance(rh, str) else rh
            config_resp_hooks.extend(extra)
        if config_resp_hooks:
            hooks = self.hooks_event({'response': config_resp_hooks})
            new_hooks = {k: v for k, v in hooks.items() if v}
            request_value['hooks'] = new_hooks
        return request_value

    # ─────────────────────────────────────────────────────────────
    # MySQL
    # ─────────────────────────────────────────────────────────────
    def execute_mysql(self):
        env_obj = self.g.get('env')
        if not env_obj or (not hasattr(env_obj, 'MYSQL_HOST') and not hasattr(env_obj, 'DB_INFO')):
            return {
                'query_sql':   lambda x: log.error('MYSQL config not found in config.py'),
                'execute_sql': lambda x: log.error('MYSQL config not found in config.py'),
            }
        try:
            db = ConnectMysql(**env_obj.DB_INFO) if hasattr(env_obj, 'DB_INFO') else ConnectMysql(
                host=env_obj.MYSQL_HOST, user=env_obj.MYSQL_USER,
                password=env_obj.MYSQL_PASSWORD, port=env_obj.MYSQL_PORT,
                database=env_obj.MYSQL_DATABASE)
            return {'query_sql': db.query_sql, 'execute_sql': db.execute_sql}
        except Exception as msg:
            log.error(f'mysql init error: {msg}')
            return {
                'query_sql':   lambda x: log.error('MYSQL connect error'),
                'execute_sql': lambda x: log.error('MYSQL connect error'),
            }

    # ─────────────────────────────────────────────────────────────
    # 文件上传
    # ─────────────────────────────────────────────────────────────
    @staticmethod
    def upload_file(filepath: Path):
        if not filepath.exists():
            log.error(f'文件路径不存在：{filepath}')
            return
        mime_type = mimetypes.guess_type(filepath)[0]
        return (filepath.name, filepath.open('rb'), mime_type)

    def multipart_encoder_request(self, request_value: dict, root_dir):
        if 'files' not in request_value:
            return request_value
        fields = list(request_value.get('data', {}).items())
        for key, value in request_value.get('files', {}).items():
            fp = Path(root_dir).joinpath(value)
            fields.append((key, self.upload_file(fp.resolve()) if fp.is_file() else value))
        m = MultipartEncoder(fields=fields)
        request_value.pop('files')
        request_value['data'] = m
        request_value.setdefault('headers', {})['Content-Type'] = m.content_type
        return request_value
