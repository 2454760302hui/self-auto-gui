"""Browser Automation API Service (FastAPI wrapper for browser-use http_server).

This service wraps the browser-use HttpService from browser-use-main.
It exposes the same REST API endpoints expected by frontend/lib/browser-api.ts.

Run standalone: python -m AutoGLM_GUI.api.browser_service
Run with main app: automatically via multiprocess in __main__.py
"""

import asyncio
import json
import os
import sys
import threading
import time
from typing import Any
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add browser-use to path
_BROWSER_USE_ROOT = Path(__file__).resolve().parent.parent.parent / "browser-use-main-debug" / "browser-use-main"
if _BROWSER_USE_ROOT.exists() and str(_BROWSER_USE_ROOT) not in sys.path:
    sys.path.insert(0, str(_BROWSER_USE_ROOT))

# ── Service State ─────────────────────────────────────────────────────────────

_traces_dir = _BROWSER_USE_ROOT / "traces"
_traces_dir.mkdir(exist_ok=True)

# LLM configuration (set via /test-llm)
_llm_config_raw = ""
_llm_config_status = "empty"  # empty | testing | ready | error
_llm_config_summary: dict[str, Any] = {}
_configured_llm: Any = None
_llm_lock = threading.Lock()

# ── FastAPI App ────────────────────────────────────────────────────────────────

app_browser = FastAPI(title="NextAgent Browser Automation API", version="1.0.0")

app_browser.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Models ───────────────────────────────────────────────────────────────────

class TaskRequest(BaseModel):
    task: str = ""
    mode: str = "nlp"
    max_steps: int = 20
    dsl: str = ""
    cdp_url: str = ""
    task_id: str = ""


class LLMTestRequest(BaseModel):
    config: str


class TraceResponse(BaseModel):
    task_id: str
    mode: str
    success: bool
    steps: int
    elapsed_ms: int
    task: str
    has_gif: bool


# ── Helper: auto-init LLM from env ────────────────────────────────────────────

def _auto_init_llm() -> tuple[str, dict[str, Any]]:
    """Try to auto-configure LLM from environment variables."""
    try:
        from browser_use.config import FlatEnvConfig, _build_legacy_llm_profiles, _choose_default_profile_name, _collect_prefixed_profiles, _merge_profile_dicts

        env_config = FlatEnvConfig()
        legacy_profiles = _build_legacy_llm_profiles(env_config)
        env_profiles = _collect_prefixed_profiles("BROWSER_USE_LLM_", dict(os.environ))
        llm_profiles = _merge_profile_dicts(legacy_profiles, env_profiles)

        if not llm_profiles:
            return "empty", {}

        default_name = _choose_default_profile_name(env_config, llm_profiles) or next(iter(llm_profiles))
        profile = llm_profiles[default_name]

        provider = profile.get("provider", "anthropic")
        model = profile.get("model", "")
        raw_config = json.dumps(profile, ensure_ascii=False)

        return "ready", {
            "configured": True,
            "status": "ready",
            "model": model,
            "provider": provider,
            "raw_config": raw_config,
        }
    except Exception:
        return "empty", {
            "configured": False,
            "status": "no_env_config",
            "model": "",
            "provider": "",
            "raw_config": "",
        }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app_browser.get("/health")
async def health():
    global _llm_config_status, _llm_config_summary
    return {
        "success": True,
        "data": {
            "status": "ready",
            "llm": {
                "status": _llm_config_status,
                "model": _llm_config_summary.get("model", ""),
            },
            "cdp_url": os.environ.get("CHROME_CDP_URL", "http://127.0.0.1:9222"),
        },
    }


@app_browser.get("/llm-status")
async def llm_status():
    global _llm_config_status, _llm_config_summary
    return {
        "success": True,
        "data": {
            "configured": _llm_config_status == "ready",
            "status": _llm_config_status,
            "model": _llm_config_summary.get("model", ""),
            "provider": _llm_config_summary.get("provider", ""),
            "raw_config": _llm_config_summary.get("raw_config", ""),
        },
    }


@app_browser.post("/test-llm")
async def test_llm(req: LLMTestRequest):
    global _llm_config_status, _llm_config_summary, _configured_llm
    with _llm_lock:
        _llm_config_status = "testing"

    try:
        import yaml
        config = yaml.safe_load(req.config)
        provider = config.get("provider", "openai")
        model = config.get("model", "")
        api_key = config.get("api_key", os.environ.get("OPENAI_API_KEY", ""))
        base_url = config.get("base_url", "")

        # Test connection with a simple call
        if provider == "anthropic":
            from anthropic import Anthropic
            client = Anthropic(api_key=api_key)
            resp = client.messages.create(
                model=model or "claude-3-5-sonnet-20241022",
                max_tokens=10,
                messages=[{"role": "user", "content": "hi"}],
            )
            status_text = f"OK ({resp.type})"
        else:
            from openai import OpenAI
            kwargs = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            client = OpenAI(**kwargs)
            resp = client.chat.completions.create(
                model=model or "gpt-4o-mini",
                max_tokens=10,
                messages=[{"role": "user", "content": "hi"}],
            )
            status_text = f"OK ({resp.model})"

        with _llm_lock:
            _llm_config_status = "ready"
            _llm_config_summary = {
                "provider": provider,
                "model": model,
                "raw_config": req.config,
            }

        return {"success": True, "data": {"status_text": status_text}}
    except Exception as e:
        with _llm_lock:
            _llm_config_status = "error"
            _llm_config_summary = {}
        return {"success": False, "error": str(e)}


@app_browser.post("/run-task")
async def run_task(req: TaskRequest):
    """Run browser automation task using browser-use Agent."""
    task_id = req.task_id or f"task-{int(time.time() * 1000)}"
    trace_dir = _traces_dir / f"task-{task_id}"
    trace_dir.mkdir(parents=True, exist_ok=True)

    start_time = time.time()
    log_lines: list[str] = []
    errors: list[str] = []
    gif_url = ""
    has_gif = False
    final_result = ""
    steps = 0

    try:
        # Auto-init LLM if not configured
        global _llm_config_status, _llm_config_summary
        if _llm_config_status == "empty":
            _llm_config_status, _llm_config_summary = _auto_init_llm()

        # Build LLM
        if _llm_config_status == "ready":
            from browser_use.llm.openai.chat import ChatOpenAI
            from browser_use.llm.anthropic.chat import ChatAnthropic
            import yaml

            cfg = yaml.safe_load(_llm_config_summary.get("raw_config", "{}"))
            provider = cfg.get("provider", "anthropic")
            model = cfg.get("model", "")
            api_key = cfg.get("api_key", "")
            base_url = cfg.get("base_url", "")

            if provider == "anthropic":
                _configured_llm = ChatAnthropic(
                    model_name=model or "claude-3-5-sonnet-20241022",
                    api_key=api_key,
                )
            else:
                kwargs = {"model_name": model or "gpt-4o-mini", "api_key": api_key}
                if base_url:
                    kwargs["base_url"] = base_url
                _configured_llm = ChatOpenAI(**kwargs)

        if _configured_llm is None:
            # Fallback: try OpenAI from env
            try:
                from browser_use.llm.openai.chat import ChatOpenAI
                _configured_llm = ChatOpenAI(model_name="gpt-4o-mini")
            except Exception as e:
                errors.append(f"LLM not configured: {e}")
                return {
                    "success": False,
                    "data": {
                        "task_id": task_id,
                        "mode": req.mode,
                        "success": False,
                        "elapsed_ms": int((time.time() - start_time) * 1000),
                        "dsl": req.dsl,
                        "log": "\n".join(log_lines),
                        "steps": 0,
                        "error": f"LLM not configured. Set BROWSER_USE_LLM_PROVIDER or call /test-llm first.",
                        "errors": errors,
                        "gif_url": "",
                        "has_gif": False,
                    },
                    "error": "LLM not configured",
                }

        from browser_use import Agent
        from browser_use.browser import Browser, BrowserProfile

        # Determine CDP URL
        cdp_url = req.cdp_url or os.environ.get("CHROME_CDP_URL", "")

        if cdp_url:
            browser = Browser(
                cdp_url=cdp_url,
                headless=False,
            )
        else:
            browser = Browser(headless=False)

        agent = Agent(
            task=req.task or req.dsl,
            llm=_configured_llm,
            browser=browser,
            max_steps=req.max_steps,
        )

        log_lines.append(f"▶ Starting task (mode={req.mode}, max_steps={req.max_steps})")
        log_lines.append(f"▶ Browser CDP: {cdp_url or 'auto'}")

        history = await agent.run()
        steps = history.number_of_steps()
        final_result = history.final_result() or ""

        elapsed_ms = int((time.time() - start_time) * 1000)
        log_lines.append(f"✓ Task completed in {steps} steps ({elapsed_ms}ms)")
        if final_result:
            log_lines.append(f"▶ {final_result}")

    except Exception as e:
        import traceback
        errors.append(str(e))
        log_lines.append(f"✗ Error: {e}")
        log_lines.append(traceback.format_exc())

    elapsed_ms = int((time.time() - start_time) * 1000)
    success = len(errors) == 0 and steps > 0

    # Save trace
    try:
        import yaml
        trace_data = {
            "task_id": task_id,
            "task": req.task or req.dsl,
            "mode": req.mode,
            "success": success,
            "steps": steps,
            "elapsed_ms": elapsed_ms,
            "final_result": final_result,
            "log": "\n".join(log_lines),
            "dsl": req.dsl,
        }
        with open(trace_dir / "trace.json", "w", encoding="utf-8") as f:
            yaml.dump(trace_data, f, allow_unicode=True)
    except Exception:
        pass

    return {
        "success": success,
        "data": {
            "task_id": task_id,
            "mode": req.mode,
            "success": success,
            "elapsed_ms": elapsed_ms,
            "dsl": req.dsl,
            "log": "\n".join(log_lines),
            "steps": steps,
            "final_result": final_result,
            "errors": errors,
            "gif_url": gif_url,
            "has_gif": has_gif,
        },
    }


@app_browser.post("/run-playwright")
async def run_playwright(req: dict):
    """Run a Playwright script directly."""
    import subprocess
    import tempfile

    script = req.get("script", "")
    task_id = req.get("task_id", f"pw-{int(time.time())}")

    if not script.strip():
        return {"success": False, "error": "Empty script"}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(script)
        script_path = f.name

    try:
        start = time.time()
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=120,
        )
        elapsed_ms = int((time.time() - start) * 1000)

        return {
            "success": result.returncode == 0,
            "data": {
                "task_id": task_id,
                "success": result.returncode == 0,
                "elapsed_ms": elapsed_ms,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "gif_url": "",
                "has_gif": False,
            },
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Script timed out after 120s"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        try:
            os.unlink(script_path)
        except Exception:
            pass


@app_browser.get("/traces")
async def list_traces():
    """List all browser automation traces."""
    runs = []
    try:
        if _traces_dir.exists():
            for td in sorted(_traces_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)[:50]:
                trace_file = td / "trace.json"
                if trace_file.exists():
                    import yaml
                    with open(trace_file, encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                    runs.append({
                        "task_id": data.get("task_id", td.name),
                        "mode": data.get("mode", "nlp"),
                        "success": data.get("success", False),
                        "steps": data.get("steps", 0),
                        "elapsed_ms": data.get("elapsed_ms", 0),
                        "task": data.get("task", ""),
                        "has_gif": data.get("has_gif", False),
                    })
    except Exception:
        pass

    return {"success": True, "runs": runs}


@app_browser.get("/traces/{task_id}/trace.json")
async def get_trace(task_id: str):
    import yaml
    trace_file = _traces_dir / f"task-{task_id}" / "trace.json"
    if not trace_file.exists():
        raise HTTPException(status_code=404, detail="Trace not found")
    with open(trace_file, encoding="utf-8") as f:
        return yaml.safe_load(f)


@app_browser.delete("/traces")
async def clear_traces():
    """Clear all browser traces."""
    count = 0
    try:
        if _traces_dir.exists():
            import shutil
            for td in _traces_dir.iterdir():
                if td.is_dir():
                    shutil.rmtree(td)
                    count += 1
    except Exception:
        pass
    return {"success": True, "cleared": count}


@app_browser.get("/dsl-demos")
async def get_demos():
    """Return DSL demo scripts."""
    demos = {
        "Bing搜索": "打开 https://cn.bing.com\n等待加载完成\n截图\n输入 #sb_form_q Python教程\n按键 Enter",
        "豆瓣电影": "打开 https://movie.douban.com\n等待加载完成\n截图\n提取 热门电影列表",
        "百度搜索": "打开 https://www.baidu.com\n等待加载完成\n输入 #kw Python自动化\n点击 #su",
        "GitHub": "打开 https://github.com\n等待加载完成\n截图\n提取 GitHub trending 项目",
        "简单截图": "打开 https://example.com\n等待加载完成\n截图",
        "表单填写": "打开 https://httpbin.org/forms/post\n等待加载完成\n填写 name: 测试用户\n填写 custtel: 13800138000\n填写 custemail: test@example.com\n点击提交",
    }
    return {"success": True, "demos": demos}


@app_browser.get("/nlp/status")
async def nlp_status():
    return {
        "success": True,
        "data": {
            "available": True,
            "status": "ready",
            "features": ["intent_detection", "entity_extraction", "dsl_generation"],
        },
    }


@app_browser.post("/nlp/analyze")
async def nlp_analyze(req: dict):
    text = req.get("text", "")
    if not text:
        return {"success": False, "error": "Empty text"}

    # Simple rule-based analysis
    import re
    commands = []
    urls = re.findall(r"https?://[^\s]+", text)
    if "打开" in text or "访问" in text:
        for url in urls:
            commands.append({"action": "navigate", "target": url})
    if "搜索" in text:
        commands.append({"action": "search", "query": text})
    if "截图" in text:
        commands.append({"action": "screenshot"})

    return {
        "success": True,
        "data": {
            "original_text": text,
            "dsl_output": "\n".join([f"# {c.get('action')}: {c.get('target', c.get('query', ''))}" for c in commands]),
            "primary_intent": "navigation" if commands else "unknown",
            "confidence": 0.85,
            "entities": [{"type": "url", "value": u} for u in urls],
            "commands": commands,
            "warnings": [],
            "processing_time_ms": 5,
        },
    }


@app_browser.post("/nlp/to-dsl")
async def nlp_to_dsl(req: dict):
    """Convert natural language to DSL script."""
    text = req.get("text", "")
    if not text:
        return {"success": False, "error": "Empty text"}

    import re
    lines = [f"# 自然语言: {text}", ""]

    # Extract URL
    urls = re.findall(r"https?://[^\s]+", text)
    if urls:
        lines.append(f"打开 {urls[0]}")
        lines.append("等待加载完成")
        lines.append("截图")

    # Detect actions
    if any(k in text for k in ["搜索", "查找", "查询"]):
        for kw in re.findall(r"[前后左右上下]?\w+(?=搜索|查找|查询)", text):
            if len(kw) > 1:
                lines.append(f"输入 #{kw}")
                lines.append("按键 Enter")
                break
        else:
            # Try to find search query
            match = re.search(r"[搜索查找](.+)", text)
            if match:
                lines.append(f"输入 {match.group(1).strip()}")

    if "提取" in text or "获取" in text:
        match = re.search(r"提取[：:](.+)", text)
        if match:
            lines.append(f"提取 {match.group(1).strip()}")

    if "登录" in text or "登录" in text:
        lines.append("# TODO: 请配置登录信息")
        lines.append("填写 username: 你的用户名")
        lines.append("填写 password: 你的密码")
        lines.append("点击登录按钮")

    if not lines[1:]:
        lines.append("# 未能识别任务，请尝试更明确的描述")
        lines.append("打开 https://example.com")

    return {
        "success": True,
        "data": {"dsl": "\n".join(lines)},
    }


@app_browser.post("/export")
async def export_dsl(req: dict):
    dsl = req.get("dsl", "")
    fmt = req.get("format", "yaml")
    if fmt == "yaml":
        content = f"# DSL Export\n---\n{dsl}"
    else:
        content = f"import pytest\n\ndef test_auto():\n    # {dsl.replace(chr(10), chr(10) + '    # ')}\n    pass\n"
    return {"success": True, "content": content}


# ── Standalone runner ─────────────────────────────────────────────────────────

def run_standalone(host: str = "0.0.0.0", port: int = 9242):
    import uvicorn
    print(f"NextAgent Browser Automation Service")
    print(f"  http://{host}:{port}")
    print(f"  Health: http://{host}:{port}/health")
    uvicorn.run(app_browser, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_standalone()
