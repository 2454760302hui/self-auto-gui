# -*- coding: utf-8 -*-
"""
NextAgent 全功能测试脚本
测试范围: AutoGLM / Browser-Use / API Testing / Security Scan
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Any

BASE = "http://127.0.0.1"
PORTS = {
    "AutoGLM":      8000,
    "Browser-Use":  9242,
    "API Testing":  9243,
    "Security Scan": 9244,
}

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def p(label: str, msg: str, ok: bool) -> None:
    icon = f"{GREEN}[PASS]{RESET}" if ok else f"{RED}[FAIL]{RESET}"
    print(f"  {icon} {CYAN}{label}{RESET}  {msg}")


@dataclass
class TestResult:
    name: str
    ok: bool
    detail: str = ""


def api_get(port: int, path: str, timeout: int = 10, method: str = "GET") -> tuple[bool, Any, str]:
    url = f"{BASE}:{port}{path}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "NextAgent-Test/1.0"}, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read().decode("utf-8")
            try:
                return True, json.loads(data), ""
            except json.JSONDecodeError:
                return True, data, ""
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:200]
        return False, None, f"HTTP {e.code}: {body}"
    except Exception as e:
        return False, None, str(e)


def api_post(port: int, path: str, body: Any = None, timeout: int = 15) -> tuple[bool, Any, str]:
    url = f"{BASE}:{port}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else b""
    try:
        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json", "User-Agent": "NextAgent-Test/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            resp = r.read().decode("utf-8")
            try:
                return True, json.loads(resp), ""
            except json.JSONDecodeError:
                return True, resp, ""
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:200]
        return False, None, f"HTTP {e.code}: {body}"
    except Exception as e:
        return False, None, str(e)


# ═══════════════════════════════════════════════════════════════════════════════
# 模块 1: AutoGLM (端口 8000)
# ═══════════════════════════════════════════════════════════════════════════════

def test_autoglm() -> list[TestResult]:
    results: list[TestResult] = []
    port = PORTS["AutoGLM"]

    # ── 1.1 健康检查 ─────────────────────────────────────────────────────────
    ok, data, err = api_get(port, "/api/health")
    if ok and isinstance(data, dict):
        version = data.get("version") or data.get("app_version", "unknown")
        results.append(TestResult("AutoGLM 健康检查", True, f"version={version}"))
    else:
        results.append(TestResult("AutoGLM 健康检查", False, err))
        return results

    # ── 1.2 设备列表 ────────────────────────────────────────────────────────
    ok, data, err = api_get(port, "/api/devices")
    if ok and isinstance(data, dict):
        devs = data.get("devices", [])
        results.append(TestResult("设备列表 API", True, f"设备数={len(devs)}"))
    else:
        results.append(TestResult("设备列表 API", False, err))

    # ── 1.3 设备分组列表 ────────────────────────────────────────────────────
    ok, data, err = api_get(port, "/api/device-groups")
    if ok:
        groups = data.get("groups", []) if isinstance(data, dict) else []
        results.append(TestResult("设备分组 API", True, f"分组数={len(groups)}"))
    else:
        results.append(TestResult("设备分组 API", False, err))

    # ── 1.4 AI 配置读取 ─────────────────────────────────────────────────────
    ok, data, err = api_get(port, "/api/config")
    if ok and isinstance(data, dict):
        model = data.get("model_name") or data.get("model", "unknown")
        source = data.get("source", "unknown")
        results.append(TestResult("AI 配置 API", True, f"model={model}, source={source}"))
    else:
        results.append(TestResult("AI 配置 API", False, err))

    # ── 1.5 Agent 状态 ──────────────────────────────────────────────────────
    ok, data, err = api_get(port, "/api/status")
    if ok and isinstance(data, dict):
        initialized = data.get("initialized", False)
        version = data.get("version", "unknown")
        results.append(TestResult(
            "Agent 状态 API", True,
            f"initialized={initialized}, version={version}"
        ))
    else:
        results.append(TestResult("Agent 状态 API", False, err))

    # ── 1.6 设备健康 ────────────────────────────────────────────────────────
    ok, data, err = api_get(port, "/api/devices/7HX0219923014524/health", timeout=15)
    if ok and isinstance(data, dict):
        battery = data.get("battery_level", "N/A")
        results.append(TestResult("设备健康监控", True, f"battery={battery}"))
    else:
        results.append(TestResult("设备健康监控", ok, err or "设备不在线"))

    # ── 1.7 通知列表 ────────────────────────────────────────────────────────
    ok, data, err = api_get(port, "/api/notifications/7HX0219923014524")
    results.append(TestResult("通知监控 API", ok, "" if ok else err))

    # ── 1.8 任务历史 ────────────────────────────────────────────────────────
    ok, data, err = api_get(port, "/api/history", timeout=15)
    if ok and isinstance(data, dict):
        items = data.get("items", data.get("history", []))
        results.append(TestResult("任务历史 API", True, f"记录数={len(items)}"))
    else:
        results.append(TestResult("任务历史 API", ok, err))

    # ── 1.9 工作流列表 ─────────────────────────────────────────────────────
    ok, data, err = api_get(port, "/api/workflows")
    if ok and isinstance(data, dict):
        wfs = data.get("workflows", [])
        results.append(TestResult("工作流 API", True, f"工作流数={len(wfs)}"))
    else:
        results.append(TestResult("工作流 API", ok, err))

    # ── 1.10 定时任务列表 ────────────────────────────────────────────────────
    ok, data, err = api_get(port, "/api/scheduled-tasks", timeout=15)
    if ok and isinstance(data, dict):
        tasks = data.get("tasks", [])
        results.append(TestResult("定时任务 API", True, f"任务数={len(tasks)}"))
    else:
        results.append(TestResult("定时任务 API", ok, err))

    # ── 1.11 指标数据 ───────────────────────────────────────────────────────
    ok, data, err = api_get(port, "/api/metrics", timeout=15)
    results.append(TestResult("指标 API", ok, "" if ok else err))

    # ── 1.12 设备控制 - 截图 ───────────────────────────────────────────────
    ok, data, err = api_post(port, "/api/control/screenshot", {"device_id": "7HX0219923014524"}, timeout=20)
    if ok and isinstance(data, dict):
        has_img = bool(data.get("image") or data.get("success"))
        results.append(TestResult("截图控制 API", True, f"success={has_img}"))
    else:
        results.append(TestResult("截图控制 API", ok, err))

    # ── 1.13 设备控制 - 获取当前应用 ──────────────────────────────────────
    ok, data, err = api_post(port, "/api/control/current-app", {"device_id": "7HX0219923014524"}, timeout=15)
    if ok and isinstance(data, dict):
        app = data.get("app_name", "N/A")
        results.append(TestResult("当前应用 API", True, f"app={app}"))
    else:
        results.append(TestResult("当前应用 API", ok, err))

    # ── 1.14 设备控制 - 已安装应用 ─────────────────────────────────────────
    ok, data, err = api_post(port, "/api/control/apps", {"device_id": "7HX0219923014524"}, timeout=30)
    if ok and isinstance(data, dict):
        sys_apps = len(data.get("system", []))
        third_apps = len(data.get("third_party", []))
        results.append(TestResult("已安装应用 API", True, f"系统={sys_apps}, 第三方={third_apps}"))
    else:
        results.append(TestResult("已安装应用 API", ok, err))

    # ── 1.15 mDNS 发现 ─────────────────────────────────────────────────────
    ok, data, err = api_get(port, "/api/devices/discover_mdns", timeout=15)
    results.append(TestResult("mDNS 设备发现", ok, "" if ok else err))

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# 模块 2: Browser-Use (端口 9242)
# ═══════════════════════════════════════════════════════════════════════════════

def test_browser() -> list[TestResult]:
    results: list[TestResult] = []
    port = PORTS["Browser-Use"]

    # ── 2.1 健康检查 ───────────────────────────────────────────────────────
    ok, data, err = api_get(port, "/health")
    if ok and isinstance(data, dict):
        results.append(TestResult("Browser-Use 健康检查", True, f"status={data.get('status', 'ok')}"))
    else:
        results.append(TestResult("Browser-Use 健康检查", False, err))
        return results

    # ── 2.2 LLM 状态 ───────────────────────────────────────────────────────
    ok, data, err = api_get(port, "/llm-status")
    if ok and isinstance(data, dict):
        cfg = data.get("configured", False)
        model = data.get("model", "N/A")
        results.append(TestResult("LLM 状态 API", True, f"configured={cfg}, model={model}"))
    else:
        results.append(TestResult("LLM 状态 API", ok, err))

    # ── 2.3 任务历史 ───────────────────────────────────────────────────────
    ok, data, err = api_get(port, "/traces")
    if ok and isinstance(data, dict):
        runs = data.get("runs", [])
        results.append(TestResult("任务历史 API", True, f"记录数={len(runs)}"))
    else:
        results.append(TestResult("任务历史 API", ok, err))

    # ── 2.4 清理历史 ───────────────────────────────────────────────────────
    ok, data, err = api_get(port, "/traces", method="DELETE")
    results.append(TestResult("清空历史 API", ok, "" if ok else err))

    # ── 2.5 DSL 任务执行 (快速模式) ────────────────────────────────────────
    ok, data, err = api_post(
        port, "/run-task",
        {
            "task": "打开 https://httpbin.org/html 并截图",
            "mode": "dsl",
            "max_steps": 5,
            "dsl": "打开 https://httpbin.org/html\n等待加载完成\n截图",
        },
        timeout=120,
    )
    if ok and isinstance(data, dict):
        success = data.get("success", False)
        elapsed = data.get("data", {}).get("elapsed_ms", 0) if isinstance(data.get("data"), dict) else 0
        results.append(TestResult(
            "DSL 任务执行", True, f"success={success}, elapsed={elapsed}ms"
        ))
    else:
        results.append(TestResult("DSL 任务执行", False, err[:100]))

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# 模块 3: API Testing (端口 9243)
# ═══════════════════════════════════════════════════════════════════════════════

def test_api_testing() -> list[TestResult]:
    results: list[TestResult] = []
    port = PORTS["API Testing"]

    # ── 3.1 健康检查 ───────────────────────────────────────────────────────
    ok, data, err = api_get(port, "/health")
    if ok:
        svc = data.get("service", "N/A") if isinstance(data, dict) else str(data)[:30]
        results.append(TestResult("API Testing 健康检查", True, f"service={svc}"))
    else:
        results.append(TestResult("API Testing 健康检查", False, err))
        return results

    # ── 3.2 环境列表 ───────────────────────────────────────────────────────
    ok, data, err = api_get(port, "/envs")
    if ok and isinstance(data, dict):
        envs = data.get("data", data.get("environments", []))
        results.append(TestResult("环境列表 API", True, f"环境数={len(envs)}"))
    else:
        results.append(TestResult("环境列表 API", ok, err))

    # ── 3.3 执行 YAML 测试用例 ───────────────────────────────────────────────
    yaml_payload = {
        "yaml": """config:
  base_url: https://httpbin.org
  env: aliyun
teststeps:
  - name: GET 请求测试
    request:
      method: GET
      url: /get
    validate:
      - assert: status_code
        expect: 200
  - name: POST JSON 测试
    request:
      method: POST
      url: /post
      headers:
        Content-Type: application/json
      data:
        name: nextagent
        type: automation
    validate:
      - assert: status_code
        expect: 200
""",
        "env": "aliyun",
    }
    ok, data, err = api_post(port, "/run", yaml_payload, timeout=30)
    if ok and isinstance(data, dict):
        results.append(TestResult(
            "YAML 测试执行", data.get("success", False),
            f"success={data.get('success')}, duration={data.get('duration_ms', 'N/A')}ms"
        ))
    else:
        results.append(TestResult("YAML 测试执行", ok, err[:100]))

    # ── 3.4 YAML 解析 ──────────────────────────────────────────────────────
    ok, data, err = api_post(port, "/parse-yaml", {
        "yaml_content": """config:
  base_url: https://httpbin.org
teststeps:
  - name: ping
    request:
      method: GET
      url: /get
"""}, timeout=15)
    results.append(TestResult("YAML 解析 API", ok, "" if ok else err))

    # ── 3.5 端点测试 ───────────────────────────────────────────────────────
    ok, data, err = api_post(port, "/test-endpoint", {
        "method": "GET",
        "url": "https://httpbin.org/get",
        "headers": {"User-Agent": "NextAgent-Test/1.0"},
    }, timeout=15)
    results.append(TestResult("端点测试 API", ok, "" if ok else err))

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# 模块 4: Security Scan (端口 9244)
# ═══════════════════════════════════════════════════════════════════════════════

def test_security() -> list[TestResult]:
    results: list[TestResult] = []
    port = PORTS["Security Scan"]

    # ── 4.1 健康检查 ───────────────────────────────────────────────────────
    ok, data, err = api_get(port, "/health")
    if ok:
        svc = data.get("service", "N/A") if isinstance(data, dict) else str(data)[:30]
        results.append(TestResult("Security Scan 健康检查", True, f"service={svc}"))
    else:
        results.append(TestResult("Security Scan 健康检查", False, err))
        return results

    # ── 4.2 扫描历史列表 ───────────────────────────────────────────────────
    ok, data, err = api_get(port, "/scans")
    if ok and isinstance(data, dict):
        scans = data.get("data", data.get("scans", []))
        results.append(TestResult("扫描历史 API", True, f"记录数={len(scans)}"))
    else:
        results.append(TestResult("扫描历史 API", ok, err))

    # ── 4.3 启动扫描任务 ────────────────────────────────────────────────────
    ok, data, err = api_post(
        port, "/scan",
        {"target_url": "http://httpbin.org", "strategy": "fast"},
        timeout=30,
    )
    if ok and isinstance(data, dict):
        scan_id = data.get("task_id", data.get("scan_id", data.get("id", "N/A")))
        results.append(TestResult("启动扫描 API", True, f"task_id={scan_id}"))
    else:
        results.append(TestResult("启动扫描 API", ok, err[:100]))

    # ── 4.4 如果有扫描 ID，查状态 ─────────────────────────────────────────
    if ok and isinstance(data, dict):
        scan_id = data.get("task_id") or data.get("scan_id") or data.get("id")
        if scan_id:
            time.sleep(2)
            ok2, data2, err2 = api_get(port, f"/scan/{scan_id}/status")
            results.append(TestResult("扫描状态 API", ok2, "" if ok2 else err2))

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# 主函数
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    print()
    print(f"{BOLD}{CYAN}  NextAgent 全功能测试{ RESET}")
    print(f"{BOLD}{CYAN}  {'─' * 46}{RESET}")

    all_results: list[tuple[str, TestResult]] = []

    modules = [
        ("AutoGLM",       test_autoglm),
        ("Browser-Use",   test_browser),
        ("API Testing",   test_api_testing),
        ("Security Scan", test_security),
    ]

    total_ok = 0
    total_fail = 0

    for name, test_fn in modules:
        print(f"\n  {BOLD}{CYAN}[{name}]{RESET}")
        try:
            results = test_fn()
        except Exception as e:
            print(f"  {RED}[ERROR] 测试模块异常: {e}{RESET}")
            continue

        for r in results:
            all_results.append((name, r))
            if r.ok:
                total_ok += 1
            else:
                total_fail += 1
            p(r.name, r.detail or ("OK" if r.ok else r.detail), r.ok)

    # ── 汇总 ─────────────────────────────────────────────────────────────────
    print()
    print(f"  {BOLD}{'─' * 46}{RESET}")
    print(f"  {BOLD}汇总:  {GREEN}通过={total_ok}  {RED}失败={total_fail}  总计={total_ok + total_fail}{RESET}")
    print(f"  {BOLD}{'─' * 46}{RESET}")
    print()

    # ── 列出失败的测试 ───────────────────────────────────────────────────────
    if total_fail > 0:
        print(f"  {RED}失败详情:{RESET}")
        for mod, r in all_results:
            if not r.ok:
                print(f"    {RED}  [{mod}] {r.name}{RESET}  {r.detail}")
        print()

    sys.exit(0 if total_fail == 0 else 1)


if __name__ == "__main__":
    main()
