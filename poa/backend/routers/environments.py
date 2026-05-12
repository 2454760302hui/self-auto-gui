"""环境变量 / 全局变量 / Mock 路由"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Any, List
from ..models.base import get_db, Environment, GlobalVariable, MockRule
from .auth import get_current_user
import asyncio
import json
import re
from datetime import datetime

router = APIRouter(prefix="/api", tags=["environments"], dependencies=[Depends(get_current_user)])


# ── Schemas ───────────────────────────────────────────────────
class EnvCreate(BaseModel):
    project_id: int
    name: str
    variables: dict = {}

class EnvUpdate(BaseModel):
    name: Optional[str] = None
    variables: Optional[dict] = None
    is_active: Optional[bool] = None

class GlobalVarCreate(BaseModel):
    project_id: int
    key: str
    value: str = ""
    enabled: bool = True
    secret: bool = False

class BatchGlobalVar(BaseModel):
    key: str
    value: str = ""
    enabled: bool = True

class MockCreate(BaseModel):
    project_id: int
    name: str
    method: str = "GET"
    path: str
    response_status: int = 200
    response_headers: dict = {}
    response_body: Any = {}
    delay: int = 0
    enabled: bool = True


# ── 环境 ──────────────────────────────────────────────────────
@router.get("/environments")
def list_environments(project_id: int, db: Session = Depends(get_db)):
    envs = db.query(Environment).filter(Environment.project_id == project_id).all()
    result = []
    for e in envs:
        d = {c.name: getattr(e, c.name) for c in e.__table__.columns}
        try:
            d['variables'] = json.loads(d['variables'] or '{}')
        except Exception:
            pass
        result.append(d)
    return result

@router.post("/environments")
def create_environment(data: EnvCreate, db: Session = Depends(get_db)):
    env = Environment(
        project_id=data.project_id,
        name=data.name,
        variables=json.dumps(data.variables, ensure_ascii=False),
    )
    db.add(env); db.commit(); db.refresh(env)
    return env

@router.post("/environments/import")
async def import_environment(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """导入环境变量（上传 JSON 文件）——必须在 /environments/{env_id}/xxx 之前注册"""
    raw = await file.read()
    try:
        payload = json.loads(raw)
    except Exception:
        raise HTTPException(400, "无效的 JSON 文件")
    name = payload.get("name", file.filename or "导入环境")
    variables = payload.get("variables", {})
    if not isinstance(variables, dict):
        raise HTTPException(400, "variables 必须是对象")
    env = Environment(
        project_id=project_id,
        name=name,
        variables=json.dumps(variables, ensure_ascii=False),
        is_active=False,
    )
    db.add(env); db.commit(); db.refresh(env)
    return {"id": env.id, "name": env.name, "variable_count": len(variables)}

@router.put("/environments/{env_id}")
def update_environment(env_id: int, data: EnvUpdate, db: Session = Depends(get_db)):
    env = db.query(Environment).filter(Environment.id == env_id).first()
    if not env:
        raise HTTPException(404)
    if data.name is not None:
        env.name = data.name
    if data.variables is not None:
        env.variables = json.dumps(data.variables, ensure_ascii=False)
    if data.is_active is not None:
        # 同一项目只能有一个激活环境
        if data.is_active:
            db.query(Environment).filter(
                Environment.project_id == env.project_id
            ).update({'is_active': False})
        env.is_active = data.is_active
    db.commit(); db.refresh(env)
    return env

@router.delete("/environments/{env_id}")
def delete_environment(env_id: int, db: Session = Depends(get_db)):
    env = db.query(Environment).filter(Environment.id == env_id).first()
    if not env:
        raise HTTPException(404)
    db.delete(env); db.commit()
    return {"ok": True}

@router.post("/environments/{env_id}/activate")
def activate_environment(env_id: int, db: Session = Depends(get_db)):
    env = db.query(Environment).filter(Environment.id == env_id).first()
    if not env:
        raise HTTPException(404)
    db.query(Environment).filter(
        Environment.project_id == env.project_id
    ).update({'is_active': False})
    env.is_active = True
    db.commit()
    return {"ok": True}


# ── 全局变量 ──────────────────────────────────────────────────
@router.get("/global-variables")
def list_global_vars(project_id: int, db: Session = Depends(get_db)):
    return db.query(GlobalVariable).filter(
        GlobalVariable.project_id == project_id).all()

@router.post("/global-variables")
def create_global_var(data: GlobalVarCreate, db: Session = Depends(get_db)):
    gv = GlobalVariable(**data.model_dump())
    db.add(gv); db.commit(); db.refresh(gv)
    return gv

@router.post("/global-variables/batch")
def batch_upsert_global_vars(
    project_id: int,
    items: List[BatchGlobalVar],
    db: Session = Depends(get_db),
):
    """批量创建/更新全局变量——必须在 /global-variables/{gv_id} 之前注册"""
    created = 0
    updated = 0
    for item in items:
        existing = db.query(GlobalVariable).filter(
            GlobalVariable.project_id == project_id,
            GlobalVariable.key == item.key,
        ).first()
        if existing:
            existing.value = item.value
            existing.enabled = item.enabled
            updated += 1
        else:
            gv = GlobalVariable(
                project_id=project_id,
                key=item.key,
                value=item.value,
                enabled=item.enabled,
            )
            db.add(gv)
            created += 1
    db.commit()
    return {"ok": True, "created": created, "updated": updated}

@router.put("/global-variables/{gv_id}")
def update_global_var(gv_id: int, data: GlobalVarCreate, db: Session = Depends(get_db)):
    gv = db.query(GlobalVariable).filter(GlobalVariable.id == gv_id).first()
    if not gv:
        raise HTTPException(404)
    for k, v in data.model_dump().items():
        setattr(gv, k, v)
    db.commit(); db.refresh(gv)
    return gv

@router.delete("/global-variables/{gv_id}")
def delete_global_var(gv_id: int, db: Session = Depends(get_db)):
    gv = db.query(GlobalVariable).filter(GlobalVariable.id == gv_id).first()
    if not gv:
        raise HTTPException(404)
    db.delete(gv); db.commit()
    return {"ok": True}


# ── Mock 服务 ─────────────────────────────────────────────────
@router.get("/mocks")
def list_mocks(project_id: int, db: Session = Depends(get_db)):
    mocks = db.query(MockRule).filter(MockRule.project_id == project_id).all()
    result = []
    for m in mocks:
        d = {c.name: getattr(m, c.name) for c in m.__table__.columns}
        for f in ('response_headers', 'response_body'):
            try:
                d[f] = json.loads(d[f] or '{}')
            except Exception:
                pass
        result.append(d)
    return result

@router.post("/mocks")
def create_mock(data: MockCreate, db: Session = Depends(get_db)):
    mock = MockRule(
        project_id=data.project_id,
        name=data.name,
        method=data.method,
        path=data.path,
        response_status=data.response_status,
        response_headers=json.dumps(data.response_headers, ensure_ascii=False),
        response_body=json.dumps(data.response_body, ensure_ascii=False),
        delay=data.delay,
        enabled=data.enabled,
    )
    db.add(mock); db.commit(); db.refresh(mock)
    return mock

@router.put("/mocks/{mock_id}")
def update_mock(mock_id: int, data: MockCreate, db: Session = Depends(get_db)):
    mock = db.query(MockRule).filter(MockRule.id == mock_id).first()
    if not mock:
        raise HTTPException(404)
    d = data.model_dump()
    d['response_headers'] = json.dumps(d['response_headers'], ensure_ascii=False)
    d['response_body']    = json.dumps(d['response_body'],    ensure_ascii=False)
    for k, v in d.items():
        setattr(mock, k, v)
    db.commit(); db.refresh(mock)
    return mock

@router.delete("/mocks/{mock_id}")
def delete_mock(mock_id: int, db: Session = Depends(get_db)):
    mock = db.query(MockRule).filter(MockRule.id == mock_id).first()
    if not mock:
        raise HTTPException(404)
    db.delete(mock); db.commit()
    return {"ok": True}


# ── Mock 请求处理已移至 mock_router（无认证） ───────────────────


# ── 无认证路由（Mock 请求处理，供被测系统调用）──────────────────
mock_router = APIRouter(prefix="/api", tags=["mock"])

@mock_router.api_route("/mock/{project_id}/{path:path}",
                  methods=["GET","POST","PUT","DELETE","PATCH","OPTIONS","HEAD"])
async def handle_mock_public(project_id: int, path: str,
                      request: Request, db: Session = Depends(get_db)):
    """处理 Mock 请求（无需认证）：/api/mock/{project_id}/your/path"""
    method = request.method.upper()
    full_path = '/' + path

    mocks = db.query(MockRule).filter(
        MockRule.project_id == project_id,
        MockRule.enabled == True,
    ).all()

    matched = None
    for mock in mocks:
        if mock.method.upper() != method and mock.method.upper() != 'ANY':
            continue
        pattern = re.sub(r':(\w+)', r'(?P<\1>[^/]+)', mock.path)
        pattern = pattern.replace('*', '.*')
        if re.fullmatch(pattern, full_path):
            matched = mock
            break

    if not matched:
        return Response(
            content=json.dumps({"error": "No mock rule matched"}),
            status_code=404,
            media_type="application/json",
        )

    if matched.delay > 0:
        await asyncio.sleep(matched.delay / 1000)

    resp_headers = json.loads(matched.response_headers or '{}')
    resp_body    = matched.response_body or '{}'

    return Response(
        content=resp_body,
        status_code=matched.response_status,
        headers=resp_headers,
        media_type=resp_headers.get('Content-Type', 'application/json'),
    )


# ── 任务3：补全缺失端点 ────────────────────────────────────────


@router.post("/environments/{env_id}/duplicate")
def duplicate_environment(env_id: int, db: Session = Depends(get_db)):
    """复制环境"""
    env = db.query(Environment).filter(Environment.id == env_id).first()
    if not env:
        raise HTTPException(404, "Environment not found")
    new_env = Environment(
        project_id=env.project_id,
        name=env.name + " (副本)",
        variables=env.variables,
        is_active=False,
    )
    db.add(new_env); db.commit(); db.refresh(new_env)
    return new_env


@router.get("/environments/{env_id}/export")
def export_environment(env_id: int, db: Session = Depends(get_db)):
    """导出环境变量为 JSON 文件下载"""
    env = db.query(Environment).filter(Environment.id == env_id).first()
    if not env:
        raise HTTPException(404, "Environment not found")
    try:
        variables = json.loads(env.variables or '{}')
    except Exception:
        variables = {}
    payload = {
        "name": env.name,
        "variables": variables,
        "exported_at": datetime.now().isoformat(),
    }
    content = json.dumps(payload, ensure_ascii=False, indent=2)
    filename = f"env_{env.name}.json"
    return Response(
        content=content.encode("utf-8"),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
