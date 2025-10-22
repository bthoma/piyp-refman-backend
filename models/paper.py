"""
Paper data models for PiyP Reference Manager API.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# Paper models
class Paper(BaseModel):
    """Basic paper model"""
    paper_id: str
    title: str
    authors: List[str] = []
    year: Optional[int] = None
    venue: Optional[str] = None
    abstract: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    citation_count: int = 0
    pdf_available: bool = False
    status: Optional[str] = None  # to_read, reading, read
    starred: bool = False
    rating: Optional[int] = None
    tags: List[str] = []
    collections: List[str] = []
    date_added: Optional[datetime] = None
    notes_count: int = 0


class PaperDetail(Paper):
    """Extended paper model with full details"""
    full_text: Optional[str] = None
    figures: List[Dict[str, Any]] = []
    tables: List[Dict[str, Any]] = []
    references: List[str] = []
    citations: List[str] = []
    related_papers: List[Paper] = []
    notes: List['Note'] = []
    ingestion_stats: Optional[Dict[str, Any]] = None


# Note models
class NoteBase(BaseModel):
    """Base note model"""
    note_type: str = Field(..., description="Type: general, methodology, results, critique, idea")
    note_text: str = Field(..., min_length=1)
    highlight_text: Optional[str] = None
    page_number: Optional[int] = None


class NoteCreate(NoteBase):
    """Note creation model"""
    user_id: str


class Note(NoteBase):
    """Complete note model"""
    id: int
    paper_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime


class NoteResponse(BaseModel):
    """Note API response"""
    success: bool
    note: Optional[Note] = None
    error: Optional[str] = None


# Response models
class PaperListResponse(BaseModel):
    """Paper list API response"""
    papers: List[Paper]
    total: int
    page: int
    pages: int


class PaperDetailResponse(BaseModel):
    """Paper detail API response"""
    paper: PaperDetail


class UploadResponse(BaseModel):
    """Paper upload API response"""
    success: bool
    paper_id: Optional[str] = None
    filename: Optional[str] = None
    file_size: Optional[int] = None
    status: Optional[str] = None
    ingestion_task_id: Optional[str] = None
    extracted_metadata: Optional[Dict[str, Any]] = None  # NEW: Extracted PDF metadata
    error: Optional[str] = None


# Update forward reference
Note.model_rebuild()