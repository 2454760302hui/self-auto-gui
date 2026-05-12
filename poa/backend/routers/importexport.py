"""Postman / Apifox / OpenAPI 导入导出"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from ..models.base import get_db, Project, Collection, Api
from .auth import get_current_user
import json

router = APIRouter(prefix="/api", tags=["import-export"], dependencies=[Depends(get_current_user)])

MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB


async def _read_upload(file: UploadFile) -> bytes:
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(400, f"文件过大，最大支持 {MAX_UPLOAD_SIZE // 1024 // 1024}MB")
    return content


# ─────────────────────────────────────────────────────────────
# 导入
# ─────────────────────────────────────────────────────────────

@router.post("/import/postman")
async def import_postman(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """导入 Postman Collection v2.1"""
    content = await _read_upload(file)
    try:
        data = json.loads(content)
    except Exception:
        raise HTTPException(400, "无效的 JSON 文件")

    info = data.get("info", {})
    schema = info.get("schema", "")
    if "v2" not in schema and "collection" not in str(data.keys()):
        raise HTTPException(400, "仅支持 Postman Collection v2.x 格式")

    proj = db.query(Project).filter(Project.id == project_id).first()
    if not proj:
        raise HTTPException(404, "项目不存在")

    stats = {"collections": 0, "apis": 0}

    def _parse_item(item: dict, parent_col_id: Optional[int]):
        """递归解析 Postman item"""
        name = item.get("name", "未命名")

        # 文件夹
        if "item" in item:
            col = Collection(
                project_id=project_id,
                parent_id=parent_col_id,
                name=name,
                description=item.get("description", ""),
            )
            db.add(col)
            db.flush()
            stats["collections"] += 1
            for sub in item["item"]:
                _parse_item(sub, col.id)
            return

        # 接口
        req = item.get("request", {})
        if not req:
            return

        method = req.get("method", "GET").upper()

        # URL
        url_obj = req.get("url", {})
        if isinstance(url_obj, str):
            path = url_obj
        else:
            raw = url_obj.get("raw", "")
            # 去掉 base_url 部分，保留路径
            path = raw

        # Headers
        headers = {}
        for h in req.get("header", []):
            if not h.get("disabled", False):
                headers[h.get("key", "")] = h.get("value", "")

        # Query params
        params = {}
        if isinstance(url_obj, dict):
            for p in url_obj.get("query", []):
                if not p.get("disabled", False):
                    params[p.get("key", "")] = p.get("value", "")

        # Body
        body_type = "none"
        body = ""
        body_obj = req.get("body", {})
        if body_obj:
            mode = body_obj.get("mode", "none")
            if mode == "raw":
                body_type = "json" if "json" in str(body_obj.get("options", {})).lower() else "raw"
                body = body_obj.get("raw", "")
            elif mode == "urlencoded":
                body_type = "form"
                form_data = {f["key"]: f["value"] for f in body_obj.get("urlencoded", [])
                             if not f.get("disabled", False)}
                body = json.dumps(form_data)
            elif mode == "formdata":
                body_type = "form"
                form_data = {f["key"]: f["value"] for f in body_obj.get("formdata", [])
                             if not f.get("disabled", False)}
                body = json.dumps(form_data)
            elif mode == "graphql":
                body_type = "graphql"
                body = json.dumps(body_obj.get("graphql", {}))

        # 描述
        desc = ""
        if isinstance(req.get("description"), str):
            desc = req["description"]
        elif isinstance(item.get("description"), str):
            desc = item["description"]

        # 确保有集合
        col_id = parent_col_id
        if col_id is None:
            default_col = Collection(
                project_id=project_id,
                name="默认集合",
            )
            db.add(default_col)
            db.flush()
            col_id = default_col.id
            stats["collections"] += 1

        api = Api(
            collection_id=col_id,
            name=name,
            method=method,
            path=path,
            description=desc,
            headers=json.dumps(headers, ensure_ascii=False),
            params=json.dumps(params, ensure_ascii=False),
            body_type=body_type,
            body=body,
        )
        db.add(api)
        stats["apis"] += 1

    for item in data.get("item", []):
        _parse_item(item, None)

    db.commit()
    return {"ok": True, "imported": stats}


@router.post("/import/apifox")
async def import_apifox(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """导入 Apifox 导出的 JSON（OpenAPI 3.0 格式）"""
    content = await _read_upload(file)
    try:
        data = json.loads(content)
    except Exception:
        raise HTTPException(400, "无效的 JSON 文件")

    # Apifox 导出格式兼容 OpenAPI 3.0
    if "openapi" in data or "swagger" in data:
        return await _import_openapi(project_id, data, db)

    # Apifox 原生格式
    if "apiCollection" in data or "apifoxProject" in data:
        return await _import_apifox_native(project_id, data, db)

    raise HTTPException(400, "不支持的 Apifox 导出格式")


@router.post("/import/openapi")
async def import_openapi(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """导入 OpenAPI 2.0 (Swagger) / 3.0 规范"""
    content = await _read_upload(file)
    try:
        data = json.loads(content)
    except Exception:
        # 尝试 YAML
        try:
            import yaml
            data = yaml.safe_load(content)
        except Exception:
            raise HTTPException(400, "无效的 JSON/YAML 文件")

    return await _import_openapi(project_id, data, db)


async def _import_openapi(project_id: int, spec: dict, db: Session) -> dict:
    """解析 OpenAPI 2.0/3.0 规范"""
    proj = db.query(Project).filter(Project.id == project_id).first()
    if not proj:
        raise HTTPException(404, "项目不存在")

    stats = {"collections": 0, "apis": 0}
    version = spec.get("openapi", spec.get("swagger", "2.0"))
    is_v3 = str(version).startswith("3")

    # 更新项目 base_url
    if is_v3:
        servers = spec.get("servers", [])
        if servers:
            proj.base_url = servers[0].get("url", "")
    else:
        host = spec.get("host", "")
        base_path = spec.get("basePath", "/")
        schemes = spec.get("schemes", ["https"])
        if host:
            proj.base_url = f"{schemes[0]}://{host}{base_path}"

    # 按 tag 创建集合
    tag_col_map: dict = {}
    for tag in spec.get("tags", []):
        col = Collection(
            project_id=project_id,
            name=tag.get("name", "默认"),
            description=tag.get("description", ""),
        )
        db.add(col)
        db.flush()
        tag_col_map[tag["name"]] = col.id
        stats["collections"] += 1

    paths = spec.get("paths", {})
    for path, path_item in paths.items():
        for method, operation in path_item.items():
            if method.upper() not in ("GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"):
                continue
            if not isinstance(operation, dict):
                continue

            tags = operation.get("tags", ["默认"])
            tag = tags[0] if tags else "默认"

            # 确保集合存在
            if tag not in tag_col_map:
                col = Collection(project_id=project_id, name=tag)
                db.add(col)
                db.flush()
                tag_col_map[tag] = col.id
                stats["collections"] += 1

            # 解析参数
            headers = {}
            params = {}
            body_type = "none"
            body = ""

            for param in operation.get("parameters", []):
                if param.get("in") == "header":
                    headers[param["name"]] = param.get("example", "")
                elif param.get("in") == "query":
                    params[param["name"]] = param.get("example", "")

            # 请求体
            if is_v3:
                req_body = operation.get("requestBody", {})
                content = req_body.get("content", {})
                if "application/json" in content:
                    body_type = "json"
                    schema = content["application/json"].get("schema", {})
                    body = json.dumps(_schema_to_example(schema, spec), ensure_ascii=False, indent=2)
                elif "application/x-www-form-urlencoded" in content:
                    body_type = "form"
                    schema = content["application/x-www-form-urlencoded"].get("schema", {})
                    body = json.dumps(_schema_to_example(schema, spec), ensure_ascii=False)
            else:
                for param in operation.get("parameters", []):
                    if param.get("in") == "body":
                        body_type = "json"
                        schema = param.get("schema", {})
                        body = json.dumps(_schema_to_example(schema, spec), ensure_ascii=False, indent=2)

            api = Api(
                collection_id=tag_col_map[tag],
                name=operation.get("summary", f"{method.upper()} {path}"),
                method=method.upper(),
                path=path,
                description=operation.get("description", ""),
                headers=json.dumps(headers, ensure_ascii=False),
                params=json.dumps(params, ensure_ascii=False),
                body_type=body_type,
                body=body,
            )
            db.add(api)
            stats["apis"] += 1

    db.commit()
    return {"ok": True, "imported": stats}


async def _import_apifox_native(project_id: int, data: dict, db: Session) -> dict:
    """解析 Apifox 原生导出格式"""
    stats = {"collections": 0, "apis": 0}

    def _parse_folder(folder: dict, parent_id: Optional[int]):
        name = folder.get("name", "未命名")
        col = Collection(
            project_id=project_id,
            parent_id=parent_id,
            name=name,
        )
        db.add(col)
        db.flush()
        stats["collections"] += 1

        for item in folder.get("items", []):
            if item.get("type") == "apiDetailFolder":
                _parse_folder(item, col.id)
            elif item.get("type") == "apiDetail":
                _parse_api(item, col.id)

    def _parse_api(item: dict, col_id: int):
        req = item.get("api", item)
        method = req.get("method", "GET").upper()
        path = req.get("path", "/")
        name = req.get("name", f"{method} {path}")

        headers = {h["name"]: h.get("example", "") for h in req.get("parameters", {}).get("header", [])}
        params = {p["name"]: p.get("example", "") for p in req.get("parameters", {}).get("query", [])}

        body_type = "none"
        body = ""
        body_obj = req.get("requestBody", {})
        if body_obj:
            ct = body_obj.get("type", "")
            if "json" in ct:
                body_type = "json"
                body = json.dumps(body_obj.get("jsonSchema", {}), ensure_ascii=False, indent=2)
            elif "form" in ct:
                body_type = "form"

        api = Api(
            collection_id=col_id,
            name=name,
            method=method,
            path=path,
            headers=json.dumps(headers, ensure_ascii=False),
            params=json.dumps(params, ensure_ascii=False),
            body_type=body_type,
            body=body,
        )
        db.add(api)
        stats["apis"] += 1

    for folder in data.get("apiCollection", data.get("items", [])):
        _parse_folder(folder, None)

    db.commit()
    return {"ok": True, "imported": stats}


def _schema_to_example(schema: dict, spec: dict) -> dict:
    """从 JSON Schema 生成示例数据"""
    if not schema:
        return {}
    # 解析 $ref
    if "$ref" in schema:
        ref = schema["$ref"]
        parts = ref.lstrip("#/").split("/")
        obj = spec
        for p in parts:
            obj = obj.get(p, {})
        return _schema_to_example(obj, spec)

    s_type = schema.get("type", "object")
    if s_type == "object":
        result = {}
        for k, v in schema.get("properties", {}).items():
            result[k] = _schema_to_example(v, spec)
        return result
    elif s_type == "array":
        items = schema.get("items", {})
        return [_schema_to_example(items, spec)]
    elif s_type == "string":
        return schema.get("example", schema.get("default", "string"))
    elif s_type == "integer":
        return schema.get("example", schema.get("default", 0))
    elif s_type == "number":
        return schema.get("example", schema.get("default", 0.0))
    elif s_type == "boolean":
        return schema.get("example", schema.get("default", True))
    return schema.get("example", schema.get("default", None))


# ─────────────────────────────────────────────────────────────
# 导出
# ─────────────────────────────────────────────────────────────

@router.get("/export/postman/{project_id}")
def export_postman(project_id: int, db: Session = Depends(get_db)):
    """导出为 Postman Collection v2.1"""
    proj = db.query(Project).filter(Project.id == project_id).first()
    if not proj:
        raise HTTPException(404)

    collections = db.query(Collection).filter(
        Collection.project_id == project_id).all()
    apis = db.query(Api).join(Collection).filter(
        Collection.project_id == project_id).all()

    api_map: dict = {}
    for api in apis:
        api_map.setdefault(api.collection_id, []).append(api)

    def _build_item(col: Collection) -> dict:
        items = []
        # 子集合
        for sub in collections:
            if sub.parent_id == col.id:
                items.append(_build_item(sub))
        # 接口
        for api in api_map.get(col.id, []):
            try:
                headers = json.loads(api.headers or "{}")
            except Exception:
                headers = {}
            try:
                params = json.loads(api.params or "{}")
            except Exception:
                params = {}

            header_list = [{"key": k, "value": v} for k, v in headers.items()]
            query_list  = [{"key": k, "value": v} for k, v in params.items()]

            body_obj = None
            if api.body_type == "json":
                body_obj = {"mode": "raw", "raw": api.body or "",
                            "options": {"raw": {"language": "json"}}}
            elif api.body_type == "form":
                try:
                    form = json.loads(api.body or "{}")
                    body_obj = {"mode": "urlencoded",
                                "urlencoded": [{"key": k, "value": v} for k, v in form.items()]}
                except Exception:
                    body_obj = {"mode": "raw", "raw": api.body or ""}
            elif api.body_type == "raw":
                body_obj = {"mode": "raw", "raw": api.body or ""}

            item = {
                "name": api.name,
                "request": {
                    "method": api.method,
                    "header": header_list,
                    "url": {
                        "raw": api.path,
                        "path": [p for p in api.path.split("/") if p],
                        "query": query_list,
                    },
                    "description": api.description,
                },
            }
            if body_obj:
                item["request"]["body"] = body_obj
            items.append(item)

        return {"name": col.name, "item": items,
                "description": col.description}

    root_items = []
    for col in collections:
        if col.parent_id is None:
            root_items.append(_build_item(col))

    collection = {
        "info": {
            "name": proj.name,
            "description": proj.description,
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "item": root_items,
    }
    return JSONResponse(content=collection, headers={
        "Content-Disposition": f'attachment; filename="{proj.name}.postman_collection.json"'
    })


@router.get("/export/openapi/{project_id}")
def export_openapi(project_id: int, db: Session = Depends(get_db)):
    """导出为 OpenAPI 3.0 规范"""
    proj = db.query(Project).filter(Project.id == project_id).first()
    if not proj:
        raise HTTPException(404)

    collections = db.query(Collection).filter(
        Collection.project_id == project_id).all()
    apis = db.query(Api).join(Collection).filter(
        Collection.project_id == project_id).all()

    col_name_map = {c.id: c.name for c in collections}

    paths: dict = {}
    tags_set: set = set()

    for api in apis:
        tag = col_name_map.get(api.collection_id, "默认")
        tags_set.add(tag)

        try:
            headers = json.loads(api.headers or "{}")
        except Exception:
            headers = {}
        try:
            params = json.loads(api.params or "{}")
        except Exception:
            params = {}

        parameters = []
        for k, v in headers.items():
            parameters.append({"name": k, "in": "header",
                                "schema": {"type": "string"}, "example": v})
        for k, v in params.items():
            parameters.append({"name": k, "in": "query",
                                "schema": {"type": "string"}, "example": v})

        operation: dict = {
            "summary": api.name,
            "description": api.description,
            "tags": [tag],
            "parameters": parameters,
            "responses": {"200": {"description": "成功"}},
        }

        if api.body_type in ("json", "form", "raw", "graphql") and api.body:
            ct = "application/json" if api.body_type in ("json", "graphql") else "application/x-www-form-urlencoded"
            try:
                example = json.loads(api.body)
            except Exception:
                example = api.body
            operation["requestBody"] = {
                "content": {ct: {"example": example}}
            }

        path_key = api.path if api.path.startswith("/") else "/" + api.path
        paths.setdefault(path_key, {})[api.method.lower()] = operation

    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": proj.name,
            "description": proj.description,
            "version": "1.0.0",
        },
        "servers": [{"url": proj.base_url or "/"}],
        "tags": [{"name": t} for t in sorted(tags_set)],
        "paths": paths,
    }
    return JSONResponse(content=spec, headers={
        "Content-Disposition": f'attachment; filename="{proj.name}.openapi.json"'
    })


@router.get("/export/apifox/{project_id}")
def export_apifox(project_id: int, db: Session = Depends(get_db)):
    """导出为 Apifox 兼容格式（OpenAPI 3.0 + Apifox 扩展）"""
    # Apifox 可以直接导入 OpenAPI 3.0，复用该逻辑
    return export_openapi(project_id, db)
