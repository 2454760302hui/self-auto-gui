"""Cookie Jar / 证书 / 定时任务 / API 文档 / 团队 / 搜索 / 变更记录"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from ..models.base import (
    get_db, Api, Collection, Project,
    CookieJar, Certificate, ScheduledTask, ApiDoc, TeamMember, ApiChangelog,
    TestSuite, TestRun, RequestHistory,
)
from .auth import get_current_user
import json
import secrets
from datetime import datetime, timedelta

router = APIRouter(prefix="/api", tags=["extras"], dependencies=[Depends(get_current_user)])


# ─────────────────────────────────────────────────────────────
# Cookie Jar
# ─────────────────────────────────────────────────────────────
class CookieJarCreate(BaseModel):
    project_id: int
    name: str
    domain: str = ""
    cookies: list = []

@router.get("/cookie-jars")
def list_cookie_jars(project_id: int, db: Session = Depends(get_db)):
    jars = db.query(CookieJar).filter(CookieJar.project_id == project_id).all()
    result = []
    for j in jars:
        d = {c.name: getattr(j, c.name) for c in j.__table__.columns}
        try:
            d['cookies'] = json.loads(d['cookies'] or '[]')
        except Exception:
            pass
        result.append(d)
    return result

@router.post("/cookie-jars")
def create_cookie_jar(data: CookieJarCreate, db: Session = Depends(get_db)):
    jar = CookieJar(
        project_id=data.project_id,
        name=data.name,
        domain=data.domain,
        cookies=json.dumps(data.cookies, ensure_ascii=False),
    )
    db.add(jar); db.commit(); db.refresh(jar)
    return jar

@router.put("/cookie-jars/{jar_id}")
def update_cookie_jar(jar_id: int, data: CookieJarCreate, db: Session = Depends(get_db)):
    jar = db.query(CookieJar).filter(CookieJar.id == jar_id).first()
    if not jar:
        raise HTTPException(404)
    jar.name    = data.name
    jar.domain  = data.domain
    jar.cookies = json.dumps(data.cookies, ensure_ascii=False)
    db.commit(); db.refresh(jar)
    return jar

@router.delete("/cookie-jars/{jar_id}")
def delete_cookie_jar(jar_id: int, db: Session = Depends(get_db)):
    jar = db.query(CookieJar).filter(CookieJar.id == jar_id).first()
    if not jar:
        raise HTTPException(404)
    db.delete(jar); db.commit()
    return {"ok": True}


# ─────────────────────────────────────────────────────────────
# SSL 证书
# ─────────────────────────────────────────────────────────────
class CertCreate(BaseModel):
    project_id: int
    name: str
    host: str
    cert_pem: str = ""
    key_pem: str = ""
    passphrase: str = ""
    enabled: bool = True

@router.get("/certificates")
def list_certificates(project_id: int, db: Session = Depends(get_db)):
    certs = db.query(Certificate).filter(Certificate.project_id == project_id).all()
    return [{c.name: getattr(cert, c.name) for c in cert.__table__.columns
             if c.name != 'key_pem'}  # 不返回私钥
            for cert in certs]

@router.post("/certificates")
def create_certificate(data: CertCreate, db: Session = Depends(get_db)):
    cert = Certificate(**data.model_dump())
    db.add(cert); db.commit(); db.refresh(cert)
    return {"id": cert.id, "name": cert.name, "host": cert.host, "enabled": cert.enabled}

@router.put("/certificates/{cert_id}")
def update_certificate(cert_id: int, data: CertCreate, db: Session = Depends(get_db)):
    cert = db.query(Certificate).filter(Certificate.id == cert_id).first()
    if not cert:
        raise HTTPException(404)
    for k, v in data.model_dump().items():
        setattr(cert, k, v)
    db.commit()
    return {"ok": True}

@router.delete("/certificates/{cert_id}")
def delete_certificate(cert_id: int, db: Session = Depends(get_db)):
    cert = db.query(Certificate).filter(Certificate.id == cert_id).first()
    if not cert:
        raise HTTPException(404)
    db.delete(cert); db.commit()
    return {"ok": True}


# ─────────────────────────────────────────────────────────────
# 定时任务
# ─────────────────────────────────────────────────────────────
class TaskCreate(BaseModel):
    project_id: int
    name: str
    suite_id: Optional[int] = None
    cron: str = "0 9 * * *"   # 默认每天9点
    enabled: bool = True
    environment_id: Optional[int] = None

@router.get("/scheduled-tasks")
def list_tasks(project_id: int, db: Session = Depends(get_db)):
    return db.query(ScheduledTask).filter(
        ScheduledTask.project_id == project_id).all()

@router.post("/scheduled-tasks")
def create_task(data: TaskCreate, db: Session = Depends(get_db)):
    task = ScheduledTask(**data.model_dump())
    db.add(task); db.commit(); db.refresh(task)
    return task

@router.put("/scheduled-tasks/{task_id}")
def update_task(task_id: int, data: TaskCreate, db: Session = Depends(get_db)):
    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    if not task:
        raise HTTPException(404)
    for k, v in data.model_dump().items():
        setattr(task, k, v)
    db.commit(); db.refresh(task)
    return task

@router.delete("/scheduled-tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    if not task:
        raise HTTPException(404)
    db.delete(task); db.commit()
    return {"ok": True}

@router.post("/scheduled-tasks/{task_id}/trigger")
async def trigger_task(task_id: int, db: Session = Depends(get_db)):
    """手动触发定时任务"""
    from ..routers.runner import _merge_variables
    from ..core.engine import execute_suite

    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    if not task:
        raise HTTPException(404)
    if not task.suite_id:
        raise HTTPException(400, "任务未绑定测试套件")

    suite = db.query(TestSuite).filter(TestSuite.id == task.suite_id).first()
    if not suite:
        raise HTTPException(404, "测试套件不存在")

    variables = _merge_variables(task.project_id, task.environment_id, db)
    steps = json.loads(suite.steps or '[]')

    result = await execute_suite(steps, variables)

    run = TestRun(
        project_id=task.project_id,
        suite_name=f"[定时] {suite.name}",
        status=result['status'],
        total=result['total'],
        passed=result['passed'],
        failed=result['failed'],
        duration=result['duration'],
        results=json.dumps(result['results'], ensure_ascii=False, default=str),
    )
    db.add(run)
    task.last_run_at = datetime.now()
    db.commit()
    return result


# ─────────────────────────────────────────────────────────────
# API 文档（在线分享）
# ─────────────────────────────────────────────────────────────
class DocCreate(BaseModel):
    project_id: int
    version: str = "1.0.0"
    title: str = ""
    is_public: bool = False

@router.get("/docs")
def list_docs(project_id: int, db: Session = Depends(get_db)):
    return db.query(ApiDoc).filter(ApiDoc.project_id == project_id).all()

@router.post("/docs/generate/{project_id}")
def generate_doc(project_id: int, data: DocCreate, db: Session = Depends(get_db)):
    """从项目接口自动生成 API 文档（OpenAPI 格式）"""
    proj = db.query(Project).filter(Project.id == project_id).first()
    if not proj:
        raise HTTPException(404)
    collections = db.query(Collection).filter(Collection.project_id == project_id).all()
    apis = db.query(Api).join(Collection).filter(Collection.project_id == project_id).all()

    col_name_map = {c.id: c.name for c in collections}
    paths: dict = {}
    tags_set: set = set()

    for api in apis:
        tag = col_name_map.get(api.collection_id, "默认")
        tags_set.add(tag)
        try:
            params_dict = json.loads(api.params or "{}")
        except Exception:
            params_dict = {}
        parameters = [{"name": k, "in": "query", "schema": {"type": "string"}, "example": v}
                      for k, v in params_dict.items()]
        operation: dict = {
            "summary": api.name,
            "description": api.description,
            "tags": [tag],
            "parameters": parameters,
            "responses": {"200": {"description": "成功"}},
        }
        if api.body_type == "json" and api.body:
            try:
                example = json.loads(api.body)
            except Exception:
                example = api.body
            operation["requestBody"] = {
                "content": {"application/json": {"example": example}}
            }
        path_key = api.path if api.path.startswith("/") else "/" + api.path
        paths.setdefault(path_key, {})[api.method.lower()] = operation

    spec = {
        "openapi": "3.0.0",
        "info": {"title": data.title or proj.name, "version": data.version},
        "servers": [{"url": proj.base_url or "/"}],
        "tags": [{"name": t} for t in sorted(tags_set)],
        "paths": paths,
    }

    share_token = secrets.token_urlsafe(32) if data.is_public else ""
    doc = ApiDoc(
        project_id=project_id,
        version=data.version,
        title=data.title or proj.name,
        content=json.dumps(spec, ensure_ascii=False),
        is_public=data.is_public,
        share_token=share_token,
    )
    db.add(doc); db.commit(); db.refresh(doc)
    return {"id": doc.id, "share_token": share_token,
            "share_url": f"/api/docs/share/{share_token}" if share_token else None}

@router.get("/docs/share/{token}")
def get_shared_doc(token: str, db: Session = Depends(get_db)):
    """通过分享 token 访问公开文档"""
    doc = db.query(ApiDoc).filter(
        ApiDoc.share_token == token,
        ApiDoc.is_public == True,
    ).first()
    if not doc:
        raise HTTPException(404, "文档不存在或未公开")
    try:
        return json.loads(doc.content)
    except Exception:
        return {}


# ─────────────────────────────────────────────────────────────
# 团队成员
# ─────────────────────────────────────────────────────────────
class MemberCreate(BaseModel):
    workspace_id: int
    username: str
    email: str = ""
    role: str = "viewer"

@router.get("/team-members")
def list_members(workspace_id: int, db: Session = Depends(get_db)):
    return db.query(TeamMember).filter(
        TeamMember.workspace_id == workspace_id).all()

@router.post("/team-members")
def add_member(data: MemberCreate, db: Session = Depends(get_db)):
    member = TeamMember(**data.model_dump())
    db.add(member); db.commit(); db.refresh(member)
    return member

@router.put("/team-members/{member_id}/role")
def update_member_role(member_id: int, role: str, db: Session = Depends(get_db)):
    member = db.query(TeamMember).filter(TeamMember.id == member_id).first()
    if not member:
        raise HTTPException(404)
    if role not in ("owner", "editor", "viewer"):
        raise HTTPException(400, "角色只能是 owner/editor/viewer")
    member.role = role
    db.commit()
    return {"ok": True}

@router.delete("/team-members/{member_id}")
def remove_member(member_id: int, db: Session = Depends(get_db)):
    member = db.query(TeamMember).filter(TeamMember.id == member_id).first()
    if not member:
        raise HTTPException(404)
    db.delete(member); db.commit()
    return {"ok": True}


# ─────────────────────────────────────────────────────────────
# 全局搜索
# ─────────────────────────────────────────────────────────────
@router.get("/search")
def search(project_id: int, q: str, db: Session = Depends(get_db)):
    """全局搜索接口名称、路径、描述"""
    if not q or len(q) < 1:
        return []
    keyword = f"%{q}%"
    apis = db.query(Api).join(Collection).filter(
        Collection.project_id == project_id,
    ).filter(
        Api.name.like(keyword) |
        Api.path.like(keyword) |
        Api.description.like(keyword)
    ).limit(20).all()

    return [{"id": a.id, "name": a.name, "method": a.method,
             "path": a.path, "collection_id": a.collection_id}
            for a in apis]


# ─────────────────────────────────────────────────────────────
# 接口变更记录
# ─────────────────────────────────────────────────────────────
@router.get("/apis/{api_id}/changelog")
def get_api_changelog(api_id: int, db: Session = Depends(get_db)):
    logs = db.query(ApiChangelog).filter(
        ApiChangelog.api_id == api_id
    ).order_by(ApiChangelog.created_at.desc()).limit(50).all()
    result = []
    for log in logs:
        d = {c.name: getattr(log, c.name) for c in log.__table__.columns}
        try:
            d['snapshot'] = json.loads(d['snapshot'] or '{}')
        except Exception:
            pass
        result.append(d)
    return result


# ─────────────────────────────────────────────────────────────
# 接口统计
# ─────────────────────────────────────────────────────────────
@router.get("/projects/{project_id}/stats")
def project_stats(project_id: int, db: Session = Depends(get_db)):
    """项目统计：接口数、集合数、测试通过率等"""
    total_apis = db.query(Api).join(Collection).filter(
        Collection.project_id == project_id).count()
    total_cols = db.query(Collection).filter(
        Collection.project_id == project_id).count()
    runs = db.query(TestRun).filter(
        TestRun.project_id == project_id).order_by(
        TestRun.created_at.desc()).limit(10).all()

    pass_rate = 0.0
    if runs:
        total_cases = sum(r.total for r in runs)
        passed_cases = sum(r.passed for r in runs)
        pass_rate = round(passed_cases / total_cases * 100, 1) if total_cases else 0.0

    # 最近7天请求量
    week_ago = datetime.now() - timedelta(days=7)
    recent_requests = db.query(RequestHistory).join(
        Api, RequestHistory.api_id == Api.id
    ).join(Collection).filter(
        Collection.project_id == project_id,
        RequestHistory.created_at >= week_ago,
    ).count()

    return {
        "total_apis":       total_apis,
        "total_collections": total_cols,
        "total_runs":       len(runs),
        "pass_rate":        pass_rate,
        "recent_requests":  recent_requests,
    }


# ── 任务4：补全缺失端点 ────────────────────────────────────────


@router.get("/scheduled-tasks/{task_id}/history")
def get_task_history(task_id: int, limit: int = 20, db: Session = Depends(get_db)):
    """任务执行历史"""
    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "Task not found")
    # 按任务名称精确匹配定时运行记录
    suite_name_pattern = f"[定时] %"
    runs = db.query(TestRun).filter(
        TestRun.project_id == task.project_id,
        TestRun.suite_name.like(suite_name_pattern),
    ).order_by(TestRun.created_at.desc()).limit(limit).all()
    result = []
    for r in runs:
        d = {c.name: getattr(r, c.name) for c in r.__table__.columns}
        d.pop('results', None)  # 历史列表不返回详细结果，减少数据量
        result.append(d)
    return result


@router.post("/scheduled-tasks/{task_id}/toggle")
def toggle_task(task_id: int, db: Session = Depends(get_db)):
    """切换定时任务启用/禁用状态"""
    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "Task not found")
    task.enabled = not task.enabled
    db.commit()
    return {"ok": True, "enabled": task.enabled}

