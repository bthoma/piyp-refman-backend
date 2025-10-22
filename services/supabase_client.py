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
        """Initialize Supabase client connection"""
        try:
            self._client = create_client(
                self.settings.SUPABASE_URL,
                self.settings.SUPABASE_SERVICE_ROLE_KEY
            )
            
            # Test connection
            await self._execute_simple_query("health_check")
            self._initialized = True
            logger.info("Supabase client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {str(e)}")
            raise
    
    async def _execute_simple_query(self, table: str, operation: str = "SELECT 1"):
        """Execute simple query for health checks"""
        if not self._initialized or not self._client:
            await self.initialize()
        
        try:
            # Run a simple query to test connection
            loop = asyncio.get_event_loop()
            if table == "health_check":
                # Just test basic connection
                result = await loop.run_in_executor(
                    None,
                    lambda: self._client.table('research_papers').select('paper_id', count='exact').limit(1).execute()
                )
            else:
                result = await loop.run_in_executor(
                    None,
                    lambda: self._client.table(table).select('*').limit(1).execute()
                )
            return result
        except Exception as e:
            logger.error(f"Query execution failed: {table} - {str(e)}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Supabase connection health"""
        try:
            if not self._initialized:
                await self.initialize()
            
            # Test basic query
            result = await self._execute_simple_query("health_check")
            
            return {
                "status": "healthy",
                "connected": True,
                "total_papers": result.count if hasattr(result, 'count') and result.count is not None else 0
            }
            
        except Exception as e:
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
            
            # Build base query
            query_builder = self._client.table('research_papers').select(
                '''
                paper_id,
                title,
                authors,
                year,
                venue,
                doi,
                arxiv_id,
                citation_count,
                created_at,
                updated_at,
                paper_reading_status (
                    status,
                    starred,
                    rating,
                    updated_at
                )
                '''
            )
            
            # Apply filters
            if filters:
                if filters.get('author'):
                    query_builder = query_builder.ilike('authors', f"%{filters['author']}%")
                
                if filters.get('year_min'):
                    query_builder = query_builder.gte('year', filters['year_min'])
                    
                if filters.get('year_max'):
                    query_builder = query_builder.lte('year', filters['year_max'])
                
                if filters.get('venue'):
                    query_builder = query_builder.ilike('venue', f"%{filters['venue']}%")
                
                if filters.get('title_contains'):
                    query_builder = query_builder.ilike('title', f"%{filters['title_contains']}%")
                
                if filters.get('status'):
                    query_builder = query_builder.eq('paper_reading_status.status', filters['status'])
                
                if filters.get('starred') is not None:
                    query_builder = query_builder.eq('paper_reading_status.starred', filters['starred'])
            
            # Apply text search if query provided
            if query:
                query_builder = query_builder.or_(
                    f"title.ilike.%{query}%,"
                    f"authors.ilike.%{query}%,"
                    f"abstract.ilike.%{query}%"
                )
            
            # Apply sorting
            if sort:
                if sort.startswith('date_added_desc'):
                    query_builder = query_builder.order('created_at', desc=True)
                elif sort.startswith('date_added_asc'):
                    query_builder = query_builder.order('created_at', desc=False)
                elif sort.startswith('date_published_desc'):
                    query_builder = query_builder.order('year', desc=True)
                elif sort.startswith('date_published_asc'):
                    query_builder = query_builder.order('year', desc=False)
                elif sort.startswith('citations_desc'):
                    query_builder = query_builder.order('citation_count', desc=True)
                elif sort.startswith('title_asc'):
                    query_builder = query_builder.order('title', desc=False)
            else:
                query_builder = query_builder.order('created_at', desc=True)
            
            # Get total count
            count_result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.table('research_papers').select('*', count='exact').execute()
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
                    # Transform to expected format
                    paper = {
                        "paper_id": paper_data['paper_id'],
                        "title": paper_data['title'],
                        "authors": paper_data['authors'],
                        "year": paper_data['year'],
                        "venue": paper_data['venue'],
                        "doi": paper_data['doi'],
                        "arxiv_id": paper_data['arxiv_id'],
                        "citation_count": paper_data.get('citation_count', 0),
                        "date_added": paper_data['created_at'],
                        "status": "to_read",  # Default
                        "starred": False,
                        "rating": None
                    }
                    
                    # Add reading status if available
                    if paper_data.get('paper_reading_status'):
                        status_data = paper_data['paper_reading_status'][0] if isinstance(paper_data['paper_reading_status'], list) else paper_data['paper_reading_status']
                        if status_data:
                            paper.update({
                                "status": status_data.get('status', 'to_read'),
                                "starred": status_data.get('starred', False),
                                "rating": status_data.get('rating')
                            })
                    
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
                    *,
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
            
            paper_data = {
                "paper_id": paper_id,
                "title": title,
                "authors": authors,
                "year": metadata.get('year') if metadata else None,
                "venue": metadata.get('venue') if metadata else None,
                "doi": metadata.get('doi') if metadata else None,
                "arxiv_id": metadata.get('arxiv_id') if metadata else None,
                "abstract": metadata.get('abstract', '') if metadata else '',
                "pdf_url": metadata.get('pdf_url') if metadata else None,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
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
            
            updates['updated_at'] = datetime.utcnow().isoformat()
            
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
                "starred": False,
                "updated_at": datetime.utcnow().isoformat()
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
            
            updates = {"updated_at": datetime.utcnow().isoformat()}
            
            if status is not None:
                updates["status"] = status
                if status == "reading" and not updates.get("started_at"):
                    updates["started_at"] = datetime.utcnow().isoformat()
                elif status == "read" and not updates.get("completed_at"):
                    updates["completed_at"] = datetime.utcnow().isoformat()
            
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
                    "paper_id": paper_id,
                    "added_at": datetime.utcnow().isoformat()
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
                        "tag_name": tag_name,
                        "created_at": datetime.utcnow().isoformat()
                    }).execute()
                )
                
                if tag_result.data:
                    tag_id = tag_result.data[0]['id']
                    
                    # Add paper-tag relationship
                    await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self._client.table('paper_tags').upsert({
                            "paper_id": paper_id,
                            "tag_id": tag_id,
                            "added_at": datetime.utcnow().isoformat()
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