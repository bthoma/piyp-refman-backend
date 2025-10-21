"""
Agent Client Service.

Handles communication with the PiyP Agent system.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
import sys
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import agents
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../piyp_agents'))
from piyp_agents import AGENT_FUNCTIONS


class AgentClient:
    """
    Client for communicating with PiyP agents.
    
    Provides a unified interface to all agent functions
    for the FastAPI backend.
    """
    
    def __init__(self):
        self.initialized = False
        
    async def initialize(self):
        """Initialize agent connections"""
        try:
            logger.info("Initializing agent client")
            
            # Test agent connectivity
            await self.health_check()
            
            self.initialized = True
            logger.info("Agent client initialized successfully")
            
        except Exception as e:
            logger.error(f"Agent client initialization failed: {str(e)}")
            raise
    
    async def health_check(self) -> Dict[str, str]:
        """Check agent health status"""
        try:
            # Test each agent
            agent_status = {}
            
            # Test orchestrator
            try:
                result = await AGENT_FUNCTIONS["get_session_status"]("health_check_user")
                agent_status["reference_manager_orchestrator"] = "healthy"
            except Exception as e:
                agent_status["reference_manager_orchestrator"] = f"error: {str(e)}"
            
            # Test other agents
            agents_to_test = [
                "search_papers",
                "analyze_gaps"
            ]
            
            for agent_func in agents_to_test:
                try:
                    # Simple test calls
                    if agent_func == "search_papers":
                        await AGENT_FUNCTIONS[agent_func]("test", "traditional", "health_check_user", limit=1)
                    elif agent_func == "analyze_gaps":
                        await AGENT_FUNCTIONS[agent_func]("health_check_user")
                    
                    agent_status[agent_func] = "healthy"
                except Exception as e:
                    agent_status[agent_func] = f"error: {str(e)}"
            
            return agent_status
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {"status": f"error: {str(e)}"}
    
    # Orchestrator methods
    async def process_paper_list(self, papers: List[dict], user_id: str, source: str = "research_domain") -> dict:
        """Process paper list from Research domain"""
        return await AGENT_FUNCTIONS["process_paper_list"](papers, user_id, source)
    
    async def get_session_status(self, user_id: str) -> dict:
        """Get user session status"""
        return await AGENT_FUNCTIONS["get_session_status"](user_id)
    
    async def cancel_operation(self, user_id: str, operation_id: str) -> dict:
        """Cancel user operation"""
        return await AGENT_FUNCTIONS["cancel_operation"](user_id, operation_id)
    
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
        """Search papers using Library Curator"""
        return await AGENT_FUNCTIONS["search_papers"](
            query, mode, user_id, filters, sort, limit, offset
        )
    
    async def export_citations(self, paper_ids: List[str], style: str, format: str, user_id: str) -> dict:
        """Export citations"""
        return await AGENT_FUNCTIONS["export_citations"](paper_ids, style, format, user_id)
    
    # PDF Retrieval methods
    async def retrieve_pdfs(self, papers: List[dict], user_id: str) -> str:
        """Retrieve PDFs for papers"""
        return await AGENT_FUNCTIONS["retrieve_pdfs"](papers, user_id)
    
    async def get_pdf_batch_status(self, batch_id: str) -> Optional[dict]:
        """Get PDF batch status"""
        return await AGENT_FUNCTIONS["get_pdf_batch_status"](batch_id)
    
    # Ingestion methods
    async def ingest_batch(self, papers: List[dict], user_id: str) -> str:
        """Ingest batch of papers"""
        return await AGENT_FUNCTIONS["ingest_batch"](papers, user_id)
    
    async def ingest_single(self, paper_id: str, pdf_path: str, user_id: str, metadata: Optional[dict] = None) -> dict:
        """Ingest single paper"""
        return await AGENT_FUNCTIONS["ingest_single"](paper_id, pdf_path, user_id, metadata)
    
    async def get_ingestion_batch_status(self, batch_id: str) -> Optional[dict]:
        """Get ingestion batch status"""
        return await AGENT_FUNCTIONS["get_ingestion_batch_status"](batch_id)
    
    # Knowledge Gap methods
    async def analyze_gaps(self, user_id: str, topic: Optional[str] = None) -> dict:
        """Analyze knowledge gaps"""
        return await AGENT_FUNCTIONS["analyze_gaps"](user_id, topic)
    
    async def trigger_knowledge_expansion(self, gap: dict, max_papers: int, user_id: str) -> dict:
        """Trigger knowledge expansion"""
        return await AGENT_FUNCTIONS["trigger_knowledge_expansion"](gap, max_papers, user_id)
    
    async def get_expansion_history(self, user_id: str, limit: int = 10) -> List[dict]:
        """Get expansion history"""
        return await AGENT_FUNCTIONS["get_expansion_history"](user_id, limit)
    
    # Helper methods for FastAPI endpoints
    async def upload_paper(
        self,
        file_data: str,  # base64 encoded
        paper_id: str,
        user_id: str,
        filename: str,
        metadata: Optional[dict] = None
    ) -> dict:
        """Upload paper via MCP tools"""
        # This would integrate with MCP tools
        # For now, simulate upload
        return {
            "success": True,
            "paper_id": paper_id,
            "pdf_path": f"/storage/users/{user_id}/papers/{paper_id}.pdf",
            "file_size": len(file_data) * 3 // 4,  # Estimate from base64
            "checksum": "sha256:placeholder"
        }
    
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
        """Get detailed paper information"""
        # This would query the database directly
        # For now, return placeholder
        return {
            "paper_id": paper_id,
            "title": "Sample Paper Title",
            "authors": ["Author One", "Author Two"],
            "year": 2023,
            "venue": "Sample Conference",
            "abstract": "This is a sample abstract...",
            "pdf_available": True,
            "status": "read",
            "starred": False,
            "tags": ["machine learning", "nlp"],
            "notes": []
        }
    
    async def delete_paper(self, paper_id: str, user_id: str) -> dict:
        """Delete paper"""
        # This would integrate with MCP tools
        return {
            "success": True,
            "paper_id": paper_id,
            "message": "Paper deleted successfully"
        }
    
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
        """Update paper reading status"""
        # This would integrate with database
        return {
            "success": True,
            "paper_id": paper_id,
            "status": status,
            "starred": starred,
            "rating": rating
        }
    
    async def add_to_collection(self, paper_id: str, user_id: str, collection_id: int) -> dict:
        """Add paper to collection"""
        # This would integrate with database
        return {
            "success": True,
            "paper_id": paper_id,
            "collection_id": collection_id
        }
    
    async def add_paper_tags(self, paper_id: str, user_id: str, tags: List[str]) -> dict:
        """Add tags to paper"""
        # This would integrate with database
        return {
            "success": True,
            "paper_id": paper_id,
            "tags": tags
        }
    
    async def get_task_status(self, task_id: str) -> Optional[dict]:
        """Get async task status"""
        # This would integrate with task tracking
        return {
            "task_id": task_id,
            "status": "running",
            "progress": 0.5,
            "created_at": "2024-10-19T12:00:00Z"
        }