"""
Stage 1: PDF to Markdown Converter
Haystack component that converts PDF files to markdown text.
"""

from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import logging
import os

from haystack import component, Document
import google.generativeai as genai

logger = logging.getLogger(__name__)

try:
    import pymupdf4llm
    PYMUPDF4LLM_AVAILABLE = True
except ImportError:
    PYMUPDF4LLM_AVAILABLE = False
    logger.warning("pymupdf4llm not available, will use fallback extraction")


@component
class PDFToMarkdownConverter:
    """
    Haystack component for intelligent PDF extraction.
    Uses PyMuPDF4LLM with Gemini Vision API fallback.
    
    Inputs:
        - file_paths (List[Path]): List of PDF file paths
    
    Outputs:
        - documents (List[Document]): Haystack documents with markdown content
    """
    
    # Thresholds for determining "insufficient text"
    MIN_CHARS_PER_PAGE = 50
    MIN_TOTAL_CHARS = 100
    
    def __init__(self, gemini_api_key: Optional[str] = None):
        """
        Initialize PDF converter.
        
        Args:
            gemini_api_key: Google Gemini API key (optional, will use env var)
        """
        self.gemini_api_key = gemini_api_key or os.getenv('GEMINI_API_KEY')
        
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.gemini_model = genai.GenerativeModel('gemini-2.5-flash')
            logger.info("Gemini Vision API configured for fallback extraction")
        else:
            self.gemini_model = None
            logger.warning("Gemini API key not found - fallback extraction unavailable")
        
        if not PYMUPDF4LLM_AVAILABLE:
            logger.warning("pymupdf4llm not installed - primary extraction unavailable")
        
        logger.info("PDFToMarkdownConverter initialized")
    
    def _extract_with_pymupdf4llm(self, pdf_path: Path) -> Tuple[str, int]:
        """Extract markdown from PDF using PyMuPDF4LLM."""
        if not PYMUPDF4LLM_AVAILABLE:
            raise ImportError("pymupdf4llm is not installed")
        
        try:
            markdown_text = pymupdf4llm.to_markdown(str(pdf_path))
            import fitz
            doc = fitz.open(pdf_path)
            page_count = len(doc)
            doc.close()
            logger.info(f"PyMuPDF4LLM extracted {len(markdown_text)} chars from {page_count} pages")
            return markdown_text, page_count
        except Exception as e:
            logger.error(f"PyMuPDF4LLM extraction failed: {str(e)}")
            raise
    
    def _is_text_sufficient(self, text: str, page_count: int) -> bool:
        """Check if extracted text is sufficient quality."""
        if not text or len(text.strip()) < self.MIN_TOTAL_CHARS:
            logger.warning(f"Text too short: {len(text)} chars (min: {self.MIN_TOTAL_CHARS})")
            return False
        
        chars_per_page = len(text) / max(page_count, 1)
        if chars_per_page < self.MIN_CHARS_PER_PAGE:
            logger.warning(f"Insufficient chars per page: {chars_per_page:.1f} (min: {self.MIN_CHARS_PER_PAGE})")
            return False
        
        non_whitespace_ratio = len(text.strip()) / len(text)
        if non_whitespace_ratio < 0.3:
            logger.warning(f"Too much whitespace: {non_whitespace_ratio:.2%}")
            return False
        
        logger.info(f"Text quality sufficient: {len(text)} chars, {chars_per_page:.1f} chars/page")
        return True
    
    def _extract_with_gemini(self, pdf_path: Path) -> str:
        """Extract text from PDF using Gemini Vision API."""
        if not self.gemini_model:
            raise ValueError("Gemini API not configured - set GEMINI_API_KEY environment variable")
        
        try:
            import fitz
            from google.generativeai.types import HarmCategory, HarmBlockThreshold
            from PIL import Image
            import io
            
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
            
            doc = fitz.open(pdf_path)
            page_count = len(doc)
            logger.info(f"Extracting {page_count} pages using Gemini Vision API...")
            
            all_text = []
            blocked_pages = []
            
            for page_num in range(page_count):
                page = doc[page_num]
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img_bytes = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_bytes))
                
                prompt = """You are an OCR system extracting text from a legal court document.
Extract all visible text from this page exactly as it appears.
Preserve structure, headings, case numbers, dates, names, and all legal content.
Format the output as markdown.
Do not add any commentary or analysis - only extract the text."""
                
                try:
                    response = self.gemini_model.generate_content(
                        [prompt, img],
                        safety_settings=safety_settings
                    )
                    
                    if response.prompt_feedback.block_reason:
                        logger.warning(f"Page {page_num + 1} blocked: {response.prompt_feedback.block_reason}")
                        blocked_pages.append(page_num + 1)
                        all_text.append(f"# Page {page_num + 1}\n\n[Content blocked by Gemini API]")
                        continue
                    
                    if not response.parts:
                        finish_reason = response.candidates[0].finish_reason if response.candidates else "unknown"
                        logger.warning(f"Page {page_num + 1} returned no content (finish_reason: {finish_reason})")
                        all_text.append(f"# Page {page_num + 1}\n\n[No content extracted]")
                        blocked_pages.append(page_num + 1)
                        continue
                    
                    page_text = response.text
                    all_text.append(f"# Page {page_num + 1}\n\n{page_text}")
                    logger.info(f"✓ Extracted page {page_num + 1}/{page_count}")
                    
                except Exception as page_error:
                    logger.error(f"Error extracting page {page_num + 1}: {str(page_error)}")
                    all_text.append(f"# Page {page_num + 1}\n\n[Extraction error: {str(page_error)}]")
                    blocked_pages.append(page_num + 1)
            
            doc.close()
            
            if len(blocked_pages) == page_count:
                raise Exception(f"All {page_count} pages were blocked or failed extraction")
            
            markdown_text = "\n\n---\n\n".join(all_text)
            
            if blocked_pages:
                logger.warning(f"Gemini Vision: {len(blocked_pages)}/{page_count} pages blocked or failed")
            
            logger.info(f"Gemini Vision extracted {len(markdown_text)} chars from {page_count} pages")
            return markdown_text
            
        except Exception as e:
            logger.error(f"Gemini Vision extraction failed: {str(e)}")
            raise
    
    def _extract_pdf(self, pdf_path: Path) -> str:
        """Extract markdown from PDF with intelligent fallback."""
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        logger.info(f"Starting PDF extraction: {pdf_path.name}")
        
        # Try PyMuPDF4LLM first
        try:
            if PYMUPDF4LLM_AVAILABLE:
                markdown_text, page_count = self._extract_with_pymupdf4llm(pdf_path)
                
                if self._is_text_sufficient(markdown_text, page_count):
                    logger.info(f"✓ Primary extraction successful: {pdf_path.name}")
                    return markdown_text
                else:
                    logger.warning(f"Primary extraction insufficient, trying Gemini Vision fallback...")
            else:
                logger.warning("PyMuPDF4LLM not available, using Gemini Vision...")
        except Exception as e:
            logger.error(f"Primary extraction failed: {str(e)}, trying fallback...")
        
        # Fallback to Gemini Vision
        try:
            markdown_text = self._extract_with_gemini(pdf_path)
            logger.info(f"✓ Fallback extraction successful: {pdf_path.name}")
            return markdown_text
        except Exception as e:
            logger.error(f"All extraction methods failed for {pdf_path.name}: {str(e)}")
            raise Exception(f"Failed to extract PDF: {str(e)}")
    
    @component.output_types(documents=List[Document])
    def run(self, file_paths: List[Path]) -> Dict[str, Any]:
        """
        Convert PDFs to markdown.
        
        Args:
            file_paths: List of PDF file paths
            
        Returns:
            Dictionary with 'documents' key containing List[Document]
        """
        documents = []
        
        for file_path in file_paths:
            file_path = Path(file_path)
            logger.info(f"Converting PDF: {file_path.name}")
            
            try:
                # Extract markdown
                markdown_text = self._extract_pdf(file_path)
                
                # Create Haystack Document
                doc = Document(
                    content=markdown_text,
                    meta={
                        "original_filename": file_path.name,
                        "file_path": str(file_path),
                        "source": "pdf_extraction"
                    }
                )
                documents.append(doc)
                logger.info(f"✓ Converted {file_path.name}: {len(markdown_text)} chars")
                
            except Exception as e:
                logger.error(f"Failed to convert {file_path.name}: {e}")
                # Create error document
                doc = Document(
                    content="",
                    meta={
                        "original_filename": file_path.name,
                        "file_path": str(file_path),
                        "error": str(e)
                    }
                )
                documents.append(doc)
        
        return {"documents": documents}
