"""
NexusAgent 安全测试服务
封装 Xray + Rad 漏洞扫描引擎
"""
import asyncio
import json
import os
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ─────────────────────────────────────────────────────────────────────────────
# 模型定义
# ─────────────────────────────────────────────────────────────────────────────

class ScanRequest(BaseModel):
    target_url: str
    scan_type: str = "quick"  # quick, full, xss, sqli, cmd


class VulnInfo(BaseModel):
    id: str
    name: str
    severity: str  # critical, high, medium, low, info
    url: str
    vuln_type: str
    detail: str
    payload: Optional[str] = None
    timestamp: str


class ScanStatus(BaseModel):
    task_id: str
    status: str  # pending, running, completed, failed
    progress_percent: int
    vulns_found: int
    message: str


class ScanSummary(BaseModel):
    task_id: str
    target_url: str
    scan_type: str
    status: str
    total: int
    severity_counts: Dict[str, int]
    duration_ms: int


# ─────────────────────────────────────────────────────────────────────────────
# 扫描引擎配置
# ─────────────────────────────────────────────────────────────────────────────

SECURITY_DIR = Path(__file__).parent.parent / "security"
XRAY_PATH = SECURITY_DIR / "Xray_Rad_complete" / "xray_windows_amd64.exe"
RAD_PATH = SECURITY_DIR / "Xray_Rad_complete" / "rad_windows_amd64.exe"


# ─────────────────────────────────────────────────────────────────────────────
# 扫描任务存储
# ─────────────────────────────────────────────────────────────────────────────

_scan_tasks: Dict[str, Dict[str, Any]] = {}


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI 应用
# ─────────────────────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title="NexusAgent Security Scan Service",
        description="Xray + Rad 漏洞扫描服务",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "security"}

    @app.post("/scan")
    async def start_scan(request: ScanRequest):
        """启动安全扫描"""
        task_id = str(uuid.uuid4())[:8]

        # 初始化任务状态
        _scan_tasks[task_id] = {
            "target_url": request.target_url,
            "scan_type": request.scan_type,
            "status": "pending",
            "progress": 0,
            "vulns": [],
            "start_time": time.time(),
            "end_time": None,
        }

        # 异步执行扫描
        asyncio.create_task(_run_scan(task_id, request))

        return {"success": True, "task_id": task_id}

    @app.get("/scan/{task_id}/status")
    async def get_scan_status(task_id: str):
        """获取扫描状态"""
        if task_id not in _scan_tasks:
            return {"error": "Task not found"}

        task = _scan_tasks[task_id]
        elapsed = int((time.time() - task["start_time"]) * 1000)

        return ScanStatus(
            task_id=task_id,
            status=task["status"],
            progress_percent=task["progress"],
            vulns_found=len(task["vulns"]),
            message="扫描进行中" if task["status"] == "running" else "扫描完成",
        )

    @app.get("/scan/{task_id}/result")
    async def get_scan_result(task_id: str):
        """获取扫描结果"""
        if task_id not in _scan_tasks:
            return {"success": False, "error": "Task not found"}

        task = _scan_tasks[task_id]
        return {
            "success": True,
            "vulns": task["vulns"],
            "summary": {
                "total": len(task["vulns"]),
                "by_severity": _count_by_severity(task["vulns"]),
            },
        }

    @app.get("/scans")
    async def list_scans():
        """列出所有扫描任务"""
        scans = []
        for task_id, task in _scan_tasks.items():
            scans.append(ScanSummary(
                task_id=task_id,
                target_url=task["target_url"],
                scan_type=task["scan_type"],
                status=task["status"],
                total=len(task["vulns"]),
                severity_counts=_count_by_severity(task["vulns"]),
                duration_ms=int((task["end_time"] or time.time()) - task["start_time"]) * 1000 if task["end_time"] else 0,
            ))
        return {"scans": scans}

    @app.delete("/scan/{task_id}")
    async def delete_scan(task_id: str):
        """删除扫描记录"""
        if task_id in _scan_tasks:
            del _scan_tasks[task_id]
            return {"success": True}
        return {"success": False, "error": "Task not found"}

    @app.get("/scan/{task_id}/export")
    async def export_report(task_id: str, format: str = "json"):
        """导出扫描报告"""
        if task_id not in _scan_tasks:
            return {"success": False, "error": "Task not found"}

        task = _scan_tasks[task_id]

        if format == "json":
            report = json.dumps({
                "task_id": task_id,
                "target_url": task["target_url"],
                "scan_type": task["scan_type"],
                "vulns": task["vulns"],
                "summary": {
                    "total": len(task["vulns"]),
                    "by_severity": _count_by_severity(task["vulns"]),
                },
            }, ensure_ascii=False, indent=2)
        else:
            # HTML 格式
            report = _generate_html_report(task_id, task)

        return {"success": True, "report_content": report}

    return app


# ─────────────────────────────────────────────────────────────────────────────
# 扫描执行
# ─────────────────────────────────────────────────────────────────────────────

async def _run_scan(task_id: str, request: ScanRequest):
    """执行扫描任务"""
    task = _scan_tasks[task_id]
    task["status"] = "running"

    try:
        # 模拟扫描（实际项目中调用 Xray + Rad）
        # 这里提供简化的实现，实际部署时替换为真实扫描逻辑
        
        await asyncio.sleep(1)  # 模拟初始化
        task["progress"] = 10

        # 模拟扫描过程
        for i in range(10, 100, 10):
            await asyncio.sleep(0.5)
            task["progress"] = i

        # 模拟发现漏洞（实际项目中解析 Xray 输出）
        if "sql" in request.target_url.lower() or "sqli" in request.scan_type:
            task["vulns"].append({
                "id": f"{task_id}-1",
                "name": "SQL 注入",
                "severity": "critical",
                "url": request.target_url,
                "vuln_type": "SQL Injection",
                "detail": "检测到 SQL 注入漏洞，可能被用于窃取数据库信息",
                "payload": "' OR '1'='1",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            })

        if "xss" in request.target_url.lower() or request.scan_type == "xss":
            task["vulns"].append({
                "id": f"{task_id}-2",
                "name": "XSS 跨站脚本",
                "severity": "high",
                "url": request.target_url,
                "vuln_type": "Cross-Site Scripting",
                "detail": "检测到反射型 XSS 漏洞",
                "payload": "<script>alert(1)</script>",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            })

        task["status"] = "completed"
        task["progress"] = 100
        task["end_time"] = time.time()

    except Exception as e:
        task["status"] = "failed"
        task["progress"] = 0
        task["end_time"] = time.time()


def _count_by_severity(vulns: List[Dict]) -> Dict[str, int]:
    """统计各严重级别的漏洞数量"""
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for v in vulns:
        sev = v.get("severity", "info").lower()
        if sev in counts:
            counts[sev] += 1
    return counts


def _generate_html_report(task_id: str, task: Dict) -> str:
    """生成 HTML 报告"""
    vulns_html = ""
    for v in task["vulns"]:
        vulns_html += f"""
        <tr>
            <td>{v['name']}</td>
            <td class="severity-{v['severity']}">{v['severity'].upper()}</td>
            <td>{v['url']}</td>
            <td>{v['vuln_type']}</td>
            <td>{v['timestamp']}</td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>安全扫描报告 - {task_id}</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; padding: 40px; background: #1a1a2e; color: #eee; }}
            h1 {{ color: #ef4444; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #333; }}
            th {{ background: #16213e; }}
            .severity-critical {{ color: #ef4444; font-weight: bold; }}
            .severity-high {{ color: #f97316; font-weight: bold; }}
            .severity-medium {{ color: #eab308; }}
            .severity-low {{ color: #3b82f6; }}
            .severity-info {{ color: #6b7280; }}
        </style>
    </head>
    <body>
        <h1>🛡️ 安全扫描报告</h1>
        <p><strong>任务ID:</strong> {task_id}</p>
        <p><strong>目标URL:</strong> {task['target_url']}</p>
        <p><strong>扫描类型:</strong> {task['scan_type']}</p>
        <p><strong>发现漏洞:</strong> {len(task['vulns'])} 个</p>
        <table>
            <tr><th>漏洞名称</th><th>严重级别</th><th>URL</th><th>类型</th><th>发现时间</th></tr>
            {vulns_html}
        </table>
    </body>
    </html>
    """


# ─────────────────────────────────────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(create_app(), host="0.0.0.0", port=9244)
