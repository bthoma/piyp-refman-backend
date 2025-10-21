"""
Citations API Router.

Handles citation generation and export in multiple formats.
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import Response
from typing import List, Optional
import logging

from services.agent_client import AgentClient

logger = logging.getLogger(__name__)
router = APIRouter()


def get_agent_client():
    """Get agent client dependency"""
    return AgentClient()


@router.post("/export")
async def export_citations(
    paper_ids: List[str],
    style: str = Query(..., regex="^(apa|mla|chicago|harvard|vancouver|ieee|bibtex)$"),
    format: str = Query("text", regex="^(text|json|xml)$"),
    user_id: str = Query(...),
    
    agent_client: AgentClient = Depends(get_agent_client)
):
    """
    Export citations in specified style and format.
    
    Supported styles: APA, MLA, Chicago, Harvard, Vancouver, IEEE, BibTeX
    Supported formats: text, json, xml
    """
    try:
        result = await agent_client.export_citations(
            paper_ids=paper_ids,
            style=style,
            format=format,
            user_id=user_id
        )
        
        if not result.get("success", True):
            raise HTTPException(status_code=500, detail=result.get("error", "Citation export failed"))
        
        content = result.get("content", "")
        filename = result.get("filename", f"citations.{format}")
        
        # Determine content type
        content_type = {
            "text": "text/plain",
            "json": "application/json", 
            "xml": "application/xml"
        }.get(format, "text/plain")
        
        return Response(
            content=content,
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Citation export failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/styles")
async def get_citation_styles():
    """Get available citation styles"""
    return {
        "styles": [
            {"id": "apa", "name": "APA", "description": "American Psychological Association"},
            {"id": "mla", "name": "MLA", "description": "Modern Language Association"},
            {"id": "chicago", "name": "Chicago", "description": "Chicago Manual of Style"},
            {"id": "harvard", "name": "Harvard", "description": "Harvard Referencing System"},
            {"id": "vancouver", "name": "Vancouver", "description": "Vancouver System"},
            {"id": "ieee", "name": "IEEE", "description": "Institute of Electrical and Electronics Engineers"},
            {"id": "bibtex", "name": "BibTeX", "description": "BibTeX Format"}
        ]
    }


@router.get("/formats")
async def get_export_formats():
    """Get available export formats"""
    return {
        "formats": [
            {"id": "text", "name": "Plain Text", "extension": "txt"},
            {"id": "json", "name": "JSON", "extension": "json"},
            {"id": "xml", "name": "XML", "extension": "xml"}
        ]
    }