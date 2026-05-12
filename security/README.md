# Security — 安全测试与漏洞扫描框架

> 基于 Xray + Rad 实现安全测试和漏洞扫描，支持被动扫描、主动爬取、认证登录、报告解析与漏洞断言。

## 技术选型

| 工具 | 用途 | 说明 |
|------|------|------|
| Xray | 被动漏洞扫描 | 检测 SQLi/XSS/XXE/命令注入/暴力破解等 |
| Rad | 主动爬取 | 基于 Chrome 的智能爬虫，发现更多攻击面 |
| Selenium | 认证登录 | 登录需要认证的页面，获取 Cookie |

## 项目结构

```
security/
  run.py                    CLI 入口
  conftest.py               pytest fixture
  config/
    scan_config.yml          扫描配置
  core/
    errors.py                错误体系
    config.py                配置加载（自动推断 Xray_Rad_complete/ 路径）
    scanner.py               Scanner 核心扫描器
    report_parser.py         报告解析器（VulnFinding/ReportSummary/断言）
    auth_handler.py          认证处理器（Selenium/requests 登录）
  testcases/
    test_security_scan.py    安全扫描测试
    test_vuln_report.py      漏洞报告断言测试
  reports/                   扫描报告输出目录
  Xray_Rad_complete/         Xray/Rad 二进制与配置（已存在）
```

## 快速开始

```bash
pip install -r requirements.txt

# 执行安全扫描
python run.py scan

# 扫描并显示漏洞摘要
python run.py scan --summary

# 串行扫描（默认并发）
python run.py scan --sequential

# 指定目标文件和输出目录
python run.py scan --targets target.txt --output reports

# 解析最新扫描报告
python run.py report --summary

# 解析指定报告
python run.py report --report Xray_Rad_complete/20250728141050.json

# 断言漏洞数量（CI/CD 用）
python run.py assert
python run.py assert --max-critical 0 --max-high 0
python run.py assert --max-high 5

# pytest 方式执行
pytest testcases/ -v

# 执行实际扫描（需要设置环境变量）
RUN_SCAN=1 pytest testcases/test_security_scan.py -v
```

## 扫描流程

```
1. 启动 Xray 被动扫描代理 (127.0.0.1:7777)
2. 读取目标 URL 列表
3. 对每个目标启动 Rad 爬虫，流量经过 Xray 代理
4. Xray 实时检测流量中的漏洞
5. 生成 JSON + HTML 报告
6. 解析报告，按严重级别分类统计
7. 断言漏洞数量是否超过阈值
```

## 漏洞检测插件

| 插件 | 说明 | 严重级别 |
|------|------|---------|
| sqldet | SQL 注入（布尔/报错/时间盲注） | high |
| xss | XSS 跨站脚本 | high |
| xxe | XML 外部实体注入 | high |
| cmd-injection | 命令注入 | critical |
| brute-force | 暴力破解 | medium |
| baseline | 基线检查（敏感信息泄露等） | low |

## 报告解析

框架自动解析 Xray JSON 报告，支持：
- 按严重级别分类（critical/high/medium/low）
- 按漏洞类型统计
- 按目标 URL 统计
- 漏洞阈值断言（CI/CD 集成）
- 处理有编码问题的 JSON 文件

## 认证扫描

对于需要登录的页面，配置 `config/scan_config.yml` 中的 `auth` 部分：

```yaml
auth:
  enabled: true
  login_url: "https://example.com/login"
  username: "admin"
  password: "password123"
  username_selector: "input[name='username']"
  password_selector: "input[name='password']"
  submit_selector: "button[type='submit']"
```

框架会使用 Selenium 登录获取 Cookie，然后注入到 Rad 爬虫中。

## pytest 测试

| 测试文件 | 测试项 |
|---------|--------|
| test_security_scan.py | 前置条件检查、二进制存在、目标存在、完整扫描 |
| test_vuln_report.py | 报告解析、摘要生成、级别分类、漏洞断言、数据完整性 |
