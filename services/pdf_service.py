"""
PDF Service for PiyP Reference Manager.

Handles PDF file operations, streaming, and storage management.
"""

import os
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class PDFService:
    """
    Service for PDF file operations.
    
    Handles PDF storage, retrieval, and streaming for the web interface.
    """
    
    def __init__(self, storage_path: str = "/storage"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    async def get_pdf_path(self, paper_id: str, user_id: str) -> Optional[str]:
        """Get the file path for a paper's PDF"""
        try:
            # Construct expected path
            pdf_path = self.storage_path / "users" / user_id / "papers" / f"{paper_id}.pdf"
            
            if pdf_path.exists():
                return str(pdf_path)
            
            # Also check alternative naming patterns
            alt_paths = [
                self.storage_path / "papers" / f"{paper_id}.pdf",
                self.storage_path / f"{paper_id}.pdf"
            ]
            
            for alt_path in alt_paths:
                if alt_path.exists():
                    return str(alt_path)
            
            logger.warning(f"PDF not found for paper {paper_id}, user {user_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting PDF path for paper {paper_id}: {str(e)}")
            return None
    
    async def store_pdf(self, paper_id: str, user_id: str, pdf_data: bytes) -> str:
        """Store PDF data to file system"""
        try:
            # Create user directory structure
            user_dir = self.storage_path / "users" / user_id / "papers"
            user_dir.mkdir(parents=True, exist_ok=True)
            
            # Write PDF file
            pdf_path = user_dir / f"{paper_id}.pdf"
            
            with open(pdf_path, 'wb') as f:
                f.write(pdf_data)
            
            logger.info(f"Stored PDF for paper {paper_id} at {pdf_path}")
            return str(pdf_path)
            
        except Exception as e:
            logger.error(f"Error storing PDF for paper {paper_id}: {str(e)}")
            raise
    
    async def delete_pdf(self, paper_id: str, user_id: str) -> bool:
        """Delete PDF file"""
        try:
            pdf_path = await self.get_pdf_path(paper_id, user_id)
            
            if pdf_path and os.path.exists(pdf_path):
                os.remove(pdf_path)
                logger.info(f"Deleted PDF for paper {paper_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error deleting PDF for paper {paper_id}: {str(e)}")
            return False
    
    async def get_pdf_info(self, paper_id: str, user_id: str) -> Optional[dict]:
        """Get PDF file information"""
        try:
            pdf_path = await self.get_pdf_path(paper_id, user_id)
            
            if not pdf_path or not os.path.exists(pdf_path):
                return None
            
            stat = os.stat(pdf_path)
            
            return {
                "path": pdf_path,
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "exists": True
            }
            
        except Exception as e:
            logger.error(f"Error getting PDF info for paper {paper_id}: {str(e)}")
            return None