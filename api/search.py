"""
Search API Router.

Handles multi-modal search: Traditional SQL, RAG semantic, Knowledge Graph traversal.
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import List, Optional, Dict, Any
import logging

from models.paper import PaperListResponse
from services.agent_client import AgentClient
from config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


def get_agent_client():
    """Get agent client dependency"""
    return AgentClient()


@router.post("/", response_model=PaperListResponse)
async def search_papers(
    query: str,
    mode: str = Query(..., regex="^(traditional|rag|kg)$"),
    user_id: str = Query(...),
    filters: Optional[Dict[str, Any]] = None,
    sort: Optional[str] = None,
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    
    agent_client: AgentClient = Depends(get_agent_client)
):
    """
    Multi-modal paper search.
    
    Supports three search modes:
    - traditional: SQL-based filtering and sorting
    - rag: Semantic similarity search using embeddings  
    - kg: Knowledge graph concept traversal
    """
    try:
        # Use agent client for search
        result = await agent_client.search_papers(
            query=query,
            mode=mode,
            user_id=user_id,
            filters=filters or {},
            sort=sort,
            limit=limit,
            offset=offset
        )
        
        if not result.get("success", True):
            raise HTTPException(status_code=500, detail=result.get("error", "Search failed"))
        
        papers = result.get("papers", [])
        total = result.get("total", 0)
        
        return PaperListResponse(
            papers=papers,
            total=total,
            page=offset // limit,
            pages=(total + limit - 1) // limit if total > 0 else 0
        )
        
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggestions")
async def get_search_suggestions(
    query: str = Query(..., min_length=2),
    user_id: str = Query(...),
    limit: int = Query(5, le=20),
    
    agent_client: AgentClient = Depends(get_agent_client)
):
    """Get search query suggestions"""
    try:
        # TODO: Implement search suggestions via agents
        # For now return empty suggestions
        return {
            "suggestions": [],
            "query": query
        }
        
    except Exception as e:
        logger.error(f"Search suggestions failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_search_history(
    user_id: str = Query(...),
    limit: int = Query(10, le=50),
    
    agent_client: AgentClient = Depends(get_agent_client)
):
    """Get user search history"""
    try:
        # TODO: Implement search history via agents
        # For now return empty history
        return {
            "history": [],
            "total": 0
        }
        
    except Exception as e:
        logger.error(f"Search history failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))