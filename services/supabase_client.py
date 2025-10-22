"""
Supabase Client for PiyP Reference Manager.

Handles all database operations using Supabase Python client.
Provides CRUD operations for papers, collections, tags, and user statistics.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from supabase import create_client, Client
from config import get_settings

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Async wrapper for Supabase client with RefMan-specific operations"""
    
    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[Client] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize connection to Supabase"""
        try:
            logger.info("Initializing Supabase connection...")
            self._client = create_client(
                self.settings.SUPABASE_URL,
                self.settings.SUPABASE_SERVICE_ROLE_KEY
            )
            self._initialized = True
            logger.info("Supabase client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {str(e)}")
            raise
    
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if database is accessible"""
        try:
            if not self._initialized or not self._client:
                return {
                    "status": "unhealthy",
                    "connected": False,
                    "error": "Client not initialized"
                }
            
            # Test basic query
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._client.table('research_papers').select('paper_id', count='exact').limit(1).execute()
            )
            
            return {
                "status": "healthy",
                "connected": True,
                "total_papers": result.count if hasattr(result, 'count') and result.count is not None else 0
            }
            
        except Exception as e:
            logger.error(f"Supabase health check failed: {str(e)}")
            return {
                "status": "unhealthy", 
                "connected": False,
                "error": str(e)
            }
    
    # ============ PAPER OPERATIONS ============
    
    async def search_papers(
        self,
        user_id: str,
        query: str = "",
        filters: Optional[Dict] = None,
        sort: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Search papers with filtering and pagination"""
        try:
            if not self._initialized:
                await self.initialize()
            
            # Build minimal query with only confirmed existing columns
            query_builder = self._client.table('research_papers').select(
                '''
                paper_id,
                title
                '''
            )
            
            # TODO: Add user_id filtering when column is added to database
            # For now, return all papers (will be filtered by RLS if configured)
            
            # Apply basic filters (only using confirmed existing columns)
            if filters:
                if filters.get('title_contains'):
                    query_builder = query_builder.ilike('title', f"%{filters['title_contains']}%")
                
                # TODO: Add other filters when column existence is confirmed
                # - author, year_min, year_max, venue, status, starred
            
            # Apply text search if query provided (only on confirmed columns)
            if query:
                query_builder = query_builder.ilike('title', f"%{query}%")
            
            # Apply sorting (only using confirmed columns)
            if sort:
                if sort.startswith('title_asc'):
                    query_builder = query_builder.order('title', desc=False)
                else:
                    # Default to title sorting for now
                    query_builder = query_builder.order('title', desc=False)
            else:
                # Default sorting by title
                query_builder = query_builder.order('title', desc=False)
            
            # Get total count (TODO: filter by user when user_id column exists)
            count_result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.table('research_papers').select('paper_id', count='exact').execute()
            )
            total_count = count_result.count if count_result else 0
            
            # Apply pagination and execute
            query_builder = query_builder.range(offset, offset + limit - 1)
            
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: query_builder.execute()
            )
            
            papers = []
            if result.data:
                for paper_data in result.data:
                    # Transform to expected format with minimal data + defaults
                    paper = {
                        "paper_id": paper_data['paper_id'],
                        "title": paper_data.get('title', 'Untitled Paper'),
                        "authors": [],  # Default empty array
                        "year": None,   # Default null
                        "venue": "",    # Default empty string
                        "doi": "",      # Default empty string
                        "arxiv_id": "", # Default empty string
                        "citation_count": 0,  # Default zero
                        "date_added": "2024-01-01T00:00:00Z",  # Default timestamp
                        "status": "to_read",  # Default
                        "starred": False,
                        "rating": None
                    }
                    
                    # TODO: Add reading status lookup in a separate query for better performance
                    
                    papers.append(paper)
            
            return {
                "success": True,
                "papers": papers,
                "total": total_count,
                "offset": offset,
                "limit": limit
            }
            
        except Exception as e:
            logger.error(f"Search papers failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "papers": [],
                "total": 0
            }
    
    async def get_paper_details(self, paper_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get complete paper details including reading status and notes"""
        try:
            if not self._initialized:
                await self.initialize()
            
            # Get paper with reading status
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.table('research_papers').select(
                    '''
                    id,
                    user_id,
                    paper_id,
                    title,
                    authors,
                    abstract,
                    year,
                    published,
                    doi,
                    arxiv_id,
                    pmid,
                    pmc_id,
                    venue,
                    citation_count,
                    fields_of_study,
                    url,
                    pdf_url,
                    pdf_path,
                    status,
                    processing_status,
                    created_at,
                    updated_at,
                    paper_reading_status (
                        status,
                        starred,
                        rating,
                        started_at,
                        completed_at,
                        updated_at
                    ),
                    paper_tags (
                        tags (
                            tag_name,
                            color
                        )
                    ),
                    collection_papers (
                        collections (
                            id,
                            name
                        )
                    )
                    '''
                ).eq('paper_id', paper_id).single().execute()
            )
            
            if not result.data:
                return None
            
            paper_data = result.data
            
            # Transform to expected format
            paper = {
                "paper_id": paper_data['paper_id'],
                "title": paper_data['title'],
                "authors": paper_data['authors'],
                "year": paper_data['year'],
                "venue": paper_data['venue'],
                "doi": paper_data['doi'],
                "arxiv_id": paper_data['arxiv_id'],
                "abstract": paper_data.get('abstract', ''),
                "citation_count": paper_data.get('citation_count', 0),
                "pdf_url": paper_data.get('pdf_url'),
                "date_added": paper_data['created_at'],
                "status": "to_read",
                "starred": False,
                "rating": None,
                "tags": [],
                "collections": [],
                "notes": []  # TODO: Implement notes table
            }
            
            # Add reading status
            if paper_data.get('paper_reading_status'):
                status_data = paper_data['paper_reading_status'][0] if isinstance(paper_data['paper_reading_status'], list) else paper_data['paper_reading_status']
                if status_data:
                    paper.update({
                        "status": status_data.get('status', 'to_read'),
                        "starred": status_data.get('starred', False),
                        "rating": status_data.get('rating'),
                        "started_at": status_data.get('started_at'),
                        "completed_at": status_data.get('completed_at')
                    })
            
            # Add tags
            if paper_data.get('paper_tags'):
                paper['tags'] = [
                    {
                        "name": tag_data['tags']['tag_name'],
                        "color": tag_data['tags']['color']
                    }
                    for tag_data in paper_data['paper_tags']
                    if tag_data.get('tags')
                ]
            
            # Add collections
            if paper_data.get('collection_papers'):
                paper['collections'] = [
                    {
                        "id": coll_data['collections']['id'],
                        "name": coll_data['collections']['name']
                    }
                    for coll_data in paper_data['collection_papers']
                    if coll_data.get('collections')
                ]
            
            return paper
            
        except Exception as e:
            logger.error(f"Get paper details failed: {str(e)}")
            return None
    
    async def _get_or_create_default_research_query(self, user_id: str) -> str:
        """Get or create a default research query for uploaded papers"""
        try:
            # First, check if a default query already exists
            def query_existing():
                return self._client.table('research_queries').select('id').eq('user_id', user_id).eq('query_text', 'Uploaded Papers').execute()
            
            result = await asyncio.get_event_loop().run_in_executor(None, query_existing)
            
            if result.data:
                return result.data['id']
            
        except Exception:
            # Query doesn't exist, so create it
            pass
        
        # Create default research query for uploaded papers
        try:
            query_data = {
                "user_id": user_id,
                "query_text": "Uploaded Papers",
                "query_type": "manual_upload",
                "status": "completed"
            }
            
            def create_query():
                return self._client.table('research_queries').insert(query_data).select('id').execute()
            
            result = await asyncio.get_event_loop().run_in_executor(None, create_query)
            
            if result.data:
                return result.data['id']
            else:
                raise Exception("Failed to create default research query")
                
        except Exception as e:
            logger.error(f"Failed to create default research query: {str(e)}")
            # Fallback: try to find any existing research query for this user
            try:
                def find_any_query():
                    return self._client.table('research_queries').select('id').eq('user_id', user_id).limit(1).execute()
                
                result = await asyncio.get_event_loop().run_in_executor(None, find_any_query)
                
                if result.data:
                    return result.data['id']
            except Exception:
                pass
            
            # If all else fails, raise the original error
            raise e
    
    async def create_paper(
        self,
        paper_id: str,
        title: str,
        authors: List[str],
        user_id: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create new paper record"""
        try:
            if not self._initialized:
                await self.initialize()
            
            # Get or create a default research query for uploaded papers
            default_query_id = await self._get_or_create_default_research_query(user_id)
            
            # Map to actual database columns based on schema
            paper_data = {
                "paper_id": paper_id,  # Custom paper_id field 
                "title": title,
                "research_query_id": default_query_id,  # Required field - use default query for uploaded papers
                "authors": authors,  # Authors array
            }
            
            # Add optional metadata if provided
            if metadata:
                if metadata.get("year"):
                    paper_data["publication_year"] = metadata["year"]
                if metadata.get("venue"):
                    paper_data["venue"] = metadata["venue"]
                if metadata.get("doi"):
                    paper_data["doi"] = metadata["doi"] 
                if metadata.get("arxiv_id"):
                    paper_data["arxiv_id"] = metadata["arxiv_id"]
                if metadata.get("abstract"):
                    paper_data["abstract"] = metadata["abstract"]
                if metadata.get("url"):
                    paper_data["url"] = metadata["url"]
                if metadata.get("pdf_url"):
                    paper_data["pdf_url"] = metadata["pdf_url"]
            
            # Insert paper
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.table('research_papers').insert(paper_data).execute()
            )
            
            if result.data:
                # Create initial reading status
                await self.create_reading_status(paper_id, user_id, 'to_read')
                
                return {
                    "success": True,
                    "paper_id": paper_id,
                    "data": result.data[0]
                }
            
            return {"success": False, "error": "Failed to create paper"}
            
        except Exception as e:
            logger.error(f"Create paper failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def update_paper(self, paper_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update paper record"""
        try:
            if not self._initialized:
                await self.initialize()
            
            # Let the database handle updated_at via triggers
            
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.table('research_papers').update(updates).eq('paper_id', paper_id).execute()
            )
            
            return {
                "success": bool(result.data),
                "data": result.data[0] if result.data else None
            }
            
        except Exception as e:
            logger.error(f"Update paper failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def delete_paper(self, paper_id: str, user_id: str) -> Dict[str, Any]:
        """Delete paper and all related data"""
        try:
            if not self._initialized:
                await self.initialize()
            
            # Delete reading status first (due to foreign key)
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.table('paper_reading_status').delete().eq('paper_id', paper_id).execute()
            )
            
            # Delete paper tags
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.table('paper_tags').delete().eq('paper_id', paper_id).execute()
            )
            
            # Delete from collections
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.table('collection_papers').delete().eq('paper_id', paper_id).execute()
            )
            
            # Delete the paper
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.table('research_papers').delete().eq('paper_id', paper_id).execute()
            )
            
            return {"success": True}
            
        except Exception as e:
            logger.error(f"Delete paper failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    # ============ READING STATUS OPERATIONS ============
    
    async def create_reading_status(
        self,
        paper_id: str,
        user_id: str,
        status: str = 'to_read'
    ) -> Dict[str, Any]:
        """Create reading status for paper"""
        try:
            if not self._initialized:
                await self.initialize()
            
            status_data = {
                "paper_id": paper_id,
                "user_id": user_id,
                "status": status,
                "starred": False
                # Let database handle updated_at
            }
            
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.table('paper_reading_status').upsert(status_data).execute()
            )
            
            return {"success": bool(result.data)}
            
        except Exception as e:
            logger.error(f"Create reading status failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def update_reading_status(
        self,
        paper_id: str,
        user_id: str,
        status: Optional[str] = None,
        starred: Optional[bool] = None,
        rating: Optional[int] = None
    ) -> Dict[str, Any]:
        """Update paper reading status"""
        try:
            if not self._initialized:
                await self.initialize()
            
            updates = {}  # Let database handle updated_at
            
            if status is not None:
                updates["status"] = status
                # Set timestamps for status transitions
                if status == "reading":
                    updates["started_at"] = "now()"
                elif status == "read":
                    updates["completed_at"] = "now()"
            
            if starred is not None:
                updates["starred"] = starred
            
            if rating is not None:
                updates["rating"] = rating
            
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.table('paper_reading_status').upsert({
                    "paper_id": paper_id,
                    "user_id": user_id,
                    **updates
                }).execute()
            )
            
            return {"success": bool(result.data)}
            
        except Exception as e:
            logger.error(f"Update reading status failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    # ============ COLLECTIONS OPERATIONS ============
    
    async def get_collections(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user collections with paper counts"""
        try:
            if not self._initialized:
                await self.initialize()
            
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.from_('collection_stats').select('*').eq('user_id', user_id).execute()
            )
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Get collections failed: {str(e)}")
            return []
    
    async def add_to_collection(
        self,
        paper_id: str,
        user_id: str,
        collection_id: int
    ) -> Dict[str, Any]:
        """Add paper to collection"""
        try:
            if not self._initialized:
                await self.initialize()
            
            # Verify collection belongs to user
            coll_check = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.table('collections').select('id').eq('id', collection_id).eq('user_id', user_id).execute()
            )
            
            if not coll_check.data:
                return {"success": False, "error": "Collection not found or access denied"}
            
            # Add to collection
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.table('collection_papers').upsert({
                    "collection_id": collection_id,
                    "paper_id": paper_id
                    # Let database handle added_at via DEFAULT NOW()
                }).execute()
            )
            
            return {"success": bool(result.data)}
            
        except Exception as e:
            logger.error(f"Add to collection failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    # ============ TAGS OPERATIONS ============
    
    async def add_paper_tags(
        self,
        paper_id: str,
        user_id: str,
        tag_names: List[str]
    ) -> Dict[str, Any]:
        """Add tags to paper"""
        try:
            if not self._initialized:
                await self.initialize()
            
            for tag_name in tag_names:
                # Get or create tag
                tag_result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._client.table('tags').upsert({
                        "user_id": user_id,
                        "tag_name": tag_name
                        # Let database handle created_at via DEFAULT NOW()
                    }).execute()
                )
                
                if tag_result.data:
                    tag_id = tag_result.data[0]['id']
                    
                    # Add paper-tag relationship
                    await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self._client.table('paper_tags').upsert({
                            "paper_id": paper_id,
                            "tag_id": tag_id
                            # Let database handle added_at via DEFAULT NOW()
                        }).execute()
                    )
            
            return {"success": True}
            
        except Exception as e:
            logger.error(f"Add paper tags failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    # ============ STATISTICS ============
    
    async def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user statistics from paper_stats_by_user view"""
        try:
            if not self._initialized:
                await self.initialize()
            
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.from_('paper_stats_by_user').select('*').eq('user_id', user_id).execute()
            )
            
            if result.data and len(result.data) > 0:
                stats_data = result.data[0]
                return {
                    "total_papers": stats_data.get('total_papers', 0),
                    "starred": stats_data.get('starred_papers', 0),
                    "to_read": stats_data.get('to_read_papers', 0),
                    "reading": stats_data.get('reading_papers', 0),
                    "read": stats_data.get('read_papers', 0),
                    "ingested_papers": stats_data.get('total_papers', 0),  # Assume all are ingested for now
                    "recent_activity": 0  # TODO: Implement recent activity calculation
                }
            
            return {
                "total_papers": 0,
                "ingested_papers": 0,
                "to_read": 0,
                "reading": 0,
                "read": 0,
                "starred": 0,
                "recent_activity": 0
            }
            
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