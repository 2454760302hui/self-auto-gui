"""POA 种子数据 —— 演示 workspace、project、示例 API 和测试套件"""
import json
from .models.base import SessionLocal, Base, engine, Workspace, Project, Collection, Api, Environment, TestSuite

DEMO_APIS = [
    # ── 用户管理 ──────────────────────────────────────────────
    {"name": "用户登录", "method": "POST", "path": "/api/auth/login",
     "headers": json.dumps({"Content-Type": "application/json"}),
     "body_type": "json", "body": json.dumps({"username": "admin", "password": "{{password}}"}, ensure_ascii=False),
     "assertions": json.dumps([{"type": "eq", "source": "status", "expected": 200}]),
     "extractions": json.dumps([{"key": "token", "expression": "$.token", "enabled": True}])},
    {"name": "获取用户信息", "method": "GET", "path": "/api/auth/me",
     "headers": json.dumps({"Authorization": "Bearer {{token}}"}),
     "assertions": json.dumps([{"type": "eq", "source": "status", "expected": 200}])},
    {"name": "修改密码", "method": "PUT", "path": "/api/auth/password",
     "headers": json.dumps({"Content-Type": "application/json", "Authorization": "Bearer {{token}}"}),
     "body_type": "json", "body": json.dumps({"old_password": "{{password}}", "new_password": "newpass123"}, ensure_ascii=False),
     "assertions": json.dumps([{"type": "eq", "source": "status", "expected": 200}])},

    # ── 项目管理 ──────────────────────────────────────────────
    {"name": "获取项目列表", "method": "GET", "path": "/api/projects",
     "assertions": json.dumps([{"type": "eq", "source": "status", "expected": 200}])},
    {"name": "创建项目", "method": "POST", "path": "/api/projects",
     "headers": json.dumps({"Content-Type": "application/json"}),
     "body_type": "json", "body": json.dumps({"workspace_id": 1, "name": "测试项目-{{timestamp()}}", "base_url": "http://httpbin.org"}, ensure_ascii=False),
     "assertions": json.dumps([{"type": "eq", "source": "status", "expected": 200}]),
     "extractions": json.dumps([{"key": "project_id", "expression": "$.id", "enabled": True}])},
    {"name": "获取项目详情", "method": "GET", "path": "/api/projects/{{project_id}}",
     "assertions": json.dumps([{"type": "eq", "source": "status", "expected": 200}])},

    # ── HTTPBin 测试 ─────────────────────────────────────────
    {"name": "GET 请求测试", "method": "GET", "path": "https://httpbin.org/get",
     "params": json.dumps({"foo": "bar", "ts": "{{timestamp()}}"}),
     "assertions": json.dumps([
         {"type": "eq", "source": "status", "expected": 200},
         {"type": "contains", "source": "body", "path": "url", "expected": "foo=bar"},
     ])},
    {"name": "POST JSON 测试", "method": "POST", "path": "https://httpbin.org/post",
     "headers": json.dumps({"Content-Type": "application/json"}),
     "body_type": "json", "body": json.dumps({"name": "{{fake.name()}}", "email": "{{fake.email()}}"}, ensure_ascii=False),
     "assertions": json.dumps([
         {"type": "eq", "source": "status", "expected": 200},
         {"type": "exists", "source": "body", "path": "json.name"},
     ])},
    {"name": "PUT 测试", "method": "PUT", "path": "https://httpbin.org/put",
     "headers": json.dumps({"Content-Type": "application/json"}),
     "body_type": "json", "body": json.dumps({"id": 1, "status": "updated"}, ensure_ascii=False),
     "assertions": json.dumps([{"type": "eq", "source": "status", "expected": 200}])},
    {"name": "DELETE 测试", "method": "DELETE", "path": "https://httpbin.org/delete",
     "assertions": json.dumps([{"type": "eq", "source": "status", "expected": 200}])},
    {"name": "响应延迟测试", "method": "GET", "path": "https://httpbin.org/delay/1",
     "assertions": json.dumps([
         {"type": "eq", "source": "status", "expected": 200},
         {"type": "lt", "source": "response_time", "expected": 5000},
     ])},
    {"name": "404 测试", "method": "GET", "path": "https://httpbin.org/status/404",
     "assertions": json.dumps([{"type": "eq", "source": "status", "expected": 404}])},
    {"name": "Cookie 测试", "method": "GET", "path": "https://httpbin.org/cookies/set?test_cookie=hello",
     "assertions": json.dumps([{"type": "eq", "source": "status", "expected": 200}])},
]


def seed():
    """插入演示数据"""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if db.query(Workspace).count() > 0:
        print("Database already has data, skipping seed")
        db.close()
        return

    # 工作区
    ws = Workspace(name="演示工作区", description="POA API 测试平台 - 演示数据")
    db.add(ws); db.flush()

    # 项目
    proj = Project(workspace_id=ws.id, name="HTTPBin 测试项目",
                   description="基于 httpbin.org 的 API 测试示例",
                   base_url="https://httpbin.org")
    db.add(proj); db.flush()

    # 集合
    user_col = Collection(project_id=proj.id, name="认证接口", sort_order=1)
    proj_col = Collection(project_id=proj.id, name="项目管理", sort_order=2)
    httpbin_col = Collection(project_id=proj.id, name="HTTPBin 基础测试", sort_order=3)
    db.add_all([user_col, proj_col, httpbin_col]); db.flush()

    # API
    for i, api_data in enumerate(DEMO_APIS):
        if i < 3:
            col_id = user_col.id
        elif i < 6:
            col_id = proj_col.id
        else:
            col_id = httpbin_col.id
        api = Api(collection_id=col_id, **api_data)
        db.add(api)

    # 环境
    env_test = Environment(project_id=proj.id, name="测试环境", is_active=True,
                           variables=json.dumps({"base_url": "https://httpbin.org", "password": "admin123"}))
    env_prod = Environment(project_id=proj.id, name="生产环境", is_active=False,
                           variables=json.dumps({"base_url": "https://api.example.com", "password": ""}))
    db.add_all([env_test, env_prod])

    # 测试套件
    suite = TestSuite(project_id=proj.id, name="HTTPBin 冒烟测试",
                      description="验证 HTTPBin 所有基础接口",
                      steps=json.dumps([
                          {"api_id": i + 1, "name": api["name"], "enabled": True}
                          for i, api in enumerate(DEMO_APIS) if i >= 6
                      ]))
    db.add(suite)

    db.commit()
    db.close()
    print("Seed data loaded: 1 workspace, 1 project, 3 collections, %d APIs, 2 environments, 1 test suite" % len(DEMO_APIS))


if __name__ == '__main__':
    seed()
