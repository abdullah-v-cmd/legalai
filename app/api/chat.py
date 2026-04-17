"""Chat API routes - Legal Q&A, Image analysis"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from typing import Optional, List
from app.core.database import get_db
from app.services.ai_service import legal_ai
from app.models.chat import ChatSession, ChatMessage
from app.models.user import User
from app.middleware.auth_middleware import get_current_user
import uuid
import logging

router = APIRouter(prefix="/api/chat", tags=["Chat"])
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    context: Optional[str] = ""


class ChatResponse(BaseModel):
    session_id: str
    message: str
    role: str = "assistant"


async def get_or_create_session(
    db: AsyncSession, session_id: Optional[str], user: Optional[User]
) -> ChatSession:
    """Get existing or create new session"""
    if session_id:
        result = await db.execute(
            select(ChatSession).where(ChatSession.session_id == session_id)
        )
        session = result.scalar_one_or_none()
        if session:
            return session
    
    # Only save session for logged-in users
    if user:
        new_session = ChatSession(
            session_id=str(uuid.uuid4()),
            user_id=user.id,
            chat_type="legal_qa",
        )
        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)
        return new_session
    else:
        # Anonymous - return temporary session (not saved)
        return ChatSession(
            session_id=str(uuid.uuid4()),
            user_id=None,
            chat_type="legal_qa",
        )


@router.post("/message")
async def chat_message(
    data: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Send a message and get AI response"""
    session = await get_or_create_session(db, data.session_id, current_user)
    
    # Get AI response
    response = await legal_ai.answer_legal_question(data.message, data.context or "")
    
    # Save messages only for authenticated users
    if current_user and session.id:
        user_msg = ChatMessage(
            session_id=session.id,
            role="user",
            content=data.message,
            message_type="text"
        )
        ai_msg = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=response,
            message_type="text",
            metadata_={"model": "mistralai/Mistral-7B-Instruct-v0.2"}
        )
        db.add(user_msg)
        db.add(ai_msg)
        
        # Update user stats
        current_user.total_queries = (current_user.total_queries or 0) + 1
        await db.commit()
    
    return {
        "session_id": session.session_id,
        "message": response,
        "role": "assistant",
        "authenticated": current_user is not None,
    }


@router.post("/image")
async def analyze_image(
    question: str = Form(default="What legal information can you extract from this image?"),
    session_id: Optional[str] = Form(default=None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Analyze an image and answer questions about it"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Login required to upload images")
    
    # Validate file type
    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only image files are allowed")
    
    # Read image
    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="Image too large. Max 10MB")
    
    # Analyze
    response = await legal_ai.analyze_image(image_bytes, question)
    
    session = await get_or_create_session(db, session_id, current_user)
    
    if session.id:
        db.add(ChatMessage(session_id=session.id, role="user", content=question, message_type="image"))
        db.add(ChatMessage(session_id=session.id, role="assistant", content=response, message_type="text"))
        current_user.total_queries = (current_user.total_queries or 0) + 1
        await db.commit()
    
    return {"session_id": session.session_id, "message": response, "role": "assistant"}


@router.get("/history")
async def get_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get chat history for authenticated user"""
    if not current_user:
        return {"sessions": [], "message": "Login to save chat history"}
    
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .order_by(desc(ChatSession.updated_at))
        .limit(20)
    )
    sessions = result.scalars().all()
    
    return {
        "sessions": [
            {
                "id": s.id,
                "session_id": s.session_id,
                "title": s.title,
                "chat_type": s.chat_type,
                "created_at": s.created_at,
                "updated_at": s.updated_at,
            }
            for s in sessions
        ]
    }


@router.get("/session/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get messages for a specific session"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.session_id == session_id,
            ChatSession.user_id == current_user.id
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    msgs_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at)
    )
    messages = msgs_result.scalars().all()
    
    return {
        "session_id": session_id,
        "messages": [
            {"role": m.role, "content": m.content, "type": m.message_type, "created_at": m.created_at}
            for m in messages
        ]
    }


@router.delete("/session/{session_id}")
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a chat session"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.session_id == session_id,
            ChatSession.user_id == current_user.id
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    await db.delete(session)
    await db.commit()
    return {"message": "Session deleted"}
