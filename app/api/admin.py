"""Admin Panel API - Full system control"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, text
from typing import Optional
from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.chat import ChatSession, ChatMessage
from app.models.document import Document
from app.middleware.auth_middleware import require_admin
from pydantic import BaseModel
from datetime import datetime, timedelta
import psutil
import os
import sys

router = APIRouter(prefix="/api/admin", tags=["Admin"])


# ===== DASHBOARD =====
@router.get("/dashboard")
async def admin_dashboard(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Admin dashboard with system overview"""
    
    # User stats
    total_users = await db.execute(select(func.count(User.id)))
    total_users = total_users.scalar()
    
    active_users = await db.execute(select(func.count(User.id)).where(User.is_active == True))
    active_users = active_users.scalar()
    
    # Chat stats
    total_sessions = await db.execute(select(func.count(ChatSession.id)))
    total_sessions = total_sessions.scalar()
    
    total_messages = await db.execute(select(func.count(ChatMessage.id)))
    total_messages = total_messages.scalar()
    
    # Document stats
    total_docs = await db.execute(select(func.count(Document.id)))
    total_docs = total_docs.scalar()
    
    # System stats
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Recent users (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    new_users = await db.execute(
        select(func.count(User.id)).where(User.created_at >= week_ago)
    )
    new_users = new_users.scalar()
    
    return {
        "stats": {
            "users": {
                "total": total_users,
                "active": active_users,
                "new_this_week": new_users,
            },
            "chats": {
                "total_sessions": total_sessions,
                "total_messages": total_messages,
            },
            "documents": {
                "total": total_docs,
            },
        },
        "system": {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_used_gb": round(memory.used / (1024**3), 2),
            "memory_total_gb": round(memory.total / (1024**3), 2),
            "disk_percent": disk.percent,
            "disk_free_gb": round(disk.free / (1024**3), 2),
            "python_version": sys.version,
            "uptime": "Running",
        }
    }


# ===== USER MANAGEMENT =====
@router.get("/users")
async def list_users(
    page: int = 1,
    per_page: int = 20,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """List all users with pagination"""
    query = select(User)
    if search:
        query = query.where(
            (User.username.ilike(f"%{search}%")) | (User.email.ilike(f"%{search}%"))
        )
    
    total = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total.scalar()
    
    users = await db.execute(
        query.order_by(desc(User.created_at))
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    users = users.scalars().all()
    
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role,
                "is_active": u.is_active,
                "total_queries": u.total_queries,
                "total_documents": u.total_documents,
                "created_at": u.created_at,
                "last_login": u.last_login,
            }
            for u in users
        ]
    }


class UserUpdateRequest(BaseModel):
    is_active: Optional[bool] = None
    role: Optional[str] = None
    full_name: Optional[str] = None


@router.patch("/users/{user_id}")
async def update_user(
    user_id: int,
    data: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Update user (activate/deactivate, change role)"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.role:
        if data.role not in [r.value for r in UserRole]:
            raise HTTPException(status_code=400, detail="Invalid role")
        user.role = data.role
    if data.full_name:
        user.full_name = data.full_name
    
    await db.commit()
    return {"message": "User updated", "user_id": user_id}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Delete a user and all their data"""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own admin account")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.delete(user)
    await db.commit()
    return {"message": f"User {user_id} deleted"}


# ===== CHAT MANAGEMENT =====
@router.get("/chats")
async def list_all_chats(
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """List all chat sessions"""
    sessions = await db.execute(
        select(ChatSession)
        .order_by(desc(ChatSession.updated_at))
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    sessions = sessions.scalars().all()
    
    return {
        "sessions": [
            {
                "id": s.id,
                "session_id": s.session_id,
                "user_id": s.user_id,
                "title": s.title,
                "type": s.chat_type,
                "created_at": s.created_at,
            }
            for s in sessions
        ]
    }


# ===== DOCUMENT MANAGEMENT =====
@router.get("/documents")
async def list_all_documents(
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """List all generated documents"""
    docs = await db.execute(
        select(Document)
        .order_by(desc(Document.created_at))
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    docs = docs.scalars().all()
    
    total = await db.execute(select(func.count(Document.id)))
    total = total.scalar()
    
    return {
        "total": total,
        "documents": [
            {
                "id": d.id,
                "user_id": d.user_id,
                "title": d.title,
                "type": d.doc_type,
                "status": d.status,
                "word_count": d.word_count,
                "created_at": d.created_at,
            }
            for d in docs
        ]
    }


# ===== SYSTEM MONITORING =====
@router.get("/monitoring")
async def system_monitoring(admin: User = Depends(require_admin)):
    """Real-time system monitoring"""
    cpu_times = psutil.cpu_times()
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Process info
    process = psutil.Process(os.getpid())
    proc_memory = process.memory_info()
    
    return {
        "cpu": {
            "percent": psutil.cpu_percent(interval=0.5),
            "count": psutil.cpu_count(),
            "user_time": cpu_times.user,
            "system_time": cpu_times.system,
        },
        "memory": {
            "total_mb": round(memory.total / 1024**2, 2),
            "available_mb": round(memory.available / 1024**2, 2),
            "used_mb": round(memory.used / 1024**2, 2),
            "percent": memory.percent,
        },
        "disk": {
            "total_gb": round(disk.total / 1024**3, 2),
            "used_gb": round(disk.used / 1024**3, 2),
            "free_gb": round(disk.free / 1024**3, 2),
            "percent": disk.percent,
        },
        "process": {
            "pid": os.getpid(),
            "memory_mb": round(proc_memory.rss / 1024**2, 2),
            "cpu_percent": process.cpu_percent(),
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


# ===== DATABASE MANAGEMENT =====
@router.get("/database/stats")
async def database_stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Database statistics"""
    users_count = await db.execute(select(func.count(User.id)))
    sessions_count = await db.execute(select(func.count(ChatSession.id)))
    messages_count = await db.execute(select(func.count(ChatMessage.id)))
    docs_count = await db.execute(select(func.count(Document.id)))
    
    # DB file size
    db_path = "./legalai.db"
    db_size = os.path.getsize(db_path) if os.path.exists(db_path) else 0
    
    return {
        "tables": {
            "users": users_count.scalar(),
            "chat_sessions": sessions_count.scalar(),
            "chat_messages": messages_count.scalar(),
            "documents": docs_count.scalar(),
        },
        "database": {
            "type": "SQLite",
            "path": db_path,
            "size_mb": round(db_size / 1024**2, 4),
        }
    }


@router.post("/database/backup")
async def backup_database(admin: User = Depends(require_admin)):
    """Create database backup"""
    import shutil
    backup_name = f"legalai_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    backup_path = f"./backups/{backup_name}"
    os.makedirs("./backups", exist_ok=True)
    
    if os.path.exists("./legalai.db"):
        shutil.copy2("./legalai.db", backup_path)
        size = os.path.getsize(backup_path)
        return {
            "message": "Backup created",
            "backup_file": backup_name,
            "size_bytes": size,
            "created_at": datetime.utcnow().isoformat(),
        }
    raise HTTPException(status_code=500, detail="Database file not found")


@router.get("/database/backups")
async def list_backups(admin: User = Depends(require_admin)):
    """List all database backups"""
    backup_dir = "./backups"
    os.makedirs(backup_dir, exist_ok=True)
    
    backups = []
    for filename in os.listdir(backup_dir):
        if filename.endswith(".db"):
            filepath = os.path.join(backup_dir, filename)
            backups.append({
                "filename": filename,
                "size_mb": round(os.path.getsize(filepath) / 1024**2, 4),
                "created_at": datetime.fromtimestamp(os.path.getctime(filepath)).isoformat()
            })
    
    return {"backups": sorted(backups, key=lambda x: x["created_at"], reverse=True)}


# ===== ANALYTICS =====
@router.get("/analytics")
async def get_analytics(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Usage analytics"""
    since = datetime.utcnow() - timedelta(days=days)
    
    new_users = await db.execute(
        select(func.count(User.id)).where(User.created_at >= since)
    )
    
    new_messages = await db.execute(
        select(func.count(ChatMessage.id)).where(ChatMessage.created_at >= since)
    )
    
    new_docs = await db.execute(
        select(func.count(Document.id)).where(Document.created_at >= since)
    )
    
    doc_types = await db.execute(
        select(Document.doc_type, func.count(Document.id))
        .group_by(Document.doc_type)
    )
    doc_types = dict(doc_types.fetchall())
    
    return {
        "period_days": days,
        "new_users": new_users.scalar(),
        "new_messages": new_messages.scalar(),
        "new_documents": new_docs.scalar(),
        "document_types": doc_types,
    }
