"""Document model for generated files"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    title = Column(String(300), nullable=False)
    doc_type = Column(String(50), nullable=False)  # word, ppt, assignment, legal_paper, test
    file_path = Column(String(500), nullable=True)
    file_size = Column(BigInteger, default=0)
    word_count = Column(Integer, default=0)
    
    # Generation params
    prompt = Column(Text, nullable=True)
    subject = Column(String(200), nullable=True)
    additional_params = Column(Text, nullable=True)  # JSON string
    
    # Status
    status = Column(String(30), default="pending")  # pending, processing, completed, failed
    error_message = Column(Text, nullable=True)
    
    # AI flags
    humanized = Column(Boolean, default=True)
    plagiarism_checked = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="documents")
