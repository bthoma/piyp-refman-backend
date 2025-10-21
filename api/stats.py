"""
Stats API Router.

Handles user statistics and dashboard metrics.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def get_user_stats(
    user_id: str = Query(...)
):
    """Get user statistics for dashboard"""
    try:
        # TODO: Implement real stats from database
        # For now return mock stats
        stats = {
            "total_papers": 0,
            "ingested_papers": 0,
            "to_read": 0,
            "reading": 0,
            "read": 0,
            "starred": 0,
            "recent_activity": 0
        }
        
        return {"stats": stats}
        
    except Exception as e:
        logger.error(f"Get user stats failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))