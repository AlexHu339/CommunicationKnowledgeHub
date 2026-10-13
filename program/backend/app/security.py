from __future__ import annotations
from datetime import datetime, timedelta
import hashlib, secrets
from fastapi import Depends, HTTPException, Request
from argon2 import PasswordHasher
from sqlalchemy.orm import Session
from .database import get_db
from .models import AuthSession, UserAccount

ph = PasswordHasher()

def is_loopback(request: Request) -> bool:
    host = request.client.host if request.client else ""
    return host in {"127.0.0.1", "::1", "localhost", "testclient"}

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def require_access(request: Request, db: Session = Depends(get_db)):
    if is_loopback(request):
        return {"mode": "local", "user": "本机用户"}
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "局域网访问需要登录")
    row = db.get(AuthSession, hash_token(auth[7:]))
    if not row or row.expires_at < datetime.utcnow():
        raise HTTPException(401, "会话已过期，请重新登录")
    return {"mode": "lan", "user_id": row.user_id}

def create_session(db: Session, user_id: int) -> tuple[str, datetime]:
    token = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(hours=12)
    db.add(AuthSession(token_hash=hash_token(token), user_id=user_id, expires_at=expires))
    db.commit()
    return token, expires

