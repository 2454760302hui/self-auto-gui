"""请求执行引擎 —— 核心能力"""
import httpx
import json
import re
import time
import uuid as _uuid
import random as _random
import logging
from typing import Any
from faker import Faker
from jsonpath_ng import parse as jsonpath_parse
import jmespath
import jsonschema

fake = Faker(locale="zh_CN")
_script_logger = logging.getLogger('poa.script')


# ── 变量渲染 ──────────────────────────────────────────────────
def render(template: Any, variables: dict) -> Any:
    """递归渲染模板变量 {{var}} 或 ${var}"""
    if isinstance(template, str):
        return _render_str(template, variables)
    elif isinstance(template, dict):
        return {k: render(v, variables) for k, v in template.items()}
    elif isinstance(template, list):
        return [render(item, variables) for item in template]
    return template


def _render_str(s: str, variables: dict) -> Any:
    # 支持 {{var}} 和 ${var} 两种语法
    pattern = re.compile(r'\{\{(.+?)\}\}|\$\{(.+?)\}')

    def replacer(m):
        expr = (m.group(1) or m.group(2)).strip()
        # 内置函数
        val = _eval_builtin(expr, variables)
        if val is not None:
            return str(val)
        # 变量查找
        return str(variables.get(expr, m.group(0)))

    result = pattern.sub(replacer, s)
    # 如果整个字符串就是一个变量引用，尝试返回原始类型
    full_match = re.fullmatch(r'\{\{(.+?)\}\}|\$\{(.+?)\}', s)
    if full_match:
        expr = (full_match.group(1) or full_match.group(2)).strip()
        val = _eval_builtin(expr, variables)
        if val is not None:
            return val
        return variables.get(expr, result)
    return result


def _eval_builtin(expr: str, variables: dict) -> Any:
    """执行内置函数"""
    import uuid as _uuid
    import random as _random

    builtins = {
        'timestamp()':    lambda: int(time.time()),
        'timestamp_ms()': lambda: int(time.time() * 1000),
        'uuid()':         lambda: _uuid.uuid4().hex,
        'rand_str()':     lambda: _uuid.uuid4().hex[:16],
        'rand_int()':     lambda: _random.randint(0, 9999),
        'fake.name()':    lambda: fake.name(),
        'fake.phone()':   lambda: fake.phone_number(),
        'fake.email()':   lambda: fake.email(),
        'fake.address()': lambda: fake.address(),
        'fake.company()': lambda: fake.company(),
        'fake.text()':    lambda: fake.text(max_nb_chars=50),
        'fake.id_card()': lambda: fake.ssn(),
    }
    # 带参数的函数
    m = re.match(r'rand_int\((\d+),\s*(\d+)\)', expr)
    if m:
        return _random.randint(int(m.group(1)), int(m.group(2)))
    m = re.match(r'rand_str\((\d+)\)', expr)
    if m:
        return _uuid.uuid4().hex[:int(m.group(1))]
    val = builtins.get(expr + '()', builtins.get(expr, None))
    if callable(val):
        return val()
    return val


# ── 提取变量 ──────────────────────────────────────────────────
def extract_variable(response_data: dict, expression: str) -> Any:
    """从响应中提取变量
    expression 支持:
      status_code / status
      headers.Content-Type
      body.xxx  (jmespath)
      $.xxx     (jsonpath)
      正则: re:pattern
    """
    if expression in ('status_code', 'status'):
        return response_data.get('status_code')
    if expression.startswith('headers.'):
        key = expression[8:]
        return response_data.get('headers', {}).get(key)
    if expression.startswith('$.'):
        try:
            expr = jsonpath_parse(expression)
            matches = expr.find(response_data.get('json', {}))
            if not matches:
                return None
            return matches[0].value if len(matches) == 1 else [m.value for m in matches]
        except Exception:
            return None
    if expression.startswith('re:'):
        pattern = expression[3:]
        text = response_data.get('text', '')
        m = re.search(pattern, text, re.S)
        return m.group(1) if m and m.lastindex else (m.group(0) if m else None)
    # jmespath
    try:
        return jmespath.search(expression, response_data.get('json', {}))
    except Exception:
        return None


# ── 断言 ──────────────────────────────────────────────────────
def run_assertion(assertion: dict, response_data: dict, variables: dict) -> dict:
    """执行单条断言，返回 {passed, message}"""
    a_type   = assertion.get('type', 'eq')
    source   = assertion.get('source', 'body')   # body/status/header/response_time
    path     = assertion.get('path', '')
    expected = render(assertion.get('expected', ''), variables)

    # 取实际值
    if source == 'status':
        actual = response_data.get('status_code')
    elif source == 'response_time':
        actual = response_data.get('elapsed_ms', 0)
    elif source == 'header':
        actual = response_data.get('headers', {}).get(path, '')
    else:
        actual = extract_variable(response_data, path) if path else response_data.get('json')

    # 类型转换
    try:
        if isinstance(actual, str) and isinstance(expected, (int, float)):
            actual = type(expected)(actual)
        elif isinstance(expected, str) and isinstance(actual, (int, float)):
            expected = type(actual)(expected)
    except (ValueError, TypeError):
        pass

    passed  = False
    message = ''
    try:
        if a_type == 'eq':
            passed = actual == expected
        elif a_type == 'ne':
            passed = actual != expected
        elif a_type == 'gt':
            passed = float(actual) > float(expected)
        elif a_type == 'lt':
            passed = float(actual) < float(expected)
        elif a_type == 'contains':
            passed = str(expected) in str(actual)
        elif a_type == 'not_contains':
            passed = str(expected) not in str(actual)
        elif a_type == 'exists':
            passed = actual is not None
        elif a_type == 'not_exists':
            passed = actual is None
        elif a_type == 'regex':
            passed = bool(re.search(str(expected), str(actual), re.S))
        elif a_type == 'json_schema':
            jsonschema.validate(instance=actual, schema=expected)
            passed = True
        elif a_type == 'len_eq':
            passed = len(actual) == int(expected)
        elif a_type == 'len_gt':
            passed = len(actual) > int(expected)
        elif a_type == 'len_lt':
            passed = len(actual) < int(expected)
        else:
            passed = actual == expected
        if not passed:
            message = f'期望 {expected!r}，实际 {actual!r}'
    except Exception as e:
        message = str(e)

    return {'passed': passed, 'message': message,
            'actual': actual, 'expected': expected, 'type': a_type}


# ── 脚本执行（沙箱） ──────────────────────────────────────────
def run_script(script: str, context: dict) -> dict:
    """执行前置/后置脚本，返回更新后的变量
    脚本中可用:
      poa.setVariable('key', value)
      poa.getVariable('key')
      poa.setEnvVariable('key', value)
      response (后置脚本中)
    """
    if not script or not script.strip():
        return context

    updated_vars = {}

    class PoaHelper:
        def setVariable(self, key, value):
            updated_vars[key] = value
            context[key] = value

        def getVariable(self, key):
            return context.get(key)

        def setEnvVariable(self, key, value):
            updated_vars[f'__env__{key}'] = value
            context[key] = value

        def log(self, *args):
            _script_logger.info(' '.join(str(a) for a in args))

    _BLOCKED_NAMES = {
        '__import__', 'eval', 'exec', 'compile', 'open', 'input',
        'breakpoint', 'exit', 'quit', 'globals', 'locals',
    }
    local_ctx = {
        'poa':       PoaHelper(),
        'response':  context.get('__response__'),
        'variables': context,
        'fake':      fake,
    }
    # 安全检查: 拒绝包含危险调用的脚本
    for name in _BLOCKED_NAMES:
        if name + '(' in script:
            raise ValueError(f"脚本不允许使用 '{name}()' 函数调用")
    safe_globals = {"__builtins__": {
        k: v for k, v in __builtins__.items()
        if k not in _BLOCKED_NAMES
    } if isinstance(__builtins__, dict) else {}}
    try:
        exec(script, safe_globals, local_ctx)  # noqa
    except Exception as e:
        _script_logger.error('脚本执行错误: %s', e)

    return updated_vars


# ── HTTP 请求执行 ─────────────────────────────────────────────
async def execute_request(api_config: dict, variables: dict,
                          timeout: float = 30.0) -> dict:
    """执行单个 API 请求
    api_config: {method, url, headers, params, body_type, body,
                 pre_script, post_script, assertions, extractions}
    variables:  当前环境变量 + 全局变量
    """
    vars_copy = dict(variables)

    # 前置脚本
    if api_config.get('pre_script'):
        run_script(api_config['pre_script'], vars_copy)

    method  = render(api_config.get('method', 'GET'), vars_copy).upper()
    url     = render(api_config.get('url', ''), vars_copy)
    headers = render(api_config.get('headers', {}), vars_copy)
    params  = render(api_config.get('params', {}), vars_copy)

    # 过滤掉 disabled 的 headers/params
    if isinstance(headers, list):
        headers = {h['key']: h['value'] for h in headers
                   if h.get('enabled', True) and h.get('key')}
    if isinstance(params, list):
        params = {p['key']: p['value'] for p in params
                  if p.get('enabled', True) and p.get('key')}

    body_type = api_config.get('body_type', 'none')
    body_raw  = api_config.get('body', '')

    kwargs: dict = {'headers': headers, 'params': params}
    if body_type == 'json':
        try:
            body_data = json.loads(render(body_raw, vars_copy)) if isinstance(body_raw, str) else render(body_raw, vars_copy)
        except Exception:
            body_data = render(body_raw, vars_copy)
        kwargs['json'] = body_data
    elif body_type == 'form':
        form_data = render(body_raw, vars_copy)
        if isinstance(form_data, list):
            form_data = {f['key']: f['value'] for f in form_data if f.get('enabled', True)}
        kwargs['data'] = form_data
    elif body_type == 'raw':
        kwargs['content'] = render(body_raw, vars_copy).encode()
    elif body_type == 'graphql':
        gql = render(body_raw, vars_copy)
        if isinstance(gql, str):
            try:
                gql = json.loads(gql)
            except Exception:
                gql = {'query': gql}
        kwargs['json'] = gql

    start = time.time()
    response_data = {}
    try:
        async with httpx.AsyncClient(timeout=timeout, verify=False,
                                     follow_redirects=True) as client:
            resp = await client.request(method, url, **kwargs)
        elapsed_ms = (time.time() - start) * 1000

        try:
            resp_json = resp.json()
        except Exception:
            resp_json = None

        response_data = {
            'status_code':  resp.status_code,
            'elapsed_ms':   round(elapsed_ms, 2),
            'headers':      dict(resp.headers),
            'text':         resp.text,
            'json':         resp_json,
            'size':         len(resp.content),
        }
    except httpx.TimeoutException:
        response_data = {'error': 'Request timeout', 'status_code': 0,
                         'elapsed_ms': (time.time() - start) * 1000}
    except Exception as e:
        response_data = {'error': str(e), 'status_code': 0,
                         'elapsed_ms': (time.time() - start) * 1000}

    # 后置脚本
    if api_config.get('post_script'):
        vars_copy['__response__'] = response_data
        run_script(api_config['post_script'], vars_copy)

    # 提取变量
    extracted = {}
    for ext in api_config.get('extractions', []):
        if not ext.get('enabled', True):
            continue
        key  = ext.get('key', '')
        expr = ext.get('expression', '')
        if key and expr:
            val = extract_variable(response_data, render(expr, vars_copy))
            extracted[key] = val
            vars_copy[key] = val

    # 断言
    assertion_results = []
    for assertion in api_config.get('assertions', []):
        if not assertion.get('enabled', True):
            continue
        result = run_assertion(assertion, response_data, vars_copy)
        assertion_results.append({**assertion, **result})

    all_passed = all(r['passed'] for r in assertion_results)

    return {
        'request': {
            'method': method, 'url': url,
            'headers': headers, 'params': params,
            'body_type': body_type, 'body': body_raw,
        },
        'response':    response_data,
        'assertions':  assertion_results,
        'extracted':   extracted,
        'passed':      all_passed,
        'variables':   {k: v for k, v in vars_copy.items() if not k.startswith('__')},
    }


# ── 测试套件执行 ──────────────────────────────────────────────
async def execute_suite(steps: list, variables: dict,
                        on_step_done=None) -> dict:
    """按顺序执行测试套件中的所有步骤"""
    results  = []
    vars_ctx = dict(variables)
    passed   = 0
    failed   = 0
    start    = time.time()

    for i, step in enumerate(steps):
        if not step.get('enabled', True):
            continue
        # 步骤级变量覆盖
        step_vars = {**vars_ctx, **step.get('variables', {})}
        result = await execute_request(step, step_vars)
        # 把提取的变量传递给后续步骤
        vars_ctx.update(result.get('extracted', {}))

        step_result = {
            'index':  i,
            'name':   step.get('name', f'Step {i+1}'),
            'passed': result['passed'],
            **result,
        }
        results.append(step_result)
        if result['passed']:
            passed += 1
        else:
            failed += 1

        if on_step_done:
            await on_step_done(step_result)

        # 失败时是否继续
        if not result['passed'] and step.get('stop_on_failure', False):
            break

    duration = round((time.time() - start) * 1000, 2)
    return {
        'total':    len(results),
        'passed':   passed,
        'failed':   failed,
        'duration': duration,
        'results':  results,
        'status':   'passed' if failed == 0 else 'failed',
    }
