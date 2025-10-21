"""
Tasks API Router.

Handles async task tracking and status monitoring.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
import logging

from services.agent_client import AgentClient

logger = logging.getLogger(__name__)
router = APIRouter()


def get_agent_client():
    """Get agent client dependency"""
    return AgentClient()


@router.get("/{task_id}")
async def get_task_status(
    task_id: str,
    agent_client: AgentClient = Depends(get_agent_client)
):
    """Get task status and progress"""
    try:
        task_status = await agent_client.get_task_status(task_id)
        
        if not task_status:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return {"task": task_status}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get task status failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    agent_client: AgentClient = Depends(get_agent_client)
):
    """Cancel a running task"""
    try:
        # TODO: Implement task cancellation via agents
        return {
            "success": True,
            "task_id": task_id,
            "status": "cancelled"
        }
        
    except Exception as e:
        logger.error(f"Cancel task failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))