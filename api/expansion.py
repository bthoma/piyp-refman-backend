"""
Expansion API Router.

Handles knowledge gap analysis and autonomous research expansion.
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import List, Optional
import logging

from services.agent_client import AgentClient

logger = logging.getLogger(__name__)
router = APIRouter()


def get_agent_client():
    """Get agent client dependency"""
    return AgentClient()


@router.get("/gaps")
async def get_knowledge_gaps(
    user_id: str = Query(...),
    topic: Optional[str] = None,
    limit: int = Query(10, le=50),
    agent_client: AgentClient = Depends(get_agent_client)
):
    """Get identified knowledge gaps"""
    try:
        result = await agent_client.analyze_gaps(user_id, topic)
        
        return {"gaps": result.get("gaps", [])}
        
    except Exception as e:
        logger.error(f"Get knowledge gaps failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/expand")
async def trigger_knowledge_expansion(
    gap_id: str,
    max_papers: int = Query(10, le=50),
    user_id: str = Query(...),
    agent_client: AgentClient = Depends(get_agent_client)
):
    """Trigger knowledge expansion for a gap"""
    try:
        # Build gap object - in real implementation this would come from database
        gap = {"id": gap_id, "topic": "Research Gap", "description": "Identified research opportunity"}
        
        result = await agent_client.trigger_knowledge_expansion(
            gap=gap,
            max_papers=max_papers,
            user_id=user_id
        )
        
        if not result.get("success", True):
            raise HTTPException(status_code=500, detail=result.get("error", "Expansion failed"))
        
        return {
            "success": True,
            "task_id": result.get("task_id"),
            "gap_id": gap_id,
            "max_papers": max_papers,
            "status": "started"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Trigger knowledge expansion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_expansion_history(
    user_id: str = Query(...),
    limit: int = Query(10, le=50),
    agent_client: AgentClient = Depends(get_agent_client)
):
    """Get expansion history"""
    try:
        history = await agent_client.get_expansion_history(user_id, limit)
        
        return {"history": history}
        
    except Exception as e:
        logger.error(f"Get expansion history failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))