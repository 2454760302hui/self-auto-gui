"""请求执行 / 测试套件 / 历史记录 路由"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Any
from ..models.base import get_db, Api, Environment, GlobalVariable, TestSuite, TestRun, RequestHistory
from ..core.engine import execute_request, execute_suite
from .auth import get_current_user
import json
import asyncio

router = APIRouter(prefix="/api", tags=["runner"], dependencies=[Depends(get_current_user)])


# ── Schemas ───────────────────────────────────────────────────
class RunRequest(BaseModel):
    api_id: Optional[int] = None
    # 或者直接传配置（快速调试）
    method: Optional[str] = "GET"
    url: Optional[str] = ""
    headers: Optional[Any] = {}
    params: Optional[Any] = {}
    body_type: Optional[str] = "none"
    body: Optional[str] = ""
    pre_script: Optional[str] = ""
    post_script: Optional[str] = ""
    assertions: Optional[list] = []
    extractions: Optional[list] = []
    environment_id: Optional[int] = None
    project_id: Optional[int] = None
    timeout: Optional[float] = 30.0

class SuiteCreate(BaseModel):
    project_id: int
    name: str
    description: str = ""
    steps: list = []

class SuiteRun(BaseModel):
    suite_id: Optional[int] = None
    steps: Optional[list] = None
    environment_id: Optional[int] = None
    project_id: Optional[int] = None


# ── 变量合并 ──────────────────────────────────────────────────
def _merge_variables(project_id: Optional[int],
                     environment_id: Optional[int],
                     db: Session) -> dict:
    variables = {}
    if project_id:
        for gv in db.query(GlobalVariable).filter(
                GlobalVariable.project_id == project_id,
                GlobalVariable.enabled == True).all():
            variables[gv.key] = gv.value
    if environment_id:
        env = db.query(Environment).filter(Environment.id == environment_id).first()
        if env:
            env_vars = json.loads(env.variables or '{}')
            for k, v in env_vars.items():
                if isinstance(v, dict):
                    if v.get('enabled', True):
                        variables[k] = v.get('value', '')
                else:
                    variables[k] = v
    return variables


# ── 单接口执行 ────────────────────────────────────────────────
@router.post("/run")
async def run_api(data: RunRequest, db: Session = Depends(get_db)):
    variables = _merge_variables(data.project_id, data.environment_id, db)

    if data.api_id:
        api = db.query(Api).filter(Api.id == data.api_id).first()
        if not api:
            raise HTTPException(404, "API not found")
        api_config = {
            'method':      api.method,
            'url':         api.path,
            'headers':     json.loads(api.headers or '{}'),
            'params':      json.loads(api.params or '{}'),
            'body_type':   api.body_type,
            'body':        api.body,
            'pre_script':  api.pre_script,
            'post_script': api.post_script,
            'assertions':  json.loads(api.assertions or '[]'),
            'extractions': json.loads(api.extractions or '[]'),
        }
    else:
        api_config = {
            'method':      data.method,
            'url':         data.url,
            'headers':     data.headers or {},
            'params':      data.params or {},
            'body_type':   data.body_type,
            'body':        data.body,
            'pre_script':  data.pre_script,
            'post_script': data.post_script,
            'assertions':  data.assertions or [],
            'extractions': data.extractions or [],
        }

    result = await execute_request(api_config, variables, timeout=data.timeout)

    # 保存历史
    if data.api_id:
        hist = RequestHistory(
            api_id=data.api_id,
            method=api_config['method'],
            url=api_config['url'],
            request_data=json.dumps(api_config, ensure_ascii=False, default=str),
            response_status=result['response'].get('status_code', 0),
            response_time=result['response'].get('elapsed_ms', 0),
            response_body=result['response'].get('text', '')[:10000],
            response_headers=json.dumps(result['response'].get('headers', {})),
        )
        db.add(hist); db.commit()

    return result


# ── 测试套件 CRUD ─────────────────────────────────────────────
@router.get("/suites")
def list_suites(project_id: int, db: Session = Depends(get_db)):
    suites = db.query(TestSuite).filter(TestSuite.project_id == project_id).all()
    result = []
    for s in suites:
        d = {c.name: getattr(s, c.name) for c in s.__table__.columns}
        try:
            d['steps'] = json.loads(d['steps'] or '[]')
        except Exception:
            pass
        result.append(d)
    return result

@router.post("/suites")
def create_suite(data: SuiteCreate, db: Session = Depends(get_db)):
    suite = TestSuite(
        project_id=data.project_id,
        name=data.name,
        description=data.description,
        steps=json.dumps(data.steps, ensure_ascii=False),
    )
    db.add(suite); db.commit(); db.refresh(suite)
    return suite

@router.put("/suites/{suite_id}")
def update_suite(suite_id: int, data: SuiteCreate, db: Session = Depends(get_db)):
    suite = db.query(TestSuite).filter(TestSuite.id == suite_id).first()
    if not suite:
        raise HTTPException(404)
    suite.name        = data.name
    suite.description = data.description
    suite.steps       = json.dumps(data.steps, ensure_ascii=False)
    db.commit(); db.refresh(suite)
    return suite

@router.delete("/suites/{suite_id}")
def delete_suite(suite_id: int, db: Session = Depends(get_db)):
    suite = db.query(TestSuite).filter(TestSuite.id == suite_id).first()
    if not suite:
        raise HTTPException(404)
    db.delete(suite); db.commit()
    return {"ok": True}


# ── 套件执行（HTTP） ──────────────────────────────────────────
@router.post("/suites/run")
async def run_suite(data: SuiteRun, db: Session = Depends(get_db)):
    variables = _merge_variables(data.project_id, data.environment_id, db)

    if data.suite_id:
        suite = db.query(TestSuite).filter(TestSuite.id == data.suite_id).first()
        if not suite:
            raise HTTPException(404)
        steps = json.loads(suite.steps or '[]')
        suite_name = suite.name
    else:
        steps = data.steps or []
        suite_name = "临时运行"

    # 补全步骤中的 api 配置
    enriched_steps = []
    for step in steps:
        api_id = step.get('api_id')
        if api_id:
            api = db.query(Api).filter(Api.id == api_id).first()
            if api:
                enriched_steps.append({
                    'name':        step.get('name', api.name),
                    'method':      api.method,
                    'url':         api.path,
                    'headers':     json.loads(api.headers or '{}'),
                    'params':      json.loads(api.params or '{}'),
                    'body_type':   api.body_type,
                    'body':        api.body,
                    'pre_script':  api.pre_script,
                    'post_script': api.post_script,
                    'assertions':  json.loads(api.assertions or '[]'),
                    'extractions': json.loads(api.extractions or '[]'),
                    'variables':   step.get('variables', {}),
                    'enabled':     step.get('enabled', True),
                    'stop_on_failure': step.get('stop_on_failure', False),
                })
        else:
            enriched_steps.append(step)

    result = await execute_suite(enriched_steps, variables)

    # 保存运行记录
    if data.project_id:
        run = TestRun(
            project_id=data.project_id,
            suite_name=suite_name,
            status=result['status'],
            total=result['total'],
            passed=result['passed'],
            failed=result['failed'],
            duration=result['duration'],
            results=json.dumps(result['results'], ensure_ascii=False, default=str),
        )
        db.add(run); db.commit()

    return result


# ── 套件执行（WebSocket 实时推送，通过 query param 认证） ──────
ws_router = APIRouter(prefix="/api", tags=["ws"])

@ws_router.websocket("/ws/run")
async def ws_run_suite(websocket: WebSocket, db: Session = Depends(get_db)):
    """WebSocket 实时推送每步执行结果（token 通过 ?token=xxx 传入）"""
    # 从 query param 验证 token
    token = websocket.query_params.get("token", "")
    try:
        from jose import jwt as _jwt
        from .auth import SECRET_KEY, ALGORITHM
        _jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        await websocket.close(code=4001, reason="认证失败")
        return

    await websocket.accept()
    try:
        raw = await websocket.receive_json()
        data = SuiteRun(**raw)
        variables = _merge_variables(data.project_id, data.environment_id, db)

        steps = data.steps or []
        if data.suite_id:
            suite = db.query(TestSuite).filter(TestSuite.id == data.suite_id).first()
            if suite:
                steps = json.loads(suite.steps or '[]')

        async def on_step_done(step_result):
            await websocket.send_json({
                'type':   'step',
                'data':   step_result,
            })

        result = await execute_suite(steps, variables, on_step_done=on_step_done)
        await websocket.send_json({'type': 'done', 'data': result})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({'type': 'error', 'message': str(e)})


# ── 历史记录 ──────────────────────────────────────────────────

class BatchDeleteBody(BaseModel):
    ids: list

@router.delete("/history/batch")
def batch_delete_history(body: BatchDeleteBody, db: Session = Depends(get_db)):
    """批量删除历史记录（必须在 /history/{hist_id} 之前注册）"""
    if not body.ids:
        return {"ok": True, "deleted": 0}
    deleted = db.query(RequestHistory).filter(
        RequestHistory.id.in_(body.ids)
    ).delete(synchronize_session=False)
    db.commit()
    return {"ok": True, "deleted": deleted}

@router.delete("/history/{hist_id}")
def delete_history(hist_id: int, db: Session = Depends(get_db)):
    h = db.query(RequestHistory).filter(RequestHistory.id == hist_id).first()
    if not h:
        raise HTTPException(404)
    db.delete(h); db.commit()
    return {"ok": True}


# ── 测试运行记录 ──────────────────────────────────────────────
@router.get("/test-runs")
def list_test_runs(project_id: int, limit: int = 20, db: Session = Depends(get_db)):
    runs = db.query(TestRun).filter(
        TestRun.project_id == project_id
    ).order_by(TestRun.created_at.desc()).limit(limit).all()
    result = []
    for r in runs:
        d = {c.name: getattr(r, c.name) for c in r.__table__.columns}
        try:
            d['results'] = json.loads(d['results'] or '[]')
        except Exception:
            pass
        result.append(d)
    return result


# ── 任务2：补全缺失端点 ────────────────────────────────────────

@router.get("/test-runs/{run_id}")
def get_test_run(run_id: int, db: Session = Depends(get_db)):
    """获取测试运行详情（含完整 results）"""
    run = db.query(TestRun).filter(TestRun.id == run_id).first()
    if not run:
        raise HTTPException(404, "TestRun not found")
    d = {c.name: getattr(run, c.name) for c in run.__table__.columns}
    try:
        d['results'] = json.loads(d['results'] or '[]')
    except Exception:
        pass
    return d


@router.get("/test-runs/{run_id}/report")
def get_test_run_report(run_id: int, db: Session = Depends(get_db)):
    """生成 HTML 格式测试报告"""
    from fastapi.responses import HTMLResponse
    run = db.query(TestRun).filter(TestRun.id == run_id).first()
    if not run:
        raise HTTPException(404, "TestRun not found")
    try:
        results = json.loads(run.results or '[]')
    except Exception:
        results = []

    rows = ""
    for r in results:
        status_color = "#28a745" if r.get("passed") else "#dc3545"
        status_text = "通过" if r.get("passed") else "失败"
        rows += f"""
        <tr>
          <td>{r.get('name', '')}</td>
          <td>{r.get('method', '')}</td>
          <td>{r.get('url', '')}</td>
          <td style="color:{status_color};font-weight:bold">{status_text}</td>
          <td>{r.get('status_code', '')}</td>
          <td>{r.get('elapsed_ms', '')} ms</td>
          <td><pre style="margin:0;font-size:12px">{r.get('error', '')}</pre></td>
        </tr>"""

    pass_rate = round(run.passed / run.total * 100, 1) if run.total else 0
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>测试报告 - {run.suite_name}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
    .header {{ background: #fff; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,.1); }}
    .stats {{ display: flex; gap: 20px; margin: 15px 0; }}
    .stat {{ background: #f8f9fa; padding: 10px 20px; border-radius: 6px; text-align: center; }}
    .stat .num {{ font-size: 28px; font-weight: bold; }}
    .passed {{ color: #28a745; }}
    .failed {{ color: #dc3545; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,.1); }}
    th {{ background: #343a40; color: #fff; padding: 12px; text-align: left; }}
    td {{ padding: 10px 12px; border-bottom: 1px solid #dee2e6; }}
    tr:hover {{ background: #f8f9fa; }}
  </style>
</head>
<body>
  <div class="header">
    <h1>测试报告：{run.suite_name}</h1>
    <p>运行时间：{run.created_at} &nbsp;|&nbsp; 耗时：{run.duration:.2f}s &nbsp;|&nbsp; 状态：<strong>{run.status}</strong></p>
    <div class="stats">
      <div class="stat"><div class="num">{run.total}</div><div>总计</div></div>
      <div class="stat"><div class="num passed">{run.passed}</div><div>通过</div></div>
      <div class="stat"><div class="num failed">{run.failed}</div><div>失败</div></div>
      <div class="stat"><div class="num">{pass_rate}%</div><div>通过率</div></div>
    </div>
  </div>
  <table>
    <thead>
      <tr><th>名称</th><th>方法</th><th>URL</th><th>状态</th><th>状态码</th><th>耗时</th><th>错误信息</th></tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
</body>
</html>"""
    return HTMLResponse(content=html)


@router.delete("/test-runs")
def delete_test_runs(project_id: int, db: Session = Depends(get_db)):
    """批量删除指定项目的所有测试运行记录"""
    deleted = db.query(TestRun).filter(TestRun.project_id == project_id).delete()
    db.commit()
    return {"ok": True, "deleted": deleted}


@router.get("/history")
def get_history_v2(
    api_id: Optional[int] = None,
    status_code: Optional[int] = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """历史记录（支持 status_code 筛选和 limit/offset 分页）"""
    q = db.query(RequestHistory)
    if api_id:
        q = q.filter(RequestHistory.api_id == api_id)
    if status_code is not None:
        q = q.filter(RequestHistory.response_status == status_code)
    total = q.count()
    records = q.order_by(RequestHistory.created_at.desc()).offset(offset).limit(limit).all()
    result = []
    for r in records:
        d = {c.name: getattr(r, c.name) for c in r.__table__.columns}
        for f in ('request_data', 'response_headers'):
            try:
                d[f] = json.loads(d[f] or '{}')
            except Exception:
                pass
        result.append(d)
    return {"total": total, "items": result, "limit": limit, "offset": offset}


@router.post("/history/{hist_id}/replay")
async def replay_history(hist_id: int, db: Session = Depends(get_db)):
    """重放历史请求（重新执行并返回结果）"""
    hist = db.query(RequestHistory).filter(RequestHistory.id == hist_id).first()
    if not hist:
        raise HTTPException(404, "History not found")

    try:
        req_data = json.loads(hist.request_data or '{}')
    except Exception:
        req_data = {}

    api_config = {
        'method':      hist.method,
        'url':         hist.url,
        'headers':     req_data.get('headers', {}),
        'params':      req_data.get('params', {}),
        'body_type':   req_data.get('body_type', 'none'),
        'body':        req_data.get('body', ''),
        'pre_script':  req_data.get('pre_script', ''),
        'post_script': req_data.get('post_script', ''),
        'assertions':  req_data.get('assertions', []),
        'extractions': req_data.get('extractions', []),
    }

    result = await execute_request(api_config, {})

    # 保存新的历史记录
    new_hist = RequestHistory(
        api_id=hist.api_id,
        method=hist.method,
        url=hist.url,
        request_data=hist.request_data,
        response_status=result['response'].get('status_code', 0),
        response_time=result['response'].get('elapsed_ms', 0),
        response_body=result['response'].get('text', '')[:10000],
        response_headers=json.dumps(result['response'].get('headers', {})),
    )
    db.add(new_hist); db.commit()

    return result
