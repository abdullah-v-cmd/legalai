"""Security utilities - JWT, Password hashing, Rate limiting"""
from datetime import datetime, timedelta
from typing import Optional, Dict
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Request
from app.core.config import settings
import hashlib
import secrets
import re

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# In-memory store for failed login attempts (use Redis in production)
_login_attempts: Dict[str, dict] = {}


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def validate_password_strength(password: str) -> bool:
    """Enforce strong password policy"""
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'\d', password):
        return False
    return True


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def generate_api_key() -> str:
    return f"legalai-{secrets.token_urlsafe(32)}"


def record_login_attempt(ip: str, success: bool):
    now = datetime.utcnow()
    if ip not in _login_attempts:
        _login_attempts[ip] = {"count": 0, "locked_until": None}
    
    if success:
        _login_attempts[ip] = {"count": 0, "locked_until": None}
        return
    
    _login_attempts[ip]["count"] += 1
    if _login_attempts[ip]["count"] >= settings.MAX_LOGIN_ATTEMPTS:
        _login_attempts[ip]["locked_until"] = now + timedelta(minutes=settings.LOCKOUT_DURATION_MINUTES)


def is_ip_locked(ip: str) -> bool:
    if ip not in _login_attempts:
        return False
    locked_until = _login_attempts[ip].get("locked_until")
    if locked_until and datetime.utcnow() < locked_until:
        return True
    if locked_until:
        _login_attempts[ip] = {"count": 0, "locked_until": None}
    return False


def sanitize_input(text: str) -> str:
    """Basic input sanitization"""
    import bleach
    return bleach.clean(text, tags=[], strip=True)
