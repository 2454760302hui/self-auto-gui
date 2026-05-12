"""Security Testing API Service (FastAPI wrapper for Xray + Rad scanner).

This service wraps the security/core/scanner.py module and exposes
REST API endpoints expected by frontend/lib/security-api.ts.

Run standalone: python -m AutoGLM_GUI.api.security_service
"""

import os
import sys
import time
import threading
import uuid
from pathlib import Path
from typing import Any
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Setup path ────────────────────────────────────────────────────────────────

_SERVICE_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_SERVICE_ROOT))

# ── Models ───────────────────────────────────────────────────────────────────

class ScanRequest(BaseModel):
    target_url: str
    scan_type: str = "quick"  # quick | full | xss | sqli | cmd
    enable_auth: bool = False
    auth_username: str = ""
    auth_password: str = ""


class TestEndpointRequest(BaseModel):
    url: str


# ── Service State ─────────────────────────────────────────────────────────────

_scan_lock = threading.Lock()
_active_scans: dict[str, dict[str, Any]] = {}
_scan_history: list[dict[str, Any]] = []
_executor = ThreadPoolExecutor(max_workers=3)

# Output directory for reports
_REPORTS_DIR = _SERVICE_ROOT / "reports"
_REPORTS_DIR.mkdir(exist_ok=True)

# ── FastAPI App ───────────────────────────────────────────────────────────────

app_security = FastAPI(title="NextAgent Security Testing API", version="1.0.0")
app_security.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Internal: run scan in thread ─────────────────────────────────────────────

def _run_scan_thread(task_id: str, target_url: str, scan_type: str):
    """Execute the security scan in a background thread."""
    from security.core.scanner import Scanner
    from security.core.config import ScanConfig

    scan = _active_scans.get(task_id)
    if not scan:
        return

    try:
        # Build config
        config = ScanConfig()
        config.targets = [target_url]
        config.output_dir = str(_REPORTS_DIR)
        config.scan_type = scan_type

        # Quick = baseline + xss + sqli
        if scan_type == "quick":
            config.enabled_plugins = ["baseline", "xss", "sqldet"]
        elif scan_type == "full":
            config.enabled_plugins = ["baseline", "brute-force", "cmd-injection", "sqldet", "xss", "xxe"]
        elif scan_type == "xss":
            config.enabled_plugins = ["xss"]
        elif scan_type == "sqli":
            config.enabled_plugins = ["sqldet"]
        elif scan_type == "cmd":
            config.enabled_plugins = ["cmd-injection"]

        scanner = Scanner(config)
        missing = scanner.check_prerequisites()
        if missing:
            scan["status"] = "failed"
            scan["message"] = f"Missing prerequisites: {', '.join(missing)}"
            return

        with scanner:
            scan["status"] = "running"
            results = scanner.scan_all([target_url], concurrent=False)
            scanner.wait_for_results()

        # Read results
        scan_info = scanner.get_results()
        json_path = scan_info.get("json_output", "")
        vulns: list[dict[str, Any]] = []

        if json_path and os.path.exists(json_path):
            import json
            try:
                raw = json.loads(open(json_path, encoding="utf-8").read())
                # Xray output format: list of vulns
                if isinstance(raw, list):
                    for v in raw:
                        vulns.append({
                            "id": str(uuid.uuid4())[:8],
                            "name": v.get("plugin", "unknown"),
                            "target": target_url,
                            "severity": v.get("severity", "info"),
                            "vuln_type": v.get("type", "unknown"),
                            "url": v.get("url", target_url),
                            "detail": v.get("detail", ""),
                            "payload": v.get("payload", ""),
                            "timestamp": v.get("create_time", time.strftime("%Y-%m-%dT%H:%M:%S")),
                        })
                elif isinstance(raw, dict):
                    vulns.append({
                        "id": str(uuid.uuid4())[:8],
                        "name": raw.get("plugin", "unknown"),
                        "target": target_url,
                        "severity": raw.get("severity", "info"),
                        "vuln_type": raw.get("type", "unknown"),
                        "url": raw.get("url", target_url),
                        "detail": raw.get("detail", ""),
                        "payload": raw.get("payload", ""),
                        "timestamp": raw.get("create_time", time.strftime("%Y-%m-%dT%H:%M:%S")),
                    })
            except Exception:
                pass

        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for v in vulns:
            sev = v.get("severity", "info")
            if sev in severity_counts:
                severity_counts[sev] += 1

        scan["status"] = "completed"
        scan["vulns_found"] = len(vulns)
        scan["vulns"] = vulns
        scan["severity_counts"] = severity_counts
        scan["json_output"] = json_path

        # Add to history
        _scan_history.insert(0, {
            "task_id": task_id,
            "target_url": target_url,
            "scan_type": scan_type,
            "severity_counts": severity_counts,
            "total": len(vulns),
            "scanned_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "duration_ms": int((time.time() - scan["start_time"]) * 1000),
        })

    except Exception as e:
        import traceback
        scan["status"] = "failed"
        scan["message"] = str(e)
        scan["error_detail"] = traceback.format_exc()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app_security.get("/health")
async def health():
    return {"status": "ok"}


@app_security.post("/scan")
async def start_scan(req: ScanRequest):
    """Start a new security scan."""
    with _scan_lock:
        task_id = f"scan-{int(time.time() * 1000)}-{uuid.uuid4().hex[:6]}"
        _active_scans[task_id] = {
            "task_id": task_id,
            "target_url": req.target_url,
            "scan_type": req.scan_type,
            "status": "pending",
            "progress_percent": 0,
            "vulns_found": 0,
            "start_time": time.time(),
            "vulns": [],
            "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
        }

    _executor.submit(_run_scan_thread, task_id, req.target_url, req.scan_type)

    return {"success": True, "task_id": task_id, "message": "Scan started"}


@app_security.get("/scan/{task_id}/status")
async def scan_status(task_id: str):
    scan = _active_scans.get(task_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    progress = 0
    if scan["status"] == "pending":
        progress = 5
    elif scan["status"] == "running":
        progress = 50
    elif scan["status"] == "completed":
        progress = 100
    elif scan["status"] == "failed":
        progress = 0

    return {
        "success": True,
        "status": scan["status"],
        "progress_percent": progress,
        "vulns_found": scan.get("vulns_found", 0),
        "message": scan.get("message", ""),
        "error": scan.get("message") if scan["status"] == "failed" else None,
    }


@app_security.get("/scan/{task_id}/result")
async def scan_result(task_id: str):
    scan = _active_scans.get(task_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    if scan["status"] not in ("completed", "failed"):
        raise HTTPException(status_code=202, detail="Scan not yet complete")

    return {
        "success": scan["status"] == "completed",
        "task_id": task_id,
        "elapsed_ms": int((time.time() - scan["start_time"]) * 1000),
        "target_url": scan["target_url"],
        "scan_type": scan["scan_type"],
        "vuln_count": scan.get("vulns_found", 0),
        "vulns": scan.get("vulns", []),
        "stdout": "",
        "stderr": scan.get("error_detail", ""),
        "error": scan.get("message") if scan["status"] == "failed" else None,
    }


@app_security.get("/scans")
async def list_scans():
    """List all scan history."""
    return {"success": True, "scans": _scan_history[:50]}


@app_security.delete("/scan/{task_id}")
async def delete_scan(task_id: str):
    if task_id in _active_scans:
        del _active_scans[task_id]
    for i, s in enumerate(_scan_history):
        if s["task_id"] == task_id:
            _scan_history.pop(i)
            break
    return {"success": True}


@app_security.get("/scan/{task_id}/export")
async def export_report(task_id: str, format: str = "json"):
    scan = _active_scans.get(task_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    if format == "json":
        import json
        content = json.dumps({
            "task_id": task_id,
            "target_url": scan["target_url"],
            "scan_type": scan["scan_type"],
            "vulns": scan.get("vulns", []),
            "severity_counts": scan.get("severity_counts", {}),
        }, indent=2, ensure_ascii=False)
    else:
        # HTML format
        vulns = scan.get("vulns", [])
        rows = ""
        for v in vulns:
            rows += f"<tr><td>{v.get('severity','')}</td><td>{v.get('name','')}</td><td>{v.get('url','')}</td></tr>"
        content = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Security Report {task_id}</title></head>
<body><h1>Security Scan Report</h1>
<p>Target: {scan['target_url']}</p>
<p>Type: {scan['scan_type']}</p>
<table border="1" cellpadding="5">
<tr><th>Severity</th><th>Vulnerability</th><th>URL</th></tr>
{rows}
</table></body></html>"""

    return {"success": True, "report_content": content}


@app_security.post("/test-endpoint")
async def test_endpoint(req: TestEndpointRequest):
    """Test connectivity to a target URL."""
    import httpx
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(req.url, follow_redirects=True)
            elapsed_ms = int((time.time() - start) * 1000)
            return {
                "success": True,
                "status_code": resp.status_code,
                "response_time_ms": elapsed_ms,
                "headers": dict(resp.headers),
                "server": resp.headers.get("server", ""),
                "powered_by": resp.headers.get("x-powered-by", ""),
            }
    except httpx.TimeoutException:
        return {"success": False, "error": "Connection timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── Standalone runner ────────────────────────────────────────────────────────

def run_standalone(host: str = "0.0.0.0", port: int = 9244):
    import uvicorn
    print(f"NextAgent Security Testing Service")
    print(f"  http://{host}:{port}")
    uvicorn.run(app_security, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_standalone()
