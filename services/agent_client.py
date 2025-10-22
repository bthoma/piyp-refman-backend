"""
Agent Client Service.

Handles communication with the PiyP Agent system.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
import sys
import os
from .supabase_client import SupabaseClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import agents - placeholder for now
# TODO: Integrate with actual agents when deployed
AGENT_FUNCTIONS = {}  # Placeholder


class AgentClient:
    """
    Client for communicating with PiyP agents.
    
    Provides a unified interface to all agent functions
    for the FastAPI backend.
    """
    
    def __init__(self):
        self.initialized = False
        self.supabase_client = SupabaseClient()
        
    async def initialize(self):
        """Initialize agent connections and database"""
        try:
            logger.info("Initializing agent client")
            
            # Initialize Supabase client
            await self.supabase_client.initialize()
            
            # Test agent connectivity
            await self.health_check()
            
            self.initialized = True
            logger.info("Agent client initialized successfully")
            
        except Exception as e:
            logger.error(f"Agent client initialization failed: {str(e)}")
            raise
    
    async def health_check(self) -> Dict[str, str]:
        """Check agent health status and database connectivity"""
        # Check database connectivity
        db_health = await self.supabase_client.health_check()
        
        return {
            "reference_manager_orchestrator": "healthy (mock)",
            "search_papers": "healthy (mock)",
            "analyze_gaps": "healthy (mock)",
            "pdf_retrieval": "healthy (mock)", 
            "ingestion": "healthy (mock)",
            "knowledge_gap": "healthy (mock)",
            "database": f"{'healthy' if db_health.get('connected') else 'unhealthy'}",
            "supabase_papers_count": str(db_health.get('total_papers', 0))
        }
    
    # Orchestrator methods
    async def process_paper_list(self, papers: List[dict], user_id: str, source: str = "research_domain") -> dict:
        """Process paper list from Research domain"""
        return {
            "success": True,
            "processed_count": len(papers),
            "task_id": f"process_{user_id}_{len(papers)}",
            "status": "processing"
        }
    
    async def get_session_status(self, user_id: str) -> dict:
        """Get user session status"""
        return {
            "user_id": user_id,
            "active_tasks": 0,
            "status": "idle",
            "last_activity": "2024-01-01T00:00:00Z"
        }
    
    async def cancel_operation(self, user_id: str, operation_id: str) -> dict:
        """Cancel user operation"""
        return {
            "success": True,
            "operation_id": operation_id,
            "status": "cancelled"
        }
    
    # Search methods (Library Curator)
    async def search_papers(
        self,
        query: str,
        mode: str,
        user_id: str,
        filters: Optional[dict] = None,
        sort: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> dict:
        """Search papers using database query"""
        try:
            # Use real database search
            result = await self.supabase_client.search_papers(
                user_id=user_id,
                query=query,
                filters=filters,
                sort=sort,
                limit=limit,
                offset=offset
            )
            
            # Add search mode context to result
            result["query"] = query
            result["mode"] = mode
            result["limit"] = limit
            result["offset"] = offset
            
            logger.info(f"Search completed: {len(result.get('papers', []))} papers found")
            return result
            
        except Exception as e:
            logger.error(f"Search papers failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "papers": [],
                "total": 0,
                "query": query,
                "mode": mode,
                "limit": limit,
                "offset": offset
            }
    
    async def export_citations(self, paper_ids: List[str], style: str, format: str, user_id: str) -> dict:
        """Export citations"""
        return {
            "success": True,
            "content": f"Mock {style.upper()} citations for {len(paper_ids)} papers",
            "filename": f"citations.{format}",
            "paper_count": len(paper_ids)
        }
    
    # PDF Retrieval methods
    async def retrieve_pdfs(self, papers: List[dict], user_id: str) -> str:
        """Retrieve PDFs for papers"""
        return f"mock_batch_{user_id}_{len(papers)}"
    
    async def get_pdf_batch_status(self, batch_id: str) -> Optional[dict]:
        """Get PDF batch status"""
        return {
            "batch_id": batch_id,
            "status": "completed",
            "progress": 1.0,
            "total_papers": 5,
            "completed_papers": 5,
            "failed_papers": 0
        }
    
    # Ingestion methods
    async def ingest_batch(self, papers: List[dict], user_id: str) -> str:
        """Ingest batch of papers"""
        return f"mock_ingestion_{user_id}_{len(papers)}"
    
    async def ingest_single(self, paper_id: str, pdf_path: str, user_id: str, metadata: Optional[dict] = None) -> dict:
        """Ingest single paper"""
        return {
            "success": True,
            "paper_id": paper_id,
            "status": "ingested",
            "processing_time": 2.5
        }
    
    async def get_ingestion_batch_status(self, batch_id: str) -> Optional[dict]:
        """Get ingestion batch status"""
        return {
            "batch_id": batch_id,
            "status": "processing",
            "progress": 0.6,
            "total_papers": 3,
            "completed_papers": 2,
            "failed_papers": 0
        }
    
    # Knowledge Gap methods
    async def analyze_gaps(self, user_id: str, topic: Optional[str] = None) -> dict:
        """Analyze knowledge gaps"""
        mock_gaps = [
            {
                "id": "gap_1",
                "topic": "Machine Learning in Healthcare",
                "description": "Limited research on ML applications in medical diagnosis",
                "confidence": 0.85,
                "suggested_papers": [
                    {
                        "paper_id": "suggested_1",
                        "title": "Deep Learning for Medical Imaging",
                        "authors": ["Dr. AI Researcher"],
                        "year": 2023,
                        "venue": "Medical AI Journal",
                        "citation_count": 45
                    }
                ],
                "created_at": "2024-01-01T00:00:00Z"
            },
            {
                "id": "gap_2", 
                "topic": "Sustainable Computing",
                "description": "Gap in energy-efficient algorithm design",
                "confidence": 0.72,
                "suggested_papers": [],
                "created_at": "2024-01-01T00:00:00Z"
            }
        ]
        
        return {"gaps": mock_gaps}
    
    async def trigger_knowledge_expansion(self, gap: dict, max_papers: int, user_id: str) -> dict:
        """Trigger knowledge expansion"""
        return {
            "success": True,
            "task_id": f"expansion_{gap.get('id', 'unknown')}_{user_id}",
            "gap_id": gap.get("id"),
            "max_papers": max_papers,
            "status": "started"
        }
    
    async def get_expansion_history(self, user_id: str, limit: int = 10) -> List[dict]:
        """Get expansion history"""
        return [
            {
                "id": "exp_1",
                "gap_topic": "Mock Research Area", 
                "papers_found": 5,
                "status": "completed",
                "created_at": "2024-01-01T00:00:00Z"
            }
        ]
    
    # Helper methods for FastAPI endpoints
    async def upload_paper(
        self,
        file_data: str,  # base64 encoded
        paper_id: str,
        user_id: str,
        filename: str,
        metadata: Optional[dict] = None
    ) -> dict:
        """Upload paper and create database record"""
        try:
            # Create paper in database
            title = metadata.get('title', filename) if metadata else filename
            authors = metadata.get('authors', []) if metadata else []
            
            result = await self.supabase_client.create_paper(
                paper_id=paper_id,
                title=title,
                authors=authors,
                user_id=user_id,
                metadata=metadata
            )
            
            if result.get('success'):
                # TODO: Integrate with actual file storage via MCP tools
                result['pdf_path'] = f"/storage/users/{user_id}/papers/{paper_id}.pdf"
                result['file_size'] = len(file_data) * 3 // 4  # Estimate from base64
                result['checksum'] = "sha256:placeholder"
            
            return result
            
        except Exception as e:
            logger.error(f"Upload paper failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def trigger_ingestion(
        self,
        paper_id: str,
        pdf_path: str,
        user_id: str,
        metadata: dict
    ) -> dict:
        """Trigger paper ingestion"""
        result = await self.ingest_single(paper_id, pdf_path, user_id, metadata)
        
        return {
            "success": result.get("success", False),
            "task_id": f"ingest_{paper_id}",
            "paper_id": paper_id
        }
    
    async def get_paper_details(self, paper_id: str, user_id: str) -> Optional[dict]:
        """Get detailed paper information from database"""
        try:
            return await self.supabase_client.get_paper_details(paper_id, user_id)
        except Exception as e:
            logger.error(f"Get paper details failed: {str(e)}")
            return None
    
    async def delete_paper(self, paper_id: str, user_id: str) -> dict:
        """Delete paper from database"""
        try:
            result = await self.supabase_client.delete_paper(paper_id, user_id)
            if result.get('success'):
                result['message'] = 'Paper deleted successfully'
            return result
        except Exception as e:
            logger.error(f"Delete paper failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def add_paper_note(
        self,
        paper_id: str,
        user_id: str,
        note_type: str,
        note_text: str,
        highlight_text: Optional[str] = None,
        page_number: Optional[int] = None
    ) -> dict:
        """Add note to paper"""
        # This would integrate with database
        return {
            "success": True,
            "note": {
                "id": 123,
                "paper_id": paper_id,
                "user_id": user_id,
                "note_type": note_type,
                "note_text": note_text,
                "highlight_text": highlight_text,
                "page_number": page_number,
                "created_at": "2024-10-19T12:00:00Z",
                "updated_at": "2024-10-19T12:00:00Z"
            }
        }
    
    async def update_paper_status(
        self,
        paper_id: str,
        user_id: str,
        status: Optional[str] = None,
        starred: Optional[bool] = None,
        rating: Optional[int] = None
    ) -> dict:
        """Update paper reading status in database"""
        try:
            result = await self.supabase_client.update_reading_status(
                paper_id=paper_id,
                user_id=user_id,
                status=status,
                starred=starred,
                rating=rating
            )
            
            if result.get('success'):
                result.update({
                    'paper_id': paper_id,
                    'status': status,
                    'starred': starred,
                    'rating': rating
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Update paper status failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def add_to_collection(self, paper_id: str, user_id: str, collection_id: int) -> dict:
        """Add paper to collection in database"""
        try:
            result = await self.supabase_client.add_to_collection(paper_id, user_id, collection_id)
            if result.get('success'):
                result.update({
                    'paper_id': paper_id,
                    'collection_id': collection_id
                })
            return result
        except Exception as e:
            logger.error(f"Add to collection failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def add_paper_tags(self, paper_id: str, user_id: str, tags: List[str]) -> dict:
        """Add tags to paper in database"""
        try:
            result = await self.supabase_client.add_paper_tags(paper_id, user_id, tags)
            if result.get('success'):
                result.update({
                    'paper_id': paper_id,
                    'tags': tags
                })
            return result
        except Exception as e:
            logger.error(f"Add paper tags failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_task_status(self, task_id: str) -> Optional[dict]:
        """Get async task status"""
        # This would integrate with task tracking
        return {
            "task_id": task_id,
            "status": "running",
            "progress": 0.5,
            "created_at": "2024-10-19T12:00:00Z"
        }
    
    async def get_user_stats(self, user_id: str) -> dict:
        """Get user statistics from database"""
        try:
            return await self.supabase_client.get_user_stats(user_id)
        except Exception as e:
            logger.error(f"Get user stats failed: {str(e)}")
            return {
                "total_papers": 0,
                "ingested_papers": 0,
                "to_read": 0,
                "reading": 0,
                "read": 0,
                "starred": 0,
                "recent_activity": 0
            }