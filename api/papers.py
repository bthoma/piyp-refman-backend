"""
Papers API Router.

Handles paper management, metadata, upload, and CRUD operations.
"""

from fastapi import APIRouter, Query, Form, File, UploadFile, HTTPException, Depends
from fastapi.responses import FileResponse, StreamingResponse
from typing import List, Optional
from datetime import datetime
import base64
import logging
import os

from models.paper import PaperListResponse, PaperDetailResponse, UploadResponse, NoteCreate, NoteResponse
from services.agent_client import AgentClient
from services.pdf_service import PDFService
from config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Dependencies
def get_agent_client():
    """Get agent client dependency"""
    return AgentClient()

def get_pdf_service():
    """Get PDF service dependency"""
    return PDFService()

settings = get_settings()


@router.get("/papers", response_model=PaperListResponse)
async def list_papers(
    user_id: str = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, le=100),
    
    # Traditional filters
    author: Optional[str] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    venue: Optional[str] = None,
    title_contains: Optional[str] = None,
    tags: Optional[List[str]] = Query(None),
    collection_id: Optional[int] = None,
    status: Optional[str] = None,  # to_read, reading, read
    starred: Optional[bool] = None,
    
    # Sort options
    sort_by: str = Query("date_added", regex="^(date_added|date_published|citations|title|author)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    
    agent_client: AgentClient = Depends(get_agent_client)
):
    """
    List papers with comprehensive filtering and sorting.
    
    This endpoint provides traditional SQL-style filtering and sorting
    for the paper library. For semantic search, use the /search endpoint.
    """
    try:
        # Build filters
        filters = {}
        
        if author:
            filters["author"] = author
        if year_min:
            filters["year_min"] = year_min
        if year_max:
            filters["year_max"] = year_max
        if venue:
            filters["venue"] = venue
        if title_contains:
            filters["title_contains"] = title_contains
        if tags:
            filters["tags"] = tags
        if collection_id:
            filters["collection_id"] = collection_id
        if status:
            filters["status"] = status
        if starred is not None:
            filters["starred"] = starred
        
        # Use traditional search mode for listing
        result = await agent_client.search_papers(
            query="",  # Empty query for listing
            mode="traditional",
            user_id=user_id,
            filters=filters,
            sort=f"{sort_by}_{sort_order}",
            limit=limit,
            offset=skip
        )
        
        if not result.get("success", True):
            raise HTTPException(status_code=500, detail=result.get("error", "Search failed"))
        
        papers = result.get("papers", [])
        total = result.get("total", 0)
        
        return PaperListResponse(
            papers=papers,
            total=total,
            page=skip // limit,
            pages=(total + limit - 1) // limit if total > 0 else 0
        )
        
    except Exception as e:
        logger.error(f"List papers failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/papers/{paper_id}", response_model=PaperDetailResponse)
async def get_paper(
    paper_id: str,
    user_id: str = Query(...),
    agent_client: AgentClient = Depends(get_agent_client)
):
    """
    Get complete paper details including notes, citations, related papers.
    """
    try:
        # Get paper details from agent
        paper = await agent_client.get_paper_details(paper_id, user_id)
        
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")
        
        return PaperDetailResponse(**paper)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get paper failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/papers/upload", response_model=UploadResponse)
async def upload_paper(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    title: Optional[str] = Form(None),
    authors: Optional[str] = Form(None),  # JSON array
    year: Optional[int] = Form(None),
    auto_ingest: bool = Form(True),
    
    agent_client: AgentClient = Depends(get_agent_client)
):
    """
    Upload PDF and optionally trigger ingestion.
    
    Workflow:
    1. Validate PDF
    2. Extract metadata if not provided
    3. Upload to storage (upload_paper tool)
    4. If auto_ingest, trigger ingestion
    5. Return paper_id and status
    """
    try:
        # Validate file
        if file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        if file.size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400, 
                detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE / (1024*1024):.1f}MB"
            )
        
        # Read file data
        file_data = await file.read()
        
        # Generate paper ID
        paper_id = f"paper_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{len(file_data)}"
        
        # Parse authors if provided
        author_list = []
        if authors:
            try:
                import json
                author_list = json.loads(authors)
            except:
                # Fallback: split by comma
                author_list = [a.strip() for a in authors.split(",")]
        
        # Build metadata
        metadata = {}
        if title:
            metadata["title"] = title
        if author_list:
            metadata["authors"] = author_list
        if year:
            metadata["year"] = year
        
        # Upload paper via agent
        upload_result = await agent_client.upload_paper(
            file_data=base64.b64encode(file_data).decode(),
            paper_id=paper_id,
            user_id=user_id,
            filename=file.filename,
            metadata=metadata
        )
        
        if not upload_result.get("success"):
            raise HTTPException(status_code=500, detail=upload_result.get("error", "Upload failed"))
        
        # Trigger ingestion if requested
        ingestion_task_id = None
        if auto_ingest:
            try:
                ingestion_result = await agent_client.trigger_ingestion(
                    paper_id=paper_id,
                    pdf_path=upload_result.get("pdf_path"),
                    user_id=user_id,
                    metadata=metadata
                )
                ingestion_task_id = ingestion_result.get("task_id")
            except Exception as e:
                logger.warning(f"Auto-ingestion failed for {paper_id}: {str(e)}")
        
        return UploadResponse(
            success=True,
            paper_id=paper_id,
            filename=file.filename,
            file_size=len(file_data),
            status="uploaded" if not auto_ingest else "ingesting",
            ingestion_task_id=ingestion_task_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/papers/{paper_id}")
async def delete_paper(
    paper_id: str,
    user_id: str = Query(...),
    agent_client: AgentClient = Depends(get_agent_client)
):
    """Delete paper from library"""
    try:
        result = await agent_client.delete_paper(paper_id, user_id)
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Delete failed"))
        
        return {"success": True, "message": "Paper deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete paper failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/papers/{paper_id}/pdf")
async def download_pdf(
    paper_id: str,
    user_id: str = Query(...),
    pdf_service: PDFService = Depends(get_pdf_service)
):
    """Stream PDF file for viewing/download"""
    try:
        # Get PDF path
        pdf_path = await pdf_service.get_pdf_path(paper_id, user_id)
        
        if not pdf_path or not os.path.exists(pdf_path):
            raise HTTPException(status_code=404, detail="PDF not found")
        
        # Stream file
        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename=f"{paper_id}.pdf"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF download failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/papers/{paper_id}/notes", response_model=NoteResponse)
async def add_note(
    paper_id: str,
    note: NoteCreate,
    agent_client: AgentClient = Depends(get_agent_client)
):
    """Add annotation/note to paper"""
    try:
        result = await agent_client.add_paper_note(
            paper_id=paper_id,
            user_id=note.user_id,
            note_type=note.note_type,
            note_text=note.note_text,
            highlight_text=note.highlight_text,
            page_number=note.page_number
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to add note"))
        
        return NoteResponse(**result.get("note", {}))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Add note failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/papers/{paper_id}/status")
async def update_status(
    paper_id: str,
    status: str,
    user_id: str = Query(...),
    starred: Optional[bool] = None,
    rating: Optional[int] = None,
    agent_client: AgentClient = Depends(get_agent_client)
):
    """Update paper reading status"""
    try:
        # Validate status
        valid_statuses = ["to_read", "reading", "read", "skimmed", "abandoned"]
        if status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
        
        # Validate rating
        if rating is not None and (rating < 1 or rating > 5):
            raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
        
        result = await agent_client.update_paper_status(
            paper_id=paper_id,
            user_id=user_id,
            status=status,
            starred=starred,
            rating=rating
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Status update failed"))
        
        return {"success": True, "status": status, "starred": starred, "rating": rating}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update status failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/papers/batch-action")
async def batch_action(
    action: str,
    paper_ids: List[str],
    user_id: str = Query(...),
    # Action-specific parameters
    status: Optional[str] = None,
    starred: Optional[bool] = None,
    collection_id: Optional[int] = None,
    tags: Optional[List[str]] = None,
    
    agent_client: AgentClient = Depends(get_agent_client)
):
    """Perform batch actions on multiple papers"""
    try:
        valid_actions = ["update_status", "add_to_collection", "add_tags", "delete"]
        if action not in valid_actions:
            raise HTTPException(status_code=400, detail=f"Invalid action. Must be one of: {valid_actions}")
        
        results = []
        
        for paper_id in paper_ids:
            try:
                if action == "update_status":
                    result = await agent_client.update_paper_status(
                        paper_id=paper_id,
                        user_id=user_id,
                        status=status,
                        starred=starred
                    )
                
                elif action == "add_to_collection":
                    result = await agent_client.add_to_collection(
                        paper_id=paper_id,
                        user_id=user_id,
                        collection_id=collection_id
                    )
                
                elif action == "add_tags":
                    result = await agent_client.add_paper_tags(
                        paper_id=paper_id,
                        user_id=user_id,
                        tags=tags
                    )
                
                elif action == "delete":
                    result = await agent_client.delete_paper(paper_id, user_id)
                
                results.append({
                    "paper_id": paper_id,
                    "success": result.get("success", False),
                    "error": result.get("error")
                })
                
            except Exception as e:
                results.append({
                    "paper_id": paper_id,
                    "success": False,
                    "error": str(e)
                })
        
        successful = sum(1 for r in results if r["success"])
        
        return {
            "action": action,
            "total": len(paper_ids),
            "successful": successful,
            "failed": len(paper_ids) - successful,
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch action failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))