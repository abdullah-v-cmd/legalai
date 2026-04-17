"""Document generation API routes"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.services.ai_service import legal_ai
from app.services.document_service import word_service, ppt_service
from app.models.document import Document
from app.models.user import User
from app.middleware.auth_middleware import require_auth, get_current_user
import os
import logging

router = APIRouter(prefix="/api/documents", tags=["Documents"])
logger = logging.getLogger(__name__)


class LegalPaperRequest(BaseModel):
    subject: str
    case_details: str = ""
    paper_type: str = "case_study"  # case_study, research, brief, memo


class AssignmentRequest(BaseModel):
    topic: str
    sample_text: str = ""
    word_count: int = 1000
    subject: str = ""
    author_name: str = "Student"


class TestPaperRequest(BaseModel):
    subject: str
    num_questions: int = 10
    difficulty: str = "medium"
    test_type: str = "mcq"  # mcq, subjective, mixed


class PPTRequest(BaseModel):
    topic: str
    duration_minutes: int = 15
    slide_count: Optional[int] = None
    theme: str = "legal_blue"


@router.post("/legal-paper")
async def generate_legal_paper(
    data: LegalPaperRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Generate a legal paper/document"""
    content = await legal_ai.generate_legal_paper(
        data.subject, data.case_details, data.paper_type
    )
    
    # Create Word doc
    author = current_user.full_name or current_user.username if current_user else "LegalAI User"
    filepath = word_service.create_legal_paper(
        title=data.subject,
        content=content,
        author=author
    )
    
    # Save record if authenticated
    if current_user:
        doc = Document(
            user_id=current_user.id,
            title=data.subject,
            doc_type="legal_paper",
            file_path=filepath,
            file_size=os.path.getsize(filepath) if os.path.exists(filepath) else 0,
            word_count=len(content.split()),
            prompt=data.case_details,
            subject=data.subject,
            status="completed",
        )
        db.add(doc)
        current_user.total_documents = (current_user.total_documents or 0) + 1
        await db.commit()
        await db.refresh(doc)
        doc_id = doc.id
    else:
        doc_id = None
    
    return {
        "content": content,
        "doc_id": doc_id,
        "download_url": f"/api/documents/download/{os.path.basename(filepath)}",
        "filename": os.path.basename(filepath),
        "word_count": len(content.split()),
    }


@router.post("/assignment")
async def generate_assignment(
    data: AssignmentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Generate a complete assignment"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Login required to generate documents")
    
    content = await legal_ai.generate_assignment(
        data.topic, data.sample_text, data.word_count
    )
    
    filepath = word_service.create_assignment(
        title=data.topic,
        content=content,
        subject=data.subject or data.topic,
        word_count=data.word_count,
        author=data.author_name or current_user.full_name or current_user.username,
    )
    
    doc = Document(
        user_id=current_user.id,
        title=data.topic,
        doc_type="assignment",
        file_path=filepath,
        file_size=os.path.getsize(filepath) if os.path.exists(filepath) else 0,
        word_count=len(content.split()),
        prompt=data.sample_text,
        subject=data.subject,
        status="completed",
        humanized=True,
        plagiarism_checked=True,
    )
    db.add(doc)
    current_user.total_documents = (current_user.total_documents or 0) + 1
    await db.commit()
    
    return {
        "content": content,
        "doc_id": doc.id,
        "download_url": f"/api/documents/download/{os.path.basename(filepath)}",
        "filename": os.path.basename(filepath),
        "word_count": len(content.split()),
        "humanized": True,
        "ai_free": True,
    }


@router.post("/test-paper")
async def generate_test_paper(
    data: TestPaperRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Generate a test/exam paper"""
    content = await legal_ai.generate_test_paper(
        data.subject, data.num_questions, data.difficulty, data.test_type
    )
    
    filepath = word_service.create_test_paper(
        title=data.subject,
        content=content,
        subject=data.subject
    )
    
    if current_user:
        doc = Document(
            user_id=current_user.id,
            title=f"Test: {data.subject}",
            doc_type="test",
            file_path=filepath,
            file_size=os.path.getsize(filepath) if os.path.exists(filepath) else 0,
            word_count=len(content.split()),
            subject=data.subject,
            status="completed",
        )
        db.add(doc)
        current_user.total_documents = (current_user.total_documents or 0) + 1
        await db.commit()
    
    return {
        "content": content,
        "download_url": f"/api/documents/download/{os.path.basename(filepath)}",
        "filename": os.path.basename(filepath),
    }


@router.post("/presentation")
async def generate_presentation(
    data: PPTRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Generate a PowerPoint presentation with script"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Login required to generate presentations")
    
    # Generate content
    ppt_data = await legal_ai.generate_ppt_content(
        data.topic, data.duration_minutes, data.slide_count
    )
    
    # Create PPT file
    filepath = ppt_service.create_presentation(ppt_data, data.theme)
    
    doc = Document(
        user_id=current_user.id,
        title=f"PPT: {data.topic}",
        doc_type="ppt",
        file_path=filepath,
        file_size=os.path.getsize(filepath) if os.path.exists(filepath) else 0,
        subject=data.topic,
        status="completed",
    )
    db.add(doc)
    current_user.total_documents = (current_user.total_documents or 0) + 1
    await db.commit()
    
    return {
        "ppt_data": ppt_data,
        "download_url": f"/api/documents/download/{os.path.basename(filepath)}",
        "filename": os.path.basename(filepath),
        "script": ppt_data.get("full_script", ""),
        "slide_count": ppt_data.get("slide_count", 0),
    }


@router.get("/download/{filename}")
async def download_document(filename: str):
    """Download a generated document"""
    # Security: prevent path traversal
    safe_filename = os.path.basename(filename)
    filepath = os.path.join("./exports", safe_filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        filepath,
        filename=safe_filename,
        media_type="application/octet-stream"
    )


@router.get("/my-documents")
async def get_my_documents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Get all documents for current user"""
    result = await db.execute(
        select(Document)
        .where(Document.user_id == current_user.id)
        .order_by(desc(Document.created_at))
    )
    docs = result.scalars().all()
    
    return {
        "documents": [
            {
                "id": d.id,
                "title": d.title,
                "type": d.doc_type,
                "word_count": d.word_count,
                "humanized": d.humanized,
                "status": d.status,
                "download_url": f"/api/documents/download/{os.path.basename(d.file_path)}" if d.file_path else None,
                "created_at": d.created_at,
            }
            for d in docs
        ]
    }
