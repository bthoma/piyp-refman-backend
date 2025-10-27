"""
RefMan Domain Schemas - Pydantic models for validation
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from uuid import UUID


class AuthorSchema(BaseModel):
    """Author information"""
    name: str
    affiliation: Optional[str] = None
    orcid: Optional[str] = None


class PaperBase(BaseModel):
    """Base paper schema"""
    title: str
    abstract: Optional[str] = None
    authors: List[AuthorSchema] = []
    publication_date: Optional[date] = None
    publication_year: Optional[int] = None
    journal: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    publisher: Optional[str] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    pmcid: Optional[str] = None
    arxiv_id: Optional[str] = None
    isbn: Optional[str] = None
    url: Optional[str] = None
    paper_type: str = "article"
    tags: List[str] = []
    notes: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
    read_status: str = "unread"
    importance: str = "normal"


class PaperCreate(PaperBase):
    """Schema for creating a paper"""
    pass


class PaperUpdate(BaseModel):
    """Schema for updating a paper"""
    title: Optional[str] = None
    abstract: Optional[str] = None
    authors: Optional[List[AuthorSchema]] = None
    publication_date: Optional[date] = None
    publication_year: Optional[int] = None
    journal: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    publisher: Optional[str] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    pmcid: Optional[str] = None
    arxiv_id: Optional[str] = None
    isbn: Optional[str] = None
    url: Optional[str] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
    read_status: Optional[str] = None
    importance: Optional[str] = None


class PaperResponse(PaperBase):
    """Paper response schema"""
    id: UUID
    user_id: UUID
    pdf_stored: bool = False
    pdf_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_accessed: Optional[datetime] = None
    summary: Optional[str] = None
    key_concepts: List[str] = []
    
    class Config:
        from_attributes = True


class CollectionBase(BaseModel):
    """Base collection schema"""
    name: str
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    parent_id: Optional[UUID] = None
    is_smart: bool = False
    smart_rules: Optional[Dict[str, Any]] = None


class CollectionCreate(CollectionBase):
    """Schema for creating a collection"""
    pass


class CollectionUpdate(BaseModel):
    """Schema for updating a collection"""
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    parent_id: Optional[UUID] = None
    smart_rules: Optional[Dict[str, Any]] = None


class CollectionResponse(CollectionBase):
    """Collection response schema"""
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AnnotationBase(BaseModel):
    """Base annotation schema"""
    page_number: Optional[int] = None
    position: Optional[Dict[str, float]] = None  # {x, y, width, height}
    selected_text: Optional[str] = None
    annotation_type: str  # highlight, note, underline
    color: Optional[str] = None
    content: Optional[str] = None


class AnnotationCreate(AnnotationBase):
    """Schema for creating an annotation"""
    paper_id: UUID


class AnnotationResponse(AnnotationBase):
    """Annotation response schema"""
    id: UUID
    paper_id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CitationFormats(BaseModel):
    """Citation formats response"""
    bibtex: Optional[str] = None
    ris: Optional[str] = None
    endnote: Optional[str] = None
    apa: Optional[str] = None
    mla: Optional[str] = None
    chicago: Optional[str] = None


class ImportRequest(BaseModel):
    """Import request schema"""
    source: str  # mendeley, zotero, bibtex, etc.
    file_content: Optional[str] = None  # Base64 encoded file
    url: Optional[str] = None  # URL to import from


class ImportResponse(BaseModel):
    """Import response schema"""
    id: UUID
    total_items: int
    imported_items: int
    failed_items: int
    status: str
    details: Optional[Dict[str, Any]] = None