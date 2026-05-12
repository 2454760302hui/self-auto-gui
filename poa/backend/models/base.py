"""数据库基础模型"""
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "poa.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── 工作空间 ──────────────────────────────────────────────────
class Workspace(Base):
    __tablename__ = "workspaces"
    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(100), nullable=False)
    description = Column(Text, default="")
    created_at  = Column(DateTime, default=datetime.now)
    projects    = relationship("Project", back_populates="workspace", cascade="all, delete")


# ── 项目 ──────────────────────────────────────────────────────
class Project(Base):
    __tablename__ = "projects"
    id           = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)
    name         = Column(String(100), nullable=False)
    description  = Column(Text, default="")
    base_url     = Column(String(500), default="")
    created_at   = Column(DateTime, default=datetime.now)
    workspace    = relationship("Workspace", back_populates="projects")
    collections  = relationship("Collection", back_populates="project", cascade="all, delete")
    environments = relationship("Environment", back_populates="project", cascade="all, delete")
    test_runs    = relationship("TestRun", back_populates="project", cascade="all, delete")


# ── 集合（文件夹） ────────────────────────────────────────────
class Collection(Base):
    __tablename__ = "collections"
    id          = Column(Integer, primary_key=True, index=True)
    project_id  = Column(Integer, ForeignKey("projects.id"), nullable=False)
    parent_id   = Column(Integer, ForeignKey("collections.id"), nullable=True)
    name        = Column(String(100), nullable=False)
    description = Column(Text, default="")
    sort_order  = Column(Integer, default=0)
    created_at  = Column(DateTime, default=datetime.now)
    project     = relationship("Project", back_populates="collections")
    apis        = relationship("Api", back_populates="collection", cascade="all, delete")
    children    = relationship("Collection", backref="parent", remote_side=[id])


# ── API 接口 ──────────────────────────────────────────────────
class Api(Base):
    __tablename__ = "apis"
    id            = Column(Integer, primary_key=True, index=True)
    collection_id = Column(Integer, ForeignKey("collections.id"), nullable=False)
    name          = Column(String(200), nullable=False)
    method        = Column(String(10), default="GET")
    path          = Column(String(500), nullable=False)
    description   = Column(Text, default="")
    # 请求配置（JSON 字符串）
    headers       = Column(Text, default="{}")
    params        = Column(Text, default="{}")
    body_type     = Column(String(20), default="none")   # none/json/form/raw/binary
    body          = Column(Text, default="")
    # 前置/后置脚本
    pre_script    = Column(Text, default="")
    post_script   = Column(Text, default="")
    # 断言
    assertions    = Column(Text, default="[]")
    # 提取变量
    extractions   = Column(Text, default="[]")
    # 标签
    tags          = Column(String(200), default="")
    status        = Column(String(20), default="active")  # active/deprecated
    created_at    = Column(DateTime, default=datetime.now)
    updated_at    = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    collection    = relationship("Collection", back_populates="apis")
    history       = relationship("RequestHistory", back_populates="api", cascade="all, delete")


# ── 环境变量 ──────────────────────────────────────────────────
class Environment(Base):
    __tablename__ = "environments"
    id         = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name       = Column(String(100), nullable=False)
    variables  = Column(Text, default="{}")   # JSON: {key: {value, enabled, secret}}
    is_active  = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    project    = relationship("Project", back_populates="environments")


# ── 全局变量 ──────────────────────────────────────────────────
class GlobalVariable(Base):
    __tablename__ = "global_variables"
    id         = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    key        = Column(String(100), nullable=False)
    value      = Column(Text, default="")
    enabled    = Column(Boolean, default=True)
    secret     = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)


# ── 请求历史 ──────────────────────────────────────────────────
class RequestHistory(Base):
    __tablename__ = "request_history"
    id           = Column(Integer, primary_key=True, index=True)
    api_id       = Column(Integer, ForeignKey("apis.id"), nullable=True)
    method       = Column(String(10))
    url          = Column(String(500))
    request_data = Column(Text, default="{}")
    response_status = Column(Integer)
    response_time   = Column(Float)
    response_body   = Column(Text, default="")
    response_headers = Column(Text, default="{}")
    created_at   = Column(DateTime, default=datetime.now)
    api          = relationship("Api", back_populates="history")


# ── 测试套件 ──────────────────────────────────────────────────
class TestSuite(Base):
    __tablename__ = "test_suites"
    id          = Column(Integer, primary_key=True, index=True)
    project_id  = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name        = Column(String(100), nullable=False)
    description = Column(Text, default="")
    steps       = Column(Text, default="[]")   # JSON: [{api_id, name, ...}]
    created_at  = Column(DateTime, default=datetime.now)


# ── 测试运行记录 ──────────────────────────────────────────────
class TestRun(Base):
    __tablename__ = "test_runs"
    id          = Column(Integer, primary_key=True, index=True)
    project_id  = Column(Integer, ForeignKey("projects.id"), nullable=False)
    suite_name  = Column(String(100), default="")
    status      = Column(String(20), default="running")  # running/passed/failed
    total       = Column(Integer, default=0)
    passed      = Column(Integer, default=0)
    failed      = Column(Integer, default=0)
    duration    = Column(Float, default=0)
    results     = Column(Text, default="[]")   # JSON 详细结果
    created_at  = Column(DateTime, default=datetime.now)
    project     = relationship("Project", back_populates="test_runs")


# ── Mock 规则 ─────────────────────────────────────────────────
class MockRule(Base):
    __tablename__ = "mock_rules"
    id          = Column(Integer, primary_key=True, index=True)
    project_id  = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name        = Column(String(100), nullable=False)
    method      = Column(String(10), default="GET")
    path        = Column(String(500), nullable=False)
    response_status  = Column(Integer, default=200)
    response_headers = Column(Text, default="{}")
    response_body    = Column(Text, default="{}")
    delay       = Column(Integer, default=0)   # 模拟延迟 ms
    enabled     = Column(Boolean, default=True)
    created_at  = Column(DateTime, default=datetime.now)


# ── Cookie Jar ────────────────────────────────────────────────
class CookieJar(Base):
    __tablename__ = "cookie_jars"
    id         = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name       = Column(String(100), nullable=False)
    domain     = Column(String(200), default="")
    cookies    = Column(Text, default="[]")   # [{name,value,domain,path,expires,httpOnly,secure}]
    created_at = Column(DateTime, default=datetime.now)


# ── SSL 证书 ──────────────────────────────────────────────────
class Certificate(Base):
    __tablename__ = "certificates"
    id          = Column(Integer, primary_key=True, index=True)
    project_id  = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name        = Column(String(100), nullable=False)
    host        = Column(String(200), nullable=False)
    cert_pem    = Column(Text, default="")   # PEM 格式证书内容
    key_pem     = Column(Text, default="")   # 私钥
    passphrase  = Column(String(200), default="")
    enabled     = Column(Boolean, default=True)
    created_at  = Column(DateTime, default=datetime.now)


# ── 定时任务 ──────────────────────────────────────────────────
class ScheduledTask(Base):
    __tablename__ = "scheduled_tasks"
    id          = Column(Integer, primary_key=True, index=True)
    project_id  = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name        = Column(String(100), nullable=False)
    suite_id    = Column(Integer, ForeignKey("test_suites.id"), nullable=True)
    cron        = Column(String(100), default="")   # cron 表达式
    enabled     = Column(Boolean, default=True)
    environment_id = Column(Integer, ForeignKey("environments.id"), nullable=True)
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    created_at  = Column(DateTime, default=datetime.now)


# ── API 文档版本 ──────────────────────────────────────────────
class ApiDoc(Base):
    __tablename__ = "api_docs"
    id          = Column(Integer, primary_key=True, index=True)
    project_id  = Column(Integer, ForeignKey("projects.id"), nullable=False)
    version     = Column(String(50), default="1.0.0")
    title       = Column(String(200), default="")
    content     = Column(Text, default="{}")   # OpenAPI JSON
    is_public   = Column(Boolean, default=False)
    share_token = Column(String(64), default="")
    created_at  = Column(DateTime, default=datetime.now)


# ── 团队成员 ──────────────────────────────────────────────────
class TeamMember(Base):
    __tablename__ = "team_members"
    id           = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)
    username     = Column(String(100), nullable=False)
    email        = Column(String(200), default="")
    role         = Column(String(20), default="viewer")  # owner/editor/viewer
    created_at   = Column(DateTime, default=datetime.now)


# ── 接口变更记录 ──────────────────────────────────────────────
class ApiChangelog(Base):
    __tablename__ = "api_changelogs"
    id         = Column(Integer, primary_key=True, index=True)
    api_id     = Column(Integer, ForeignKey("apis.id"), nullable=False)
    operator   = Column(String(100), default="")
    action     = Column(String(20), default="update")  # create/update/delete
    snapshot   = Column(Text, default="{}")   # 变更前的快照
    created_at = Column(DateTime, default=datetime.now)


def init_db():
    # 确保所有模型都已导入后再建表
    # auth.py 中的 User/APIKey 模型通过 Base.metadata 自动注册
    Base.metadata.create_all(bind=engine)
