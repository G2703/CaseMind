"""
PDF document loader implementation using Adapter pattern.
"""

import logging
from pathlib import Path
import fitz  # PyMuPDF

from core.interfaces import IDocumentLoader
from core.exceptions import DocumentLoadError

logger = logging.getLogger(__name__)


class PDFLoader(IDocumentLoader):
    """
    PDF document loader using PyMuPDF.
    Adapts PyMuPDF functionality to IDocumentLoader interface.
    """
    
    def validate(self, file_path: Path) -> bool:
        """
        Validate if file can be loaded.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            True if valid, False otherwise
        """
        if not file_path.exists():
            logger.error(f"File does not exist: {file_path}")
            return False
        
        if not file_path.suffix.lower() == '.pdf':
            logger.error(f"File is not a PDF: {file_path}")
            return False
        
        return True
    
    def load(self, file_path: Path) -> str:
        """
        Load PDF and extract text content.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Extracted text content
            
        Raises:
            DocumentLoadError: If loading fails
        """
        if not self.validate(file_path):
            raise DocumentLoadError(f"Invalid PDF file: {file_path}")
        
        try:
            # Open PDF with PyMuPDF
            doc = fitz.open(file_path)
            
            # Extract text from all pages
            text_parts = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                text_parts.append(page.get_text())
            
            doc.close()
            
            # Join all pages
            raw_text = "\n\n".join(text_parts)
            
            # Clean text
            cleaned_text = self._clean_text(raw_text)
            
            logger.info(f"Loaded PDF: {file_path.name} ({len(cleaned_text)} characters)")
            return cleaned_text
            
        except Exception as e:
            logger.error(f"Failed to load PDF {file_path}: {e}")
            raise DocumentLoadError(f"PDF loading failed: {e}")
    
    def _clean_text(self, text: str) -> str:
        """
        Clean extracted text.
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        lines = [line.strip() for line in text.split('\n')]
        lines = [line for line in lines if line]
        
        # Join lines
        cleaned = '\n'.join(lines)
        
        # Remove excessive newlines
        while '\n\n\n' in cleaned:
            cleaned = cleaned.replace('\n\n\n', '\n\n')
        
        return cleaned.strip()
