"""Authentication API routes"""
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
from app.core.database import get_db
from app.services.auth_service import auth_service
from app.middleware.auth_middleware import require_auth, get_client_ip
from app.models.user import User

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str = ""


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/register")
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    user = await auth_service.register(
        db, data.username, data.email, data.password, data.full_name
    )
    return {
        "message": "Registration successful",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
        }
    }


@router.post("/login")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    ip = get_client_ip(request)
    return await auth_service.login(db, form_data.username, form_data.password, ip)


@router.post("/login/json")
async def login_json(
    data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    ip = get_client_ip(request)
    return await auth_service.login(db, data.username, data.password, ip)


@router.get("/me")
async def get_me(current_user: User = Depends(require_auth)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "api_key": current_user.api_key,
        "total_queries": current_user.total_queries,
        "total_documents": current_user.total_documents,
        "created_at": current_user.created_at,
    }


@router.post("/logout")
async def logout(current_user: User = Depends(require_auth)):
    return {"message": "Logged out successfully"}
