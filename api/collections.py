"""
Collections API Router.

Handles paper collection management and organization.
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import List, Optional
import logging
from datetime import datetime

from models.paper import PaperListResponse
from services.agent_client import AgentClient

logger = logging.getLogger(__name__)
router = APIRouter()


def get_agent_client():
    """Get agent client dependency"""
    return AgentClient()


@router.get("/")
async def list_collections(
    user_id: str = Query(...),
    agent_client: AgentClient = Depends(get_agent_client)
):
    """List user's collections"""
    try:
        # TODO: Implement via agents
        # For now return empty collections
        return {
            "collections": []
        }
        
    except Exception as e:
        logger.error(f"List collections failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def create_collection(
    name: str,
    user_id: str = Query(...),
    description: Optional[str] = None,
    agent_client: AgentClient = Depends(get_agent_client)
):
    """Create new collection"""
    try:
        # TODO: Implement via agents
        # For now return mock collection
        return {
            "success": True,
            "collection": {
                "id": 1,
                "name": name,
                "description": description,
                "user_id": user_id,
                "paper_count": 0,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Create collection failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{collection_id}/papers", response_model=PaperListResponse)
async def get_collection_papers(
    collection_id: int,
    user_id: str = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, le=100),
    agent_client: AgentClient = Depends(get_agent_client)
):
    """Get papers in collection"""
    try:
        # TODO: Implement via agents
        # For now return empty papers
        return PaperListResponse(
            papers=[],
            total=0,
            page=skip // limit,
            pages=0
        )
        
    except Exception as e:
        logger.error(f"Get collection papers failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{collection_id}/papers/{paper_id}")
async def add_paper_to_collection(
    collection_id: int,
    paper_id: str,
    user_id: str = Query(...),
    agent_client: AgentClient = Depends(get_agent_client)
):
    """Add paper to collection"""
    try:
        # TODO: Implement via agents
        return {"success": True, "message": "Paper added to collection"}
        
    except Exception as e:
        logger.error(f"Add paper to collection failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{collection_id}/papers/{paper_id}")
async def remove_paper_from_collection(
    collection_id: int,
    paper_id: str,
    user_id: str = Query(...),
    agent_client: AgentClient = Depends(get_agent_client)
):
    """Remove paper from collection"""
    try:
        # TODO: Implement via agents
        return {"success": True, "message": "Paper removed from collection"}
        
    except Exception as e:
        logger.error(f"Remove paper from collection failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))