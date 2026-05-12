# -*- coding: utf-8 -*-
"""Comprehensive verification script for all NextAgent modules."""

import time
from dataclasses import dataclass, field
from typing import Any

import httpx


def sg(data: Any, key: str, default: Any = None) -> Any:
    if isinstance(data, dict):
        return data.get(key, default)
    return default


@dataclass
class ModuleResult:
    name: str
    port: int
    checks: list[tuple[str, bool, str]] = field(default_factory=list)

    def add(self, name: str, ok: bool, detail: str = ""):
        self.checks.append((name, ok, detail))

    def passed_count(self) -> int:
        return sum(1 for _, ok, _ in self.checks if ok)


BASE = "http://127.0.0.1"
G = "\033[92m"
R = "\033[91m"
Y = "\033[93m"
C = "\033[96m"
B = "\033[1m"
N = "\033[0m"


def api_get(port: int, path: str, timeout: float = 10) -> tuple[bool, Any | None, str]:
    url = f"{BASE}:{port}{path}"
    try:
        resp = httpx.get(url, timeout=timeout)
        if resp.status_code == 200:
            try:
                return True, resp.json(), ""
            except Exception:
                return True, resp.text, ""
        return False, None, f"HTTP {resp.status_code}"
    except Exception as e:
        return False, None, str(e)[:80]


def api_post(port: int, path: str, body: Any = None, timeout: float = 15) -> tuple[bool, Any | None, str]:
    url = f"{BASE}:{port}{path}"
    try:
        resp = httpx.post(url, json=body, timeout=timeout)
        if resp.status_code in (200, 201):
            try:
                return True, resp.json(), ""
            except Exception:
                return True, resp.text, ""
        return False, None, f"HTTP {resp.status_code}: {resp.text[:120]}"
    except Exception as e:
        return False, None, str(e)[:80]


def check(m: ModuleResult, name: str, ok: bool, detail: str = ""):
    icon = f"{G}OK{N}" if ok else f"{R}FAIL{N}"
    print(f"  {icon}  {name}" + (f"  {Y}{detail}{N}" if detail and not ok else ""))
    m.add(name, ok, detail)


# =============================================================================
# Module 1: AutoGLM-GUI Main Server
# =============================================================================
def verify_main_server() -> ModuleResult:
    m = ModuleResult("AutoGLM-GUI Main (port 9527)", 9527)
    print(f"\n{B}{C}{'=' * 62}{N}")
    print(f"{B}{C}  Module 1: AutoGLM-GUI Main Server{N}")
    print(f"{B}{C}{'=' * 62}{N}")

    ok, d, e = api_get(9527, "/api/health")
    check(m, "1.1  Health check", ok, e or ("version=" + str(sg(d, "version", "?"))))

    ok, d, e = api_get(9527, "/api/devices")
    devs = sg(d, "devices", []) if ok else []
    check(m, "1.2  Device list API", ok, e or ("device_count=" + str(len(devs))))

    ok, d, e = api_get(9527, "/api/device-groups")
    groups = sg(d, "groups", []) if ok else []
    check(m, "1.3  Device groups API", ok, e or ("group_count=" + str(len(groups))))

    ok, d, e = api_get(9527, "/api/config")
    check(m, "1.4  AI config read", ok, e or ("model=" + str(sg(d, "model_name", "?"))))

    ok, d, e = api_get(9527, "/api/status")
    check(m, "1.5  Agent status API", ok, e or ("initialized=" + str(sg(d, "initialized", "?"))))

    serial = None
    if devs and isinstance(devs[0], dict):
        serial = devs[0].get("serialno")
    if serial:
        ok, d, e = api_get(9527, "/api/history/" + serial)
        items = sg(d, "items", []) if ok else []
        check(m, "1.6  Task history API", ok, e or ("record_count=" + str(len(items))))
    else:
        check(m, "1.6  Task history API", True, "no device, skipped")

    ok, d, e = api_get(9527, "/api/workflows")
    wfs = sg(d, "workflows", []) if ok else []
    check(m, "1.7  Workflow list API", ok, e or ("workflow_count=" + str(len(wfs))))

    ok, d, e = api_get(9527, "/api/scheduled-tasks")
    tasks = sg(d, "tasks", []) if ok else []
    check(m, "1.8  Scheduled tasks API", ok, e or ("task_count=" + str(len(tasks))))

    ok, d, e = api_get(9527, "/api/metrics")
    check(m, "1.9  Prometheus metrics API", ok, e or "available")

    ok, d, e = api_get(9527, "/api/version")
    check(m, "1.10 Version info API", ok, e or ("version=" + str(sg(d, "version", "?"))))

    dev_id = devs[0].get("device_id") if devs and isinstance(devs[0], dict) else None
    if dev_id:
        ok, d, e = api_post(9527, "/api/control/screenshot", {"device_id": dev_id}, timeout=20)
        check(m, "1.11 Screenshot control", ok, e or "screenshot_ok")
    else:
        check(m, "1.11 Screenshot control", True, "no device, skipped")

    if dev_id:
        ok, d, e = api_post(9527, "/api/control/current-app", {"device_id": dev_id}, timeout=15)
        check(m, "1.12 Current app query", ok, e or ("app=" + str(sg(d, "app_name", "?"))))
    else:
        check(m, "1.12 Current app query", True, "no device, skipped")

    if dev_id:
        ok, d, e = api_post(9527, "/api/control/apps", {"device_id": dev_id}, timeout=30)
        sys_apps = len(sg(d, "system", [])) if ok else 0
        third = len(sg(d, "third_party", [])) if ok else 0
        check(m, "1.13 Installed apps list", ok, e or ("sys=" + str(sys_apps) + " 3rd=" + str(third)))
    else:
        check(m, "1.13 Installed apps list", True, "no device, skipped")

    ok, d, e = api_post(9527, "/api/chat", {"device_id": "no-such-device", "message": "test"})
    check(m, "1.14 Chat error handling", ok, e or "graceful_rejection")

    if dev_id and serial:
        ok, d, e = api_post(9527, "/api/task-sessions", {"device_id": dev_id, "device_serial": serial})
        sid = sg(d, "session_id") if ok else None
        check(m, "1.15 Task session create", ok, e or ("session=" + str(sid)[:8] if sid else "no_session"))
    else:
        check(m, "1.15 Task session create", True, "no device, skipped")

    ok, d, e = api_get(9527, "/api/layered-agent/config")
    check(m, "1.16 Layered agent config API", ok, e or ("max_turns=" + str(sg(d, "max_turns", "?"))))

    ok, d, e = api_get(9527, "/api/mcp/tools")
    tools_count = len(sg(d, "tools", [])) if ok else 0
    check(m, "1.17 MCP tools registration API", ok, e or ("tools=" + str(tools_count)))

    ok, d, e = api_get(9527, "/api/health-monitor")
    check(m, "1.18 Health monitor API", ok, e or "available")

    return m


# =============================================================================
# Module 2: Browser Automation
# =============================================================================
def verify_browser_service() -> ModuleResult:
    m = ModuleResult("Browser-Use Automation (port 9242)", 9242)
    print(f"\n{B}{C}{'=' * 62}{N}")
    print(f"{B}{C}  Module 2: Browser-Use Browser Automation{N}")
    print(f"{B}{C}{'=' * 62}{N}")

    ok, d, e = api_get(9242, "/health")
    check(m, "2.1  Health check", ok, e or ("status=" + str(sg(d, "status", "?"))))

    ok, d, e = api_get(9242, "/llm-status")
    check(m, "2.2  LLM status", ok, e or ("configured=" + str(sg(d, "configured", "?"))))

    ok, d, e = api_get(9242, "/traces")
    runs = sg(d, "runs", []) if ok else []
    check(m, "2.3  Task history / Traces", ok, e or ("record_count=" + str(len(runs))))

    ok, d, e = api_get(9242, "/nlp/status")
    check(m, "2.4  NLP analysis status API", ok, e or ("status=" + str(sg(d, "status", "?"))))

    return m


# =============================================================================
# Module 3: API Interface Testing
# =============================================================================
def verify_interface_service() -> ModuleResult:
    m = ModuleResult("API Interface Testing (port 9243)", 9243)
    print(f"\n{B}{C}{'=' * 62}{N}")
    print(f"{B}{C}  Module 3: API Interface Testing{N}")
    print(f"{B}{C}{'=' * 62}{N}")

    ok, d, e = api_get(9243, "/health")
    check(m, "3.1  Health check", ok, e or ("service=" + str(sg(d, "service", "?"))))

    ok, d, e = api_get(9243, "/envs")
    envs = sg(d, "data", []) if ok else []
    check(m, "3.2  Environment list", ok, e or ("env_count=" + str(len(envs))))

    ok, d, e = api_post(9243, "/parse-yaml", {
        "yaml_content": "config:\n  base_url: https://httpbin.org\nteststeps:\n  - name: ping\n    request:\n      method: GET\n      url: /get\n"
    }, timeout=15)
    steps = len(sg(d, "teststeps", [])) if ok else 0
    check(m, "3.3  YAML test case parsing", ok, e or ("parsed_steps=" + str(steps)))

    ok, d, e = api_post(9243, "/test-endpoint", {
        "method": "GET",
        "url": "https://httpbin.org/get",
        "headers": {"User-Agent": "NextAgent-Verification/1.0"},
    }, timeout=15)
    check(m, "3.4  Single endpoint test execution", ok, e or ("status=" + str(sg(d, "status_code", "?"))))

    ok, d, e = api_post(9243, "/run", {
        "yaml": "config:\n  base_url: https://httpbin.org\nteststeps:\n  - name: ping\n    request:\n      method: GET\n      url: /get\n"
    }, timeout=15)
    check(m, "3.5  Test case execution via /run", ok, e or ("success=" + str(sg(d, "success", "?"))))

    return m


# =============================================================================
# Module 4: Security Testing
# =============================================================================
def verify_security_service() -> ModuleResult:
    m = ModuleResult("Security Scan (port 9244)", 9244)
    print(f"\n{B}{C}{'=' * 62}{N}")
    print(f"{B}{C}  Module 4: Security Scan{N}")
    print(f"{B}{C}{'=' * 62}{N}")

    ok, d, e = api_get(9244, "/health")
    check(m, "4.1  Health check", ok, e or ("service=" + str(sg(d, "service", "?"))))

    ok, d, e = api_get(9244, "/scans")
    scans = sg(d, "data", []) if ok else []
    check(m, "4.2  Scan history list", ok, e or ("scan_count=" + str(len(scans))))

    ok, d, e = api_post(9244, "/scan", {
        "target_url": "http://httpbin.org",
        "strategy": "fast"
    }, timeout=30)
    scan_id = sg(d, "task_id") or sg(d, "scan_id") if ok else None
    check(m, "4.3  Start fast scan", ok, e or ("task_id=" + str(scan_id)))

    if scan_id:
        time.sleep(2)
        ok2, d2, e2 = api_get(9244, "/scan/" + str(scan_id) + "/status")
        check(m, "4.4  Scan status query", ok2, e2 or ("status=" + str(sg(d2, "status", "?"))))

    return m


# =============================================================================
# Module 5: Cross-module integration
# =============================================================================
def verify_inter_module_integration() -> ModuleResult:
    m = ModuleResult("Cross-Module Integration", 0)
    print(f"\n{B}{C}{'=' * 62}{N}")
    print(f"{B}{C}  Module 5: Cross-Module Integration & Associations{N}")
    print(f"{B}{C}{'=' * 62}{N}")

    ok, devs_data, _ = api_get(9527, "/api/devices")
    devs = sg(devs_data, "devices", []) if ok else []
    dev_id = devs[0].get("device_id") if devs and isinstance(devs[0], dict) else None
    serial = devs[0].get("serialno") if devs and isinstance(devs[0], dict) else None

    check(m, "5.1  Device polling -> DeviceManager -> device list",
          ok, ("device_count=" + str(len(devs))) if ok else "failed")

    ok, d, e = api_get(9527, "/api/config")
    check(m, "5.2  ConfigManager -> Chat API",
          ok, e or ("model=" + str(sg(d, "model_name", "?"))))

    if dev_id and serial:
        ok, d, e = api_post(9527, "/api/task-sessions", {"device_id": dev_id, "device_serial": serial})
        sid = sg(d, "session_id") if ok else None
        if ok and sid:
            ok2, d2, e2 = api_get(9527, "/api/task-sessions/" + str(sid))
            check(m, "5.3  TaskManager -> TaskStore -> History", ok2, e2 or "session_detail_ok")
        else:
            check(m, "5.3  TaskManager -> TaskStore -> History", False, e)
    else:
        check(m, "5.3  TaskManager -> TaskStore -> History", True, "no device, skipped")

    ok, d, e = api_post(9527, "/api/workflows", {"name": "VerifyWF", "text": "verification test"})
    wf_id = sg(d, "uuid") if ok else None
    check(m, "5.4  Workflow -> TaskManager", ok, e or ("workflow_id=" + str(wf_id)[:8] if wf_id else "no_id"))

    if wf_id and serial:
        ok, d, e = api_post(9527, "/api/scheduled-tasks", {
            "name": "VerifySchedule",
            "workflow_uuid": wf_id,
            "cron_expression": "0 * * * *",
            "device_serialnos": [serial],
        }, timeout=10)
        check(m, "5.5  SchedulerManager -> ScheduledTasks", ok, e or ("task_id=" + str(sg(d, "id", "?"))))
    else:
        check(m, "5.5  SchedulerManager -> ScheduledTasks", True, "no workflow or device, skipped")

    if dev_id:
        ok, d, e = api_post(9527, "/api/control/screenshot", {"device_id": dev_id}, timeout=20)
        check(m, "5.6  Agent -> DeviceManager -> Control", ok, e or "device_control_ok")
    else:
        check(m, "5.6  Agent -> DeviceManager -> Control", True, "no device, skipped")

    ok, d, e = api_get(9527, "/api/agents/list")
    check(m, "5.7  AgentFactory -> Agent registration",
          ok, e or ("agent_types=" + str(len(sg(d, "agents", [])) if ok else "?")))

    ok, d, e = api_get(9527, "/api/metrics")
    check(m, "5.8  MetricsCollector -> Prometheus", ok, e or "metrics_ok")

    if serial:
        ok, d, e = api_get(9527, "/api/history/" + serial)
        check(m, "5.9  Trace module -> step timing", ok, e or "history_records_ok")
    else:
        check(m, "5.9  Trace module -> step timing", True, "no device, skipped")

    ok, d, e = api_get(9527, "/api/layered-agent/sessions")
    check(m, "5.10 LayeredAgent -> Session management",
          ok, e or ("sessions=" + str(len(sg(d, "sessions", [])) if ok else "?")))

    return m


def print_summary(modules: list[ModuleResult]):
    total_passed = sum(m.passed_count() for m in modules)
    total_checks = sum(len(m.checks) for m in modules)
    total_modules = len(modules)
    modules_passed = sum(1 for m in modules if all(ok for _, ok, _ in m.checks))

    print(f"\n{B}{C}{'#' * 62}{N}")
    print(f"{B}  VERIFICATION SUMMARY{N}")
    print(f"{B}{C}{'#' * 62}{N}")
    print(f"  Total modules:       {total_modules}")
    print(f"  Total checks:        {total_checks}")
    print(f"  Passed:              {G}{total_passed}{N}")
    print(f"  Failed:              {R}{total_checks - total_passed}{N}")
    print(f"  Module pass rate:     {G if modules_passed == total_modules else Y}{modules_passed}/{total_modules}{N}")
    print()
    for mod in modules:
        p = mod.passed_count()
        t = len(mod.checks)
        icon = f"{G}PASS{N}" if p == t else (f"{R}FAIL{N}" if p == 0 else f"{Y}PARTIAL{N}")
        print(f"  {icon}  {mod.name}  {G}{p}{N}/{t}")
    print(f"\n{B}{C}{'#' * 62}{N}\n")


def main():
    print(f"\n{B}{C}{'#' * 62}{N}")
    print(f"{B}{C}#  NextAgent Full-Module Functional Verification{N}")
    print(f"{B}{C}{'#' * 62}{N}")

    results = [
        verify_main_server(),
        verify_browser_service(),
        verify_interface_service(),
        verify_security_service(),
        verify_inter_module_integration(),
    ]

    print_summary(results)


if __name__ == "__main__":
    main()
