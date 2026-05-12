"""备份与恢复模块"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import json

from ..models.base import (
    get_db, Project, Collection, Api, Environment,
    GlobalVariable, MockRule, TestSuite, Workspace,
)
from .auth import get_current_user

router = APIRouter(prefix="/api", tags=["backup"], dependencies=[Depends(get_current_user)])

MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB


def _safe_json_parse(val):
    if isinstance(val, (dict, list)):
        return val
    try:
        return json.loads(val or '{}')
    except Exception:
        return val

def _serialize_api(api: Api) -> dict:
    d = {c.name: getattr(api, c.name) for c in api.__table__.columns}
    for f in ('headers', 'params', 'assertions', 'extractions'):
        d[f] = _safe_json_parse(d.get(f))
    d['created_at'] = str(d.get('created_at', ''))
    d['updated_at'] = str(d.get('updated_at', ''))
    return d


def _serialize_env(env: Environment) -> dict:
    d = {c.name: getattr(env, c.name) for c in env.__table__.columns}
    d['variables'] = _safe_json_parse(d.get('variables'))
    d['created_at'] = str(d.get('created_at', ''))
    return d


def _serialize_mock(mock: MockRule) -> dict:
    d = {c.name: getattr(mock, c.name) for c in mock.__table__.columns}
    for f in ('response_headers', 'response_body'):
        d[f] = _safe_json_parse(d.get(f))
    d['created_at'] = str(d.get('created_at', ''))
    return d


def _serialize_suite(suite: TestSuite) -> dict:
    d = {c.name: getattr(suite, c.name) for c in suite.__table__.columns}
    d['steps'] = _safe_json_parse(d.get('steps'))
    d['created_at'] = str(d.get('created_at', ''))
    return d


@router.post("/backup/{project_id}")
def backup_project(project_id: int, db: Session = Depends(get_db)):
    """导出项目完整数据为 JSON 文件下载"""
    proj = db.query(Project).filter(Project.id == project_id).first()
    if not proj:
        raise HTTPException(404, "Project not found")

    collections = db.query(Collection).filter(Collection.project_id == project_id).all()
    col_ids = [c.id for c in collections]

    apis = db.query(Api).filter(Api.collection_id.in_(col_ids)).all() if col_ids else []
    environments = db.query(Environment).filter(Environment.project_id == project_id).all()
    global_vars = db.query(GlobalVariable).filter(GlobalVariable.project_id == project_id).all()
    mocks = db.query(MockRule).filter(MockRule.project_id == project_id).all()
    suites = db.query(TestSuite).filter(TestSuite.project_id == project_id).all()

    payload = {
        "version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "project": {
            "name": proj.name,
            "description": proj.description,
            "base_url": proj.base_url,
        },
        "collections": [
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "parent_id": c.parent_id,
                "sort_order": c.sort_order,
            }
            for c in collections
        ],
        "apis": [_serialize_api(a) for a in apis],
        "environments": [_serialize_env(e) for e in environments],
        "global_variables": [
            {"key": gv.key, "value": gv.value, "enabled": gv.enabled, "secret": gv.secret}
            for gv in global_vars
        ],
        "mocks": [_serialize_mock(m) for m in mocks],
        "test_suites": [_serialize_suite(s) for s in suites],
    }

    content = json.dumps(payload, ensure_ascii=False, indent=2)
    ascii_filename = f"backup_project_{project_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
    return Response(
        content=content.encode("utf-8"),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{ascii_filename}"'},
    )


@router.post("/restore")
async def restore_project(
    workspace_id: int,
    conflict_strategy: str = "skip",
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """上传备份 JSON 文件，恢复到指定 workspace_id"""
    if conflict_strategy not in ("skip", "overwrite"):
        raise HTTPException(400, "conflict_strategy 只能是 skip 或 overwrite")

    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(404, "Workspace not found")

    raw = await file.read()
    if len(raw) > MAX_UPLOAD_SIZE:
        raise HTTPException(400, f"文件过大，最大支持 {MAX_UPLOAD_SIZE // 1024 // 1024}MB")
    try:
        payload = json.loads(raw)
    except Exception:
        raise HTTPException(400, "无效的 JSON 文件")

    proj_data = payload.get("project", {})
    if not proj_data.get("name"):
        raise HTTPException(400, "备份文件缺少项目信息")

    # 创建或复用项目
    existing_proj = db.query(Project).filter(
        Project.workspace_id == workspace_id,
        Project.name == proj_data["name"],
    ).first()

    if existing_proj and conflict_strategy == "skip":
        return {"message": "项目已存在，已跳过", "collections": 0, "apis": 0, "environments": 0, "mocks": 0, "test_suites": 0}

    if existing_proj and conflict_strategy == "overwrite":
        proj = existing_proj
        proj.description = proj_data.get("description", "")
        proj.base_url = proj_data.get("base_url", "")
    else:
        proj = Project(
            workspace_id=workspace_id,
            name=proj_data["name"],
            description=proj_data.get("description", ""),
            base_url=proj_data.get("base_url", ""),
        )
        db.add(proj)
        db.flush()

    stats = {"collections": 0, "apis": 0, "environments": 0, "global_variables": 0, "mocks": 0, "test_suites": 0}

    # 集合（需要映射旧 id -> 新 id）
    col_id_map: dict = {}
    for col_data in payload.get("collections", []):
        old_id = col_data.get("id")
        existing_col = db.query(Collection).filter(
            Collection.project_id == proj.id,
            Collection.name == col_data["name"],
        ).first()
        if existing_col and conflict_strategy == "skip":
            col_id_map[old_id] = existing_col.id
            continue
        if existing_col and conflict_strategy == "overwrite":
            col = existing_col
        else:
            col = Collection(project_id=proj.id)
            db.add(col)
        col.name = col_data["name"]
        col.description = col_data.get("description", "")
        col.sort_order = col_data.get("sort_order", 0)
        db.flush()
        col_id_map[old_id] = col.id
        stats["collections"] += 1

    # 修正 parent_id
    for col_data in payload.get("collections", []):
        old_id = col_data.get("id")
        old_parent = col_data.get("parent_id")
        if old_parent and old_id in col_id_map and old_parent in col_id_map:
            col = db.query(Collection).filter(Collection.id == col_id_map[old_id]).first()
            if col:
                col.parent_id = col_id_map[old_parent]

    # 接口
    for api_data in payload.get("apis", []):
        old_col_id = api_data.get("collection_id")
        new_col_id = col_id_map.get(old_col_id)
        if not new_col_id:
            continue
        existing_api = db.query(Api).filter(
            Api.collection_id == new_col_id,
            Api.name == api_data["name"],
        ).first()
        if existing_api and conflict_strategy == "skip":
            continue
        if existing_api and conflict_strategy == "overwrite":
            api = existing_api
        else:
            api = Api(collection_id=new_col_id)
            db.add(api)
        api.name = api_data.get("name", "")
        api.method = api_data.get("method", "GET")
        api.path = api_data.get("path", "/")
        api.description = api_data.get("description", "")
        api.body_type = api_data.get("body_type", "none")
        api.body = api_data.get("body", "")
        api.pre_script = api_data.get("pre_script", "")
        api.post_script = api_data.get("post_script", "")
        api.tags = api_data.get("tags", "")
        api.status = api_data.get("status", "active")
        for f in ('headers', 'params', 'assertions', 'extractions'):
            val = api_data.get(f, {} if f in ('headers', 'params') else [])
            try:
                setattr(api, f, json.dumps(val, ensure_ascii=False))
            except Exception:
                setattr(api, f, '{}' if f in ('headers', 'params') else '[]')
        stats["apis"] += 1

    # 环境
    for env_data in payload.get("environments", []):
        existing_env = db.query(Environment).filter(
            Environment.project_id == proj.id,
            Environment.name == env_data["name"],
        ).first()
        if existing_env and conflict_strategy == "skip":
            continue
        if existing_env and conflict_strategy == "overwrite":
            env = existing_env
        else:
            env = Environment(project_id=proj.id)
            db.add(env)
        env.name = env_data["name"]
        try:
            env.variables = json.dumps(env_data.get("variables", {}), ensure_ascii=False)
        except Exception:
            env.variables = "{}"
        stats["environments"] += 1

    # 全局变量
    for gv_data in payload.get("global_variables", []):
        existing_gv = db.query(GlobalVariable).filter(
            GlobalVariable.project_id == proj.id,
            GlobalVariable.key == gv_data["key"],
        ).first()
        if existing_gv and conflict_strategy == "skip":
            continue
        if existing_gv and conflict_strategy == "overwrite":
            existing_gv.value = gv_data.get("value", "")
            existing_gv.enabled = gv_data.get("enabled", True)
        else:
            gv = GlobalVariable(
                project_id=proj.id,
                key=gv_data["key"],
                value=gv_data.get("value", ""),
                enabled=gv_data.get("enabled", True),
                secret=gv_data.get("secret", False),
            )
            db.add(gv)
        stats["global_variables"] += 1

    # Mock 规则
    for mock_data in payload.get("mocks", []):
        existing_mock = db.query(MockRule).filter(
            MockRule.project_id == proj.id,
            MockRule.name == mock_data["name"],
        ).first()
        if existing_mock and conflict_strategy == "skip":
            continue
        if existing_mock and conflict_strategy == "overwrite":
            mock = existing_mock
        else:
            mock = MockRule(project_id=proj.id)
            db.add(mock)
        mock.name = mock_data.get("name", "")
        mock.method = mock_data.get("method", "GET")
        mock.path = mock_data.get("path", "/")
        mock.response_status = mock_data.get("response_status", 200)
        mock.delay = mock_data.get("delay", 0)
        mock.enabled = mock_data.get("enabled", True)
        try:
            mock.response_headers = json.dumps(mock_data.get("response_headers", {}), ensure_ascii=False)
            mock.response_body = json.dumps(mock_data.get("response_body", {}), ensure_ascii=False)
        except Exception:
            mock.response_headers = "{}"
            mock.response_body = "{}"
        stats["mocks"] += 1

    # 测试套件
    for suite_data in payload.get("test_suites", []):
        existing_suite = db.query(TestSuite).filter(
            TestSuite.project_id == proj.id,
            TestSuite.name == suite_data["name"],
        ).first()
        if existing_suite and conflict_strategy == "skip":
            continue
        if existing_suite and conflict_strategy == "overwrite":
            suite = existing_suite
        else:
            suite = TestSuite(project_id=proj.id)
            db.add(suite)
        suite.name = suite_data.get("name", "")
        suite.description = suite_data.get("description", "")
        try:
            suite.steps = json.dumps(suite_data.get("steps", []), ensure_ascii=False)
        except Exception:
            suite.steps = "[]"
        stats["test_suites"] += 1

    db.commit()
    return {"ok": True, "project_id": proj.id, **stats}
