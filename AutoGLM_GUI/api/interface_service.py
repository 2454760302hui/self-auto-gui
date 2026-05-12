"""API Interface Testing Service (FastAPI wrapper for httprunner-style runner).

This service wraps the interface/hui_core/runner.py module and exposes
REST API endpoints expected by frontend/lib/interface-api.ts.

Run standalone: python -m AutoGLM_GUI.api.interface_service
"""

import os
import sys
import time
import types
import threading
import io
import contextlib
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# ── Setup path ────────────────────────────────────────────────────────────────

_INTERFACE_ROOT = Path(__file__).resolve().parent.parent.parent / "interface"
sys.path.insert(0, str(_INTERFACE_ROOT))

# ── Environment Map ───────────────────────────────────────────────────────────

_ENVIRONMENTS = {
    "aliyun": {"name": "阿里云", "base_url": "https://api-c.soboten.com"},
    "tencent": {"name": "腾讯云", "base_url": "https://api-c.soboten.com"},
    "sg": {"name": "新加坡", "base_url": "https://sg-api-c.soboten.com"},
    "us": {"name": "美国", "base_url": "https://us-api-c.soboten.com"},
}

# ── Models ───────────────────────────────────────────────────────────────────

class RunTestRequest(BaseModel):
    yaml: str
    env: str = "aliyun"


class TestEndpointRequest(BaseModel):
    method: str = "GET"
    url: str
    data: dict | None = None


# ── FastAPI App ────────────────────────────────────────────────────────────────

app_interface = FastAPI(title="NextAgent API Interface Testing API", version="1.0.0")
app_interface.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helper: run YAML test ────────────────────────────────────────────────────

def _run_yaml_test(yaml_content: str, env_key: str) -> tuple[bool, str]:
    """Run YAML test case and capture output."""
    from hui_core.runner import RunYaml
    import yaml as yaml_mod
    from hui_core.log import log

    # Capture log output
    output = io.StringIO()
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
        old_level = log.level
        log.level = "INFO"

        try:
            raw = yaml_mod.safe_load(yaml_content)
            if not raw:
                return False, "Empty YAML content"

            # Create a fake module for the runner
            module = types.ModuleType("test_module")
            module.__file__ = "<yaml_test>"

            # Create globals with env base_url
            env_cfg = _ENVIRONMENTS.get(env_key, _ENVIRONMENTS["aliyun"])
            g = {"env": type("Env", (), {"BASE_URL": env_cfg["base_url"]})()}

            runner = RunYaml(raw, module, g)
            runner.run()
            return True, output.getvalue()

        except Exception as e:
            import traceback
            log.error(f"Test execution error: {e}")
            return False, f"{output.getvalue()}\n{e}\n{traceback.format_exc()}"
        finally:
            log.level = old_level


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app_interface.get("/health")
async def health():
    return {"status": "ok"}


@app_interface.post("/run")
async def run_test(req: RunTestRequest):
    """Run a YAML test case."""
    if not req.yaml.strip():
        return {"success": False, "error": "Empty YAML content"}

    success, output = _run_yaml_test(req.yaml, req.env)

    return {
        "success": success,
        "output": output if success else "",
        "error": None if success else output,
    }


@app_interface.get("/envs")
async def list_envs():
    """List available test environments."""
    envs = [
        {"name": data["name"], "base_url": data["base_url"], "description": f"{data['name']} 环境"}
        for key, data in _ENVIRONMENTS.items()
    ]
    return {"envs": envs}


@app_interface.post("/test-endpoint")
async def test_endpoint(req: TestEndpointRequest):
    """Test a single HTTP endpoint."""
    import httpx
    import time as time_module

    start = time_module.time()
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            kwargs = {"url": req.url}
            if req.method == "GET":
                kwargs["params"] = req.data
            elif req.method in ("POST", "PUT", "PATCH"):
                kwargs["json"] = req.data

            resp = await client.request(req.method, **kwargs)
            elapsed_ms = int((time_module.time() - start) * 1000)

            # Try to parse JSON body
            body = None
            try:
                body = resp.json()
            except Exception:
                body = resp.text[:500] if resp.text else None

            return {
                "success": resp.status_code < 400,
                "status_code": resp.status_code,
                "response_time_ms": elapsed_ms,
                "body": body,
            }
    except httpx.TimeoutException:
        return {"success": False, "error": "Request timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app_interface.post("/parse-yaml")
async def parse_yaml(req: dict):
    """Parse and validate YAML test case."""
    import yaml
    try:
        parsed = yaml.safe_load(req.get("yaml_content", ""))
        if not parsed:
            return {"success": False, "error": "Empty YAML"}
        return {
            "success": True,
            "test_case": {
                "name": "Parsed Test",
                "description": parsed.get("description", ""),
                "config": parsed.get("config", {}),
                "teststeps": parsed.get("teststeps", []),
            },
        }
    except yaml.YAMLError as e:
        return {"success": False, "error": f"YAML parse error: {e}"}


# ── Standalone runner ─────────────────────────────────────────────────────────

def run_standalone(host: str = "0.0.0.0", port: int = 9243):
    import uvicorn
    print(f"NextAgent API Interface Testing Service")
    print(f"  http://{host}:{port}")
    uvicorn.run(app_interface, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_standalone()
