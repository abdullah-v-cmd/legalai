"""Authentication Service"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from fastapi import HTTPException, status
from datetime import datetime
from app.models.user import User, UserRole
from app.core.security import (
    hash_password, verify_password, create_access_token,
    create_refresh_token, generate_api_key, record_login_attempt,
    is_ip_locked, validate_password_strength
)
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class AuthService:
    async def register(self, db: AsyncSession, username: str, email: str,
                        password: str, full_name: str = "") -> User:
        """Register a new user"""
        # Check username uniqueness
        result = await db.execute(select(User).where(User.username == username))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Username already taken")
        
        # Check email uniqueness
        result = await db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Validate password
        if not validate_password_strength(password):
            raise HTTPException(
                status_code=400,
                detail="Password must be at least 8 chars with uppercase, lowercase, and digit"
            )
        
        user = User(
            username=username,
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            api_key=generate_api_key(),
            is_verified=True,  # Auto-verify for demo
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info(f"New user registered: {username}")
        return user
    
    async def login(self, db: AsyncSession, username_or_email: str, 
                     password: str, ip: str = "0.0.0.0") -> dict:
        """Login user and return tokens"""
        # Check IP lockout
        if is_ip_locked(ip):
            raise HTTPException(
                status_code=429,
                detail=f"Too many failed attempts. Try again in {settings.LOCKOUT_DURATION_MINUTES} minutes."
            )
        
        # Find user
        result = await db.execute(
            select(User).where(
                (User.username == username_or_email) | (User.email == username_or_email)
            )
        )
        user = result.scalar_one_or_none()
        
        if not user or not verify_password(password, user.hashed_password):
            record_login_attempt(ip, success=False)
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account disabled")
        
        # Update last login
        user.last_login = datetime.utcnow()
        await db.commit()
        
        record_login_attempt(ip, success=True)
        
        token_data = {"sub": str(user.id), "username": user.username, "role": user.role}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        logger.info(f"User logged in: {user.username}")
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "api_key": user.api_key,
            }
        }
    
    async def get_current_user(self, db: AsyncSession, user_id: int) -> User:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    
    async def create_admin(self, db: AsyncSession) -> User:
        """Create initial admin user if not exists"""
        result = await db.execute(select(User).where(User.username == settings.ADMIN_USERNAME))
        existing = result.scalar_one_or_none()
        if existing:
            return existing
        
        admin = User(
            username=settings.ADMIN_USERNAME,
            email=settings.ADMIN_EMAIL,
            hashed_password=hash_password(settings.ADMIN_PASSWORD),
            full_name="LegalAI Administrator",
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True,
            api_key=generate_api_key(),
        )
        db.add(admin)
        await db.commit()
        await db.refresh(admin)
        logger.info("Admin user created")
        return admin


auth_service = AuthService()
