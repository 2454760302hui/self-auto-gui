"""项目 / 工作空间 / 集合 路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from ..models.base import get_db, Workspace, Project, Collection, Api, ApiChangelog
from .auth import get_current_user
import json

router = APIRouter(prefix="/api", tags=["projects"], dependencies=[Depends(get_current_user)])


# ── Schemas ───────────────────────────────────────────────────
class WorkspaceCreate(BaseModel):
    name: str
    description: str = ""

class ProjectCreate(BaseModel):
    workspace_id: int
    name: str
    description: str = ""
    base_url: str = ""

class CollectionCreate(BaseModel):
    project_id: int
    parent_id: Optional[int] = None
    name: str
    description: str = ""
    sort_order: int = 0

class ApiCreate(BaseModel):
    collection_id: int
    name: str
    method: str = "GET"
    path: str
    description: str = ""
    headers: dict = {}
    params: dict = {}
    body_type: str = "none"
    body: str = ""
    pre_script: str = ""
    post_script: str = ""
    assertions: list = []
    extractions: list = []
    tags: str = ""

class ApiUpdate(BaseModel):
    name: Optional[str] = None
    method: Optional[str] = None
    path: Optional[str] = None
    description: Optional[str] = None
    headers: Optional[dict] = None
    params: Optional[dict] = None
    body_type: Optional[str] = None
    body: Optional[str] = None
    pre_script: Optional[str] = None
    post_script: Optional[str] = None
    assertions: Optional[list] = None
    extractions: Optional[list] = None
    tags: Optional[str] = None
    status: Optional[str] = None


# ── 工作空间 ──────────────────────────────────────────────────
@router.get("/workspaces")
def list_workspaces(db: Session = Depends(get_db)):
    return db.query(Workspace).all()

@router.post("/workspaces")
def create_workspace(data: WorkspaceCreate, db: Session = Depends(get_db)):
    ws = Workspace(**data.model_dump())
    db.add(ws); db.commit(); db.refresh(ws)
    return ws

@router.delete("/workspaces/{ws_id}")
def delete_workspace(ws_id: int, db: Session = Depends(get_db)):
    ws = db.query(Workspace).filter(Workspace.id == ws_id).first()
    if not ws:
        raise HTTPException(404, "Workspace not found")
    db.delete(ws); db.commit()
    return {"ok": True}


# ── 项目 ──────────────────────────────────────────────────────
@router.get("/projects")
def list_projects(workspace_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(Project)
    if workspace_id:
        q = q.filter(Project.workspace_id == workspace_id)
    return q.all()

@router.post("/projects")
def create_project(data: ProjectCreate, db: Session = Depends(get_db)):
    proj = Project(**data.model_dump())
    db.add(proj); db.commit(); db.refresh(proj)
    return proj

@router.get("/projects/{proj_id}")
def get_project(proj_id: int, db: Session = Depends(get_db)):
    proj = db.query(Project).filter(Project.id == proj_id).first()
    if not proj:
        raise HTTPException(404, "Project not found")
    return proj

@router.delete("/projects/{proj_id}")
def delete_project(proj_id: int, db: Session = Depends(get_db)):
    proj = db.query(Project).filter(Project.id == proj_id).first()
    if not proj:
        raise HTTPException(404)
    db.delete(proj); db.commit()
    return {"ok": True}


# ── 集合 ──────────────────────────────────────────────────────
@router.get("/collections")
def list_collections(project_id: int, db: Session = Depends(get_db)):
    return db.query(Collection).filter(Collection.project_id == project_id).all()

@router.post("/collections")
def create_collection(data: CollectionCreate, db: Session = Depends(get_db)):
    col = Collection(**data.model_dump())
    db.add(col); db.commit(); db.refresh(col)
    return col

@router.delete("/collections/{col_id}")
def delete_collection(col_id: int, db: Session = Depends(get_db)):
    col = db.query(Collection).filter(Collection.id == col_id).first()
    if not col:
        raise HTTPException(404)
    db.delete(col); db.commit()
    return {"ok": True}


# ── API 接口 ──────────────────────────────────────────────────
@router.get("/apis")
def list_apis(collection_id: int, db: Session = Depends(get_db)):
    apis = db.query(Api).filter(Api.collection_id == collection_id).all()
    result = []
    for api in apis:
        d = {c.name: getattr(api, c.name) for c in api.__table__.columns}
        for f in ('headers', 'params', 'assertions', 'extractions'):
            try:
                d[f] = json.loads(d[f] or '{}')
            except Exception:
                pass
        result.append(d)
    return result

@router.post("/apis")
def create_api(data: ApiCreate, db: Session = Depends(get_db)):
    d = data.model_dump()
    for f in ('headers', 'params', 'assertions', 'extractions'):
        d[f] = json.dumps(d[f], ensure_ascii=False)
    api = Api(**d)
    db.add(api); db.commit(); db.refresh(api)
    return api

@router.get("/apis/{api_id}")
def get_api(api_id: int, db: Session = Depends(get_db)):
    api = db.query(Api).filter(Api.id == api_id).first()
    if not api:
        raise HTTPException(404)
    d = {c.name: getattr(api, c.name) for c in api.__table__.columns}
    for f in ('headers', 'params', 'assertions', 'extractions'):
        try:
            d[f] = json.loads(d[f] or '{}')
        except Exception:
            pass
    return d

@router.put("/apis/{api_id}")
def update_api(api_id: int, data: ApiUpdate, db: Session = Depends(get_db)):
    api = db.query(Api).filter(Api.id == api_id).first()
    if not api:
        raise HTTPException(404)
    # 更新前保存快照到变更记录
    snapshot = {c.name: getattr(api, c.name) for c in api.__table__.columns}
    for f in ('headers', 'params', 'assertions', 'extractions'):
        try:
            snapshot[f] = json.loads(snapshot[f] or '{}')
        except Exception:
            pass
    changelog = ApiChangelog(
        api_id=api_id,
        action="update",
        snapshot=json.dumps(snapshot, ensure_ascii=False, default=str),
    )
    db.add(changelog)

    update_data = data.model_dump(exclude_none=True)
    for f in ('headers', 'params', 'assertions', 'extractions'):
        if f in update_data:
            update_data[f] = json.dumps(update_data[f], ensure_ascii=False)
    for k, v in update_data.items():
        setattr(api, k, v)
    db.commit(); db.refresh(api)
    return api

@router.delete("/apis/{api_id}")
def delete_api(api_id: int, db: Session = Depends(get_db)):
    api = db.query(Api).filter(Api.id == api_id).first()
    if not api:
        raise HTTPException(404)
    db.delete(api); db.commit()
    return {"ok": True}


# ── 树形结构（集合+接口） ─────────────────────────────────────
@router.get("/projects/{proj_id}/tree")
def get_project_tree(proj_id: int, db: Session = Depends(get_db)):
    """返回项目的完整树形结构"""
    collections = db.query(Collection).filter(
        Collection.project_id == proj_id).order_by(Collection.sort_order).all()
    apis = db.query(Api).join(Collection).filter(
        Collection.project_id == proj_id).all()

    api_map: dict = {}
    for api in apis:
        api_map.setdefault(api.collection_id, []).append({
            'id': api.id, 'name': api.name,
            'method': api.method, 'path': api.path,
            'status': api.status, 'type': 'api',
        })

    def build_tree(parent_id):
        nodes = []
        for col in collections:
            if col.parent_id == parent_id:
                nodes.append({
                    'id': col.id, 'name': col.name,
                    'type': 'collection',
                    'children': build_tree(col.id) + api_map.get(col.id, []),
                })
        return nodes

    return build_tree(None)


# ── 任务1：补全缺失端点 ────────────────────────────────────────

class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    base_url: Optional[str] = None

class CollectionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None
    parent_id: Optional[int] = None

class MoveApiBody(BaseModel):
    collection_id: int


@router.put("/workspaces/{ws_id}")
def update_workspace(ws_id: int, data: WorkspaceUpdate, db: Session = Depends(get_db)):
    ws = db.query(Workspace).filter(Workspace.id == ws_id).first()
    if not ws:
        raise HTTPException(404, "Workspace not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(ws, k, v)
    db.commit(); db.refresh(ws)
    return ws


@router.get("/workspaces/{ws_id}")
def get_workspace(ws_id: int, db: Session = Depends(get_db)):
    ws = db.query(Workspace).filter(Workspace.id == ws_id).first()
    if not ws:
        raise HTTPException(404, "Workspace not found")
    return ws


@router.put("/projects/{proj_id}")
def update_project(proj_id: int, data: ProjectUpdate, db: Session = Depends(get_db)):
    proj = db.query(Project).filter(Project.id == proj_id).first()
    if not proj:
        raise HTTPException(404, "Project not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(proj, k, v)
    db.commit(); db.refresh(proj)
    return proj


@router.put("/collections/{col_id}")
def update_collection(col_id: int, data: CollectionUpdate, db: Session = Depends(get_db)):
    col = db.query(Collection).filter(Collection.id == col_id).first()
    if not col:
        raise HTTPException(404, "Collection not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(col, k, v)
    db.commit(); db.refresh(col)
    return col


@router.post("/collections/{col_id}/duplicate")
def duplicate_collection(col_id: int, db: Session = Depends(get_db)):
    """复制集合及其下所有接口"""
    col = db.query(Collection).filter(Collection.id == col_id).first()
    if not col:
        raise HTTPException(404, "Collection not found")

    new_col = Collection(
        project_id=col.project_id,
        parent_id=col.parent_id,
        name=col.name + " (副本)",
        description=col.description,
        sort_order=col.sort_order + 1,
    )
    db.add(new_col); db.flush()

    apis = db.query(Api).filter(Api.collection_id == col_id).all()
    for api in apis:
        new_api = Api(
            collection_id=new_col.id,
            name=api.name,
            method=api.method,
            path=api.path,
            description=api.description,
            headers=api.headers,
            params=api.params,
            body_type=api.body_type,
            body=api.body,
            pre_script=api.pre_script,
            post_script=api.post_script,
            assertions=api.assertions,
            extractions=api.extractions,
            tags=api.tags,
            status=api.status,
        )
        db.add(new_api)

    db.commit(); db.refresh(new_col)
    return {"id": new_col.id, "name": new_col.name, "api_count": len(apis)}


@router.post("/apis/{api_id}/duplicate")
def duplicate_api(api_id: int, db: Session = Depends(get_db)):
    """复制接口"""
    api = db.query(Api).filter(Api.id == api_id).first()
    if not api:
        raise HTTPException(404, "API not found")

    new_api = Api(
        collection_id=api.collection_id,
        name=api.name + " (副本)",
        method=api.method,
        path=api.path,
        description=api.description,
        headers=api.headers,
        params=api.params,
        body_type=api.body_type,
        body=api.body,
        pre_script=api.pre_script,
        post_script=api.post_script,
        assertions=api.assertions,
        extractions=api.extractions,
        tags=api.tags,
        status=api.status,
    )
    db.add(new_api); db.commit(); db.refresh(new_api)
    return new_api


@router.post("/apis/{api_id}/move")
def move_api(api_id: int, body: MoveApiBody, db: Session = Depends(get_db)):
    """移动接口到其他集合"""
    api = db.query(Api).filter(Api.id == api_id).first()
    if not api:
        raise HTTPException(404, "API not found")
    col = db.query(Collection).filter(Collection.id == body.collection_id).first()
    if not col:
        raise HTTPException(404, "Collection not found")
    api.collection_id = body.collection_id
    db.commit(); db.refresh(api)
    return {"ok": True, "api_id": api_id, "collection_id": body.collection_id}
