# Interface — YAML 驱动的 API 自动化测试框架

> 基于 pytest + YAML 的接口自动化测试，零 Python 代码，用 YAML 描述测试用例。
> 内置变量渲染、数据提取、断言验证、Allure 报告，支持 HTTP / WebSocket。

## 技术选型

| 组件 | 说明 |
|------|------|
| pytest | 测试框架 |
| requests | HTTP 请求 |
| Allure | 测试报告 |
| Jinja2 | 模板变量渲染 |
| jsonpath / jmespath | 数据提取 |
| PyYAML | YAML 解析 |

## 项目结构

```
interface/
  conftest.py               pytest + hui 插件配置
  pytest.ini                pytest 配置
  config.py                 全局配置
  hui_core/
    render_template_obj.py   模板变量渲染 (${var}, ${func()})
    extract.py               数据提取 (JSONPath/JMESPath/Regex/Object/WS)
    validate.py              断言比较 (eq/ne/gt/lt/contains/regex/len等)
    hui_builtins.py          内置函数 (timestamp/rand_str/b64/md5/fake等)
    log.py                   日志
    exceptions.py            异常定义
  common/                    公共方法
  testcases/                 YAML 测试用例目录 (131个)
  tests/                     单元测试
    test_extract.py          数据提取测试
    test_validate.py         断言比较测试
    test_render_template.py  模板渲染测试
    test_hui_builtins.py     内置函数测试
  logs/                      日志输出
  debug/                     调试工具
```

## 快速开始

```bash
pip install -r requirements.txt

# 执行所有测试
pytest testcases/ -v

# 执行指定用例
pytest testcases/saas/hui_api_testcases/ -v

# 生成 Allure 报告
pytest testcases/ --alluredir=./report
allure serve ./report
```

## YAML 用例示例

```yaml
# testcases/demo/login.yml
name: 登录接口测试
variables:
  base_url: https://api.example.com
  username: admin
  password: "123456"

request:
  method: POST
  url: ${base_url}/api/login
  headers:
    Content-Type: application/json
  json:
    username: ${username}
    password: ${password}

extract:
  - key: token
    expression: $.data.token
    type: jsonpath

validate:
  - eq: [$.code, 200]
  - contains: [$.msg, success]
  - lt: [$.response_time, 1000]
```

## 变量渲染

支持 `${var}` 语法，在 URL / Headers / Body 中使用：

```yaml
url: ${base_url}/api/users/${user_id}
headers:
  Authorization: Bearer ${token}
json:
  name: ${username}
  timestamp: ${timestamp()}
  random: ${rand_str(8)}
```

### 内置函数

| 函数 | 说明 | 示例 |
|------|------|------|
| `timestamp()` | 当前时间戳（秒） | `1700000000` |
| `timestamp(ms=True)` | 毫秒时间戳 | `1700000000000` |
| `rand_str(5)` | 随机字符串 | `a1b2c` |
| `rand_int(1,100)` | 随机整数 | `42` |
| `current_time()` | 当前时间 | `2025-01-01 12:00:00` |
| `b64_encode('hello')` | Base64编码 | `aGVsbG8=` |
| `b64_decode('aGVsbG8=')` | Base64解码 | `hello` |
| `md5('hello')` | MD5摘要 | `5d41402abc4b...` |
| `sha256('hello')` | SHA256摘要 | `2cf24dba5fb0...` |
| `fake.name()` | 随机姓名 | `张三` |
| `fake.email()` | 随机邮箱 | `test@example.com` |
| `fake.phone()` | 随机手机号 | `13800138000` |

## 数据提取

| 方式 | 表达式格式 | 说明 |
|------|-----------|------|
| JSONPath | `$.data.name` | 从 JSON body 提取 |
| JMESPath | `body.data.name` | JMESPath 表达式 |
| Header | `headers.Content-Type` | 从响应头提取 |
| Regex | `.+?` 或 `.*?` 包含的表达式 | 正则匹配 |
| 对象属性 | `status_code` / `url` / `text` | 直接取值 |
| WebSocket | `status` / `text` / `$.xxx` | WS 响应提取 |

## 断言验证

| 断言 | 说明 | 示例 |
|------|------|------|
| `equals` | 等于 | `equals(1, 1)` |
| `not_equals` | 不等于 | `not_equals(1, 2)` |
| `greater_than` | 大于 | `greater_than(5, 3)` |
| `less_than` | 小于 | `less_than(1, 5)` |
| `contains` | 包含 | `contains("hello world", "world")` |
| `not_contains` | 不包含 | `not_contains("hello", "xyz")` |
| `regex_match` | 正则匹配 | `regex_match("hello123", r"hello\d+")` |
| `length_equals` | 长度等于 | `length_equals([1,2,3], 3)` |
| `startswith` | 开头匹配 | `startswith("hello", "he")` |
| `endswith` | 结尾匹配 | `endswith("hello", "lo")` |
| `response_time_less_than` | 响应时间小于 | `response_time_less_than(100, 200)` |

## 单元测试

```bash
cd interface
pytest tests/ -v
# 181 tests passed
```

## 测试用例统计

- 131+ YAML 测试用例覆盖所有 API 接口
- 支持参数化、数据驱动
- Allure 报告生成
- WebSocket 接口测试支持
