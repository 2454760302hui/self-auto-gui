"""用户认证模块"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, timedelta
import os
import hashlib
import secrets
import time

from ..models.base import get_db, Base, engine
from passlib.context import CryptContext
from jose import JWTError, jwt

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ── 配置 ──────────────────────────────────────────────────────
SECRET_KEY = os.environ.get("POA_SECRET")
if not SECRET_KEY:
    import warnings
    SECRET_KEY = "dev-mode-secret-do-not-use-in-production"
    warnings.warn(
        "POA_SECRET 未设置，使用开发模式密钥。"
        "生产环境请设置 POA_SECRET 环境变量。"
    )
ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


# ── 模型（直接在文件内定义，不修改 base.py） ──────────────────
class User(Base):
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}
    id              = Column(Integer, primary_key=True, index=True)
    username        = Column(String(100), unique=True, nullable=False)
    email           = Column(String(200), unique=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    is_active       = Column(Boolean, default=True)
    role            = Column(String(20), default="user")  # admin/user
    created_at      = Column(DateTime, default=datetime.now)


class APIKey(Base):
    __tablename__ = "api_keys"
    __table_args__ = {"extend_existing": True}
    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    name        = Column(String(100), nullable=False)
    key_hash    = Column(String(200), nullable=False, unique=True)
    last_used_at = Column(DateTime, nullable=True)
    created_at  = Column(DateTime, default=datetime.now)


# 建表
Base.metadata.create_all(bind=engine)


# ── Schemas ───────────────────────────────────────────────────
class RegisterBody(BaseModel):
    username: str
    email: EmailStr
    password: str

class LoginBody(BaseModel):
    username: str
    password: str

class PasswordChangeBody(BaseModel):
    old_password: str
    new_password: str

class APIKeyCreate(BaseModel):
    name: str


# ── 工具函数 ──────────────────────────────────────────────────
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_token(user_id: int, username: str) -> str:
    expire = datetime.utcnow() + timedelta(days=TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(user_id), "username": username, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "未提供认证凭据")
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub", 0))
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token 无效或已过期")
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户不存在")
    return user


# ── 登录限速 ──────────────────────────────────────────────────
_login_attempts: dict = {}  # {ip: [timestamp, ...]}
_MAX_LOGIN_ATTEMPTS = 10
_LOGIN_WINDOW = 300  # 5 分钟

def _check_login_rate(ip: str):
    now = time.time()
    attempts = _login_attempts.get(ip, [])
    # 清理过期记录
    attempts = [t for t in attempts if now - t < _LOGIN_WINDOW]
    _login_attempts[ip] = attempts
    if len(attempts) >= _MAX_LOGIN_ATTEMPTS:
        raise HTTPException(429, f"登录尝试过于频繁，请 {_LOGIN_WINDOW // 60} 分钟后重试")

def _record_login_attempt(ip: str):
    _login_attempts.setdefault(ip, []).append(time.time())


# ── 端点 ──────────────────────────────────────────────────────
@router.post("/register")
def register(data: RegisterBody, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(400, "用户名已存在")
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(400, "邮箱已被注册")
    user = User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
    )
    db.add(user); db.commit(); db.refresh(user)
    token = create_token(user.id, user.username)
    return {"token": token, "user": {"id": user.id, "username": user.username, "email": user.email, "role": user.role}}


@router.post("/login")
def login(request: Request, data: LoginBody, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    _check_login_rate(client_ip)
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.hashed_password):
        _record_login_attempt(client_ip)
        raise HTTPException(401, "用户名或密码错误")
    if not user.is_active:
        raise HTTPException(403, "账号已被禁用")
    token = create_token(user.id, user.username)
    return {"token": token, "user": {"id": user.id, "username": user.username, "email": user.email, "role": user.role}}


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at,
    }


@router.post("/logout")
def logout():
    return {"ok": True, "message": "已登出，请客户端清除 token"}


@router.post("/api-keys")
def create_api_key(
    data: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    raw_key = "poa_" + secrets.token_urlsafe(32)
    api_key = APIKey(
        user_id=current_user.id,
        name=data.name,
        key_hash=hash_api_key(raw_key),
    )
    db.add(api_key); db.commit(); db.refresh(api_key)
    return {"id": api_key.id, "name": api_key.name, "key": raw_key, "created_at": api_key.created_at}


@router.get("/api-keys")
def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    keys = db.query(APIKey).filter(APIKey.user_id == current_user.id).all()
    return [{"id": k.id, "name": k.name, "last_used_at": k.last_used_at, "created_at": k.created_at} for k in keys]


@router.delete("/api-keys/{key_id}")
def delete_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    key = db.query(APIKey).filter(APIKey.id == key_id, APIKey.user_id == current_user.id).first()
    if not key:
        raise HTTPException(404, "API Key 不存在")
    db.delete(key); db.commit()
    return {"ok": True}


@router.put("/password")
def change_password(
    data: PasswordChangeBody,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(data.old_password, current_user.hashed_password):
        raise HTTPException(400, "旧密码错误")
    current_user.hashed_password = hash_password(data.new_password)
    db.commit()
    return {"ok": True}
