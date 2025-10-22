"""
PDF Metadata Extractor Service.

Automatically extracts metadata from uploaded PDF files using:
1. Basic PDF properties (title, author, subject)
2. DOI lookup via Crossref API for complete metadata
3. Text extraction from first page for pattern matching

Provides high-quality metadata extraction to minimize manual data entry.
"""

import asyncio
import logging
import re
import requests
from typing import Optional, Dict, List, Any
from datetime import datetime
import PyPDF2
from io import BytesIO
import aiohttp

logger = logging.getLogger(__name__)


class PDFMetadataExtractor:
    """Extract metadata from PDF files using multiple strategies"""
    
    def __init__(self):
        self.crossref_api_url = "https://api.crossref.org/works"
        self.session_headers = {
            'User-Agent': 'PiyP-RefMan/1.0 (mailto:support@piyp.com)'  # Polite API usage
        }
    
    async def extract_pdf_metadata(self, file_data: bytes, filename: str) -> Dict[str, Any]:
        """
        Extract comprehensive metadata from PDF file.
        
        Args:
            file_data: PDF file content as bytes
            filename: Original filename
            
        Returns:
            Dict with extracted metadata: title, authors, year, venue, doi, abstract, etc.
        """
        logger.info(f"Extracting metadata from PDF: {filename}")
        
        metadata = {
            "title": "",
            "authors": [],
            "year": None,
            "venue": "",
            "doi": "",
            "abstract": "",
            "subject": "",
            "keywords": "",
            "citation_count": 0,
            "extraction_method": "none",
            "extraction_confidence": 0.0
        }
        
        try:
            # Phase 1: Extract basic PDF properties
            basic_metadata = self._extract_basic_pdf_properties(file_data)
            metadata.update(basic_metadata)
            
            # Phase 2: Extract text and search for DOI
            first_page_text = self._extract_first_page_text(file_data)
            doi = self._find_doi_in_text(first_page_text)
            
            if doi:
                logger.info(f"Found DOI in PDF: {doi}")
                # Phase 3: Query Crossref for authoritative metadata
                crossref_metadata = await self._query_crossref_api(doi)
                
                if crossref_metadata:
                    logger.info("Successfully retrieved metadata from Crossref")
                    metadata.update(crossref_metadata)
                    metadata["extraction_method"] = "crossref"
                    metadata["extraction_confidence"] = 0.95
                    return metadata
            
            # Phase 4: Enhanced text parsing if no DOI found
            if first_page_text:
                text_metadata = self._extract_metadata_from_text(first_page_text)
                metadata.update(text_metadata)
                metadata["extraction_method"] = "text_parsing"
                metadata["extraction_confidence"] = 0.6
            
            # Use basic PDF properties if available
            if metadata.get("title") or metadata.get("authors"):
                if metadata["extraction_method"] == "none":
                    metadata["extraction_method"] = "pdf_properties"
                    metadata["extraction_confidence"] = 0.7
            else:
                # Fallback to filename-based title
                metadata["title"] = self._clean_filename_for_title(filename)
                metadata["extraction_method"] = "filename"
                metadata["extraction_confidence"] = 0.3
            
            return metadata
            
        except Exception as e:
            logger.error(f"PDF metadata extraction failed: {str(e)}")
            metadata.update({
                "title": self._clean_filename_for_title(filename),
                "extraction_method": "error",
                "extraction_confidence": 0.1,
                "error": str(e)
            })
            return metadata
    
    def _extract_basic_pdf_properties(self, file_data: bytes) -> Dict[str, Any]:
        """Extract metadata from PDF document properties"""
        metadata = {}
        
        try:
            pdf_stream = BytesIO(file_data)
            pdf_reader = PyPDF2.PdfReader(pdf_stream)
            
            # Get document info
            if pdf_reader.metadata:
                info = pdf_reader.metadata
                
                # Extract title
                if '/Title' in info and info['/Title']:
                    metadata['title'] = str(info['/Title']).strip()
                
                # Extract author(s)
                if '/Author' in info and info['/Author']:
                    authors_str = str(info['/Author']).strip()
                    # Split authors by common separators
                    authors = self._parse_authors_string(authors_str)
                    metadata['authors'] = authors
                
                # Extract subject
                if '/Subject' in info and info['/Subject']:
                    metadata['subject'] = str(info['/Subject']).strip()
                
                # Extract keywords
                if '/Keywords' in info and info['/Keywords']:
                    metadata['keywords'] = str(info['/Keywords']).strip()
                
                # Extract creation date
                if '/CreationDate' in info and info['/CreationDate']:
                    try:
                        creation_date = str(info['/CreationDate'])
                        year = self._extract_year_from_date(creation_date)
                        if year:
                            metadata['year'] = year
                    except:
                        pass
            
            logger.info(f"Extracted basic PDF properties: {len(metadata)} fields")
            
        except Exception as e:
            logger.warning(f"Failed to extract basic PDF properties: {str(e)}")
        
        return metadata
    
    def _extract_first_page_text(self, file_data: bytes) -> str:
        """Extract text from first page of PDF"""
        try:
            pdf_stream = BytesIO(file_data)
            pdf_reader = PyPDF2.PdfReader(pdf_stream)
            
            if len(pdf_reader.pages) > 0:
                first_page = pdf_reader.pages[0]
                text = first_page.extract_text()
                logger.info(f"Extracted {len(text)} characters from first page")
                return text
                
        except Exception as e:
            logger.warning(f"Failed to extract text from PDF: {str(e)}")
        
        return ""
    
    def _find_doi_in_text(self, text: str) -> Optional[str]:
        """Find DOI pattern in text using comprehensive regex patterns"""
        if not text:
            return None
        
        # Multiple DOI patterns to catch different formats
        doi_patterns = [
            r'doi:\s*(10\.\d{4,}/[^\s\]]+)',  # doi: 10.1234/example
            r'DOI:\s*(10\.\d{4,}/[^\s\]]+)',  # DOI: 10.1234/example  
            r'https?://doi\.org/(10\.\d{4,}/[^\s\]]+)',  # https://doi.org/10.1234/example
            r'https?://dx\.doi\.org/(10\.\d{4,}/[^\s\]]+)',  # https://dx.doi.org/10.1234/example
            r'(10\.\d{4,}/[^\s\]]+)',  # Raw DOI pattern
        ]
        
        for pattern in doi_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                doi = match.group(1) if match.groups() else match.group(0)
                # Clean up DOI
                doi = doi.rstrip('.,;:)]')
                
                # Validate DOI format
                if self._is_valid_doi(doi):
                    return doi
        
        return None
    
    def _is_valid_doi(self, doi: str) -> bool:
        """Validate DOI format"""
        # Basic DOI validation
        doi_pattern = r'^10\.\d{4,}/[^\s]+$'
        return bool(re.match(doi_pattern, doi)) and len(doi) > 10
    
    async def _query_crossref_api(self, doi: str) -> Optional[Dict[str, Any]]:
        """Query Crossref API for comprehensive metadata"""
        try:
            url = f"{self.crossref_api_url}/{doi}"
            
            # Use aiohttp for async requests
            async with aiohttp.ClientSession(headers=self.session_headers) as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        work = data.get('message', {})
                        
                        # Extract comprehensive metadata
                        metadata = {}
                        
                        # Title
                        if 'title' in work and work['title']:
                            metadata['title'] = work['title'][0]
                        
                        # Authors
                        authors = []
                        if 'author' in work:
                            for author in work['author']:
                                given = author.get('given', '')
                                family = author.get('family', '')
                                if given and family:
                                    authors.append(f"{given} {family}")
                                elif family:
                                    authors.append(family)
                        metadata['authors'] = authors
                        
                        # Publication year
                        if 'published-print' in work:
                            date_parts = work['published-print'].get('date-parts', [[]])
                            if date_parts and date_parts[0]:
                                metadata['year'] = date_parts[0][0]
                        elif 'published-online' in work:
                            date_parts = work['published-online'].get('date-parts', [[]])
                            if date_parts and date_parts[0]:
                                metadata['year'] = date_parts[0][0]
                        
                        # Venue/Journal
                        if 'container-title' in work and work['container-title']:
                            metadata['venue'] = work['container-title'][0]
                        
                        # DOI
                        metadata['doi'] = doi
                        
                        # Abstract
                        if 'abstract' in work:
                            metadata['abstract'] = work['abstract']
                        
                        # Citation count
                        if 'is-referenced-by-count' in work:
                            metadata['citation_count'] = work['is-referenced-by-count']
                        
                        # Publisher
                        if 'publisher' in work:
                            metadata['publisher'] = work['publisher']
                        
                        # Subject/Keywords
                        if 'subject' in work:
                            metadata['keywords'] = ', '.join(work['subject'])
                        
                        logger.info(f"Successfully extracted metadata from Crossref for DOI: {doi}")
                        return metadata
                    else:
                        logger.warning(f"Crossref API returned status {response.status} for DOI: {doi}")
        
        except asyncio.TimeoutError:
            logger.warning(f"Crossref API timeout for DOI: {doi}")
        except Exception as e:
            logger.error(f"Crossref API query failed for DOI {doi}: {str(e)}")
        
        return None
    
    def _extract_metadata_from_text(self, text: str) -> Dict[str, Any]:
        """Extract metadata from PDF text using pattern matching"""
        metadata = {}
        
        if not text:
            return metadata
        
        # Extract potential title (first few lines, capitalized)
        lines = text.split('\n')[:10]  # First 10 lines
        for line in lines:
            line = line.strip()
            if len(line) > 20 and len(line) < 200:  # Reasonable title length
                # Check if line looks like a title (mixed case, not all caps)
                if line[0].isupper() and any(c.islower() for c in line):
                    if not metadata.get('title'):
                        metadata['title'] = line
                        break
        
        # Extract year patterns
        year_pattern = r'\b(19|20)\d{2}\b'
        years = re.findall(year_pattern, text)
        if years:
            # Use the most recent year found
            year_numbers = [int(y) for y in years if int(y) >= 1990 and int(y) <= datetime.now().year]
            if year_numbers:
                metadata['year'] = max(year_numbers)
        
        # Look for author patterns (names followed by affiliations or emails)
        author_patterns = [
            r'[A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)*',  # First Last [Middle]
        ]
        
        potential_authors = []
        for pattern in author_patterns:
            matches = re.findall(pattern, text[:1000])  # First 1000 chars
            potential_authors.extend(matches[:5])  # Max 5 authors
        
        if potential_authors:
            metadata['authors'] = potential_authors
        
        return metadata
    
    def _parse_authors_string(self, authors_str: str) -> List[str]:
        """Parse author string into list of individual authors"""
        if not authors_str:
            return []
        
        # Common separators for multiple authors
        separators = [';', ',', '&', ' and ', '\n']
        
        authors = [authors_str]  # Start with original string
        
        # Split by each separator
        for sep in separators:
            new_authors = []
            for author in authors:
                new_authors.extend([a.strip() for a in author.split(sep) if a.strip()])
            authors = new_authors
        
        # Clean up authors and filter reasonable names
        clean_authors = []
        for author in authors:
            author = author.strip()
            # Basic validation: has at least first and last name
            if len(author.split()) >= 2 and len(author) < 50:
                clean_authors.append(author)
        
        return clean_authors[:10]  # Limit to 10 authors
    
    def _extract_year_from_date(self, date_str: str) -> Optional[int]:
        """Extract year from PDF date string"""
        try:
            # PDF dates are often in format D:YYYYMMDDHHmmSSOHH'mm
            year_match = re.search(r'(\d{4})', date_str)
            if year_match:
                year = int(year_match.group(1))
                # Validate reasonable year range
                if 1900 <= year <= datetime.now().year:
                    return year
        except:
            pass
        
        return None
    
    def _clean_filename_for_title(self, filename: str) -> str:
        """Clean filename to create a reasonable title"""
        # Remove file extension
        title = filename.rsplit('.', 1)[0] if '.' in filename else filename
        
        # Replace underscores and hyphens with spaces
        title = title.replace('_', ' ').replace('-', ' ')
        
        # Remove common file prefixes
        prefixes_to_remove = ['paper', 'article', 'document', 'file']
        words = title.split()
        if words and words[0].lower() in prefixes_to_remove:
            words = words[1:]
        
        title = ' '.join(words)
        
        # Capitalize properly
        title = ' '.join(word.capitalize() for word in title.split())
        
        return title if title else filename


# Global instance
pdf_extractor = PDFMetadataExtractor()


# Convenience function for API usage
async def extract_pdf_metadata(file_data: bytes, filename: str) -> Dict[str, Any]:
    """
    Extract metadata from PDF file.
    
    Args:
        file_data: PDF file content as bytes
        filename: Original filename
        
    Returns:
        Dict with extracted metadata
    """
    return await pdf_extractor.extract_pdf_metadata(file_data, filename)