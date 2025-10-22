"""
Stats API Router.

Handles user statistics and dashboard metrics.
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Dict, Any
import logging
from services.agent_client import AgentClient

logger = logging.getLogger(__name__)
router = APIRouter()


def get_agent_client():
    """Get agent client dependency"""
    return AgentClient()


@router.get("/")
async def get_user_stats(
    user_id: str = Query(...),
    agent_client: AgentClient = Depends(get_agent_client)
):
    """Get user statistics for dashboard"""
    try:
        # Get real stats from database via agent client
        stats = await agent_client.get_user_stats(user_id)
        
        return {"stats": stats}
        
    except Exception as e:
        logger.error(f"Get user stats failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))