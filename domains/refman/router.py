"""
RefMan Domain Router - Reference Manager endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
import hashlib

from config.database import get_client
from config.settings import settings
from domains.core.auth import decode_token
from .schemas import PaperCreate, PaperResponse, CollectionCreate, CollectionResponse

router = APIRouter()
security = HTTPBearer()


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Get current user ID from token"""
    token = credentials.credentials
    payload = decode_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )
    
    return payload.get("sub")


@router.get("/papers", response_model=List[PaperResponse])
async def get_papers(
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    collection_id: Optional[str] = None,
    user_id: str = Depends(get_current_user_id)
):
    """Get user's papers with optional filtering"""
    client = get_client()
    
    query = client.table('refman.papers').select('*').eq('user_id', user_id)
    
    if search:
        query = query.text_search('search_vector', search)
    
    if collection_id:
        # Join with paper_collections
        query = query.filter('id', 'in', 
            client.table('refman.paper_collections')
                .select('paper_id')
                .eq('collection_id', collection_id)
                .execute().data
        )
    
    papers = query.range(skip, skip + limit - 1).order('created_at', desc=True).execute()
    
    return [PaperResponse(**paper) for paper in papers.data]


@router.post("/papers", response_model=PaperResponse)
async def create_paper(
    paper: PaperCreate,
    user_id: str = Depends(get_current_user_id)
):
    """Create a new paper entry"""
    client = get_client()
    
    paper_data = paper.dict(exclude_unset=True)
    paper_data['user_id'] = user_id
    
    result = client.table('refman.papers').insert(paper_data).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create paper"
        )
    
    return PaperResponse(**result.data[0])


@router.get("/papers/{paper_id}", response_model=PaperResponse)
async def get_paper(
    paper_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get a specific paper"""
    client = get_client()
    
    paper = client.table('refman.papers').select('*').eq('id', paper_id).eq('user_id', user_id).execute()
    
    if not paper.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found"
        )
    
    return PaperResponse(**paper.data[0])


@router.post("/papers/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    paper_id: Optional[str] = None,
    user_id: str = Depends(get_current_user_id)
):
    """Upload a PDF file and optionally attach to a paper"""
    if file.content_type != 'application/pdf':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )
    
    # Check file size
    if file.size > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {settings.max_upload_size_mb}MB"
        )
    
    # Calculate file hash
    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()
    
    # TODO: Save file to storage and extract metadata
    # TODO: Create paper entry if paper_id not provided
    
    return {
        "message": "PDF upload functionality coming soon",
        "file_hash": file_hash,
        "filename": file.filename
    }


@router.get("/collections", response_model=List[CollectionResponse])
async def get_collections(
    user_id: str = Depends(get_current_user_id)
):
    """Get user's collections"""
    client = get_client()
    
    collections = client.table('refman.collections').select('*').eq('user_id', user_id).execute()
    
    return [CollectionResponse(**col) for col in collections.data]


@router.post("/collections", response_model=CollectionResponse)
async def create_collection(
    collection: CollectionCreate,
    user_id: str = Depends(get_current_user_id)
):
    """Create a new collection"""
    client = get_client()
    
    collection_data = collection.dict(exclude_unset=True)
    collection_data['user_id'] = user_id
    
    result = client.table('refman.collections').insert(collection_data).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create collection"
        )
    
    return CollectionResponse(**result.data[0])


@router.post("/collections/{collection_id}/papers/{paper_id}")
async def add_paper_to_collection(
    collection_id: str,
    paper_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Add a paper to a collection"""
    client = get_client()
    
    # Verify ownership of both paper and collection
    paper = client.table('refman.papers').select('id').eq('id', paper_id).eq('user_id', user_id).execute()
    collection = client.table('refman.collections').select('id').eq('id', collection_id).eq('user_id', user_id).execute()
    
    if not paper.data or not collection.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper or collection not found"
        )
    
    # Add to junction table
    result = client.table('refman.paper_collections').insert({
        'paper_id': paper_id,
        'collection_id': collection_id
    }).execute()
    
    return {"message": "Paper added to collection successfully"}