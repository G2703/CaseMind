"""
PDF Extraction Service with intelligent fallback strategy.
Uses PyMuPDF4LLM for primary extraction, Gemini Vision API for scanned documents.
"""

import logging
import os
from pathlib import Path
from typing import Optional, Tuple
import google.generativeai as genai

logger = logging.getLogger(__name__)

try:
    import pymupdf4llm
    PYMUPDF4LLM_AVAILABLE = True
except ImportError:
    PYMUPDF4LLM_AVAILABLE = False
    logger.warning("pymupdf4llm not available, will use fallback extraction")


class PDFExtractionService:
    """
    Service for intelligent PDF text extraction.
    
    Strategy:
    1. Primary: PyMuPDF4LLM (fast, works for digital text PDFs)
    2. Quality check: Evaluate if extracted text is sufficient
    3. Fallback: Gemini Vision API for scanned/image-based PDFs
    """
    
    # Thresholds for determining "insufficient text"
    MIN_CHARS_PER_PAGE = 50  # Minimum characters per page to consider valid
    MIN_TOTAL_CHARS = 100     # Minimum total characters
    
    def __init__(self, gemini_api_key: Optional[str] = None):
        """
        Initialize PDF extraction service.
        
        Args:
            gemini_api_key: Google Gemini API key (optional, will use env var if not provided)
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
        
        logger.info("PDFExtractionService initialized")
    
    def _extract_with_pymupdf4llm(self, pdf_path: Path) -> Tuple[str, int]:
        """
        Extract markdown from PDF using PyMuPDF4LLM.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Tuple of (markdown_text, page_count)
        """
        if not PYMUPDF4LLM_AVAILABLE:
            raise ImportError("pymupdf4llm is not installed")
        
        try:
            # Extract markdown using pymupdf4llm
            markdown_text = pymupdf4llm.to_markdown(str(pdf_path))
            
            # Get page count using PyMuPDF
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
        """
        Check if extracted text is sufficient quality.
        
        Args:
            text: Extracted text
            page_count: Number of pages in PDF
            
        Returns:
            True if text is sufficient, False if needs fallback
        """
        if not text or len(text.strip()) < self.MIN_TOTAL_CHARS:
            logger.warning(f"Text too short: {len(text)} chars (min: {self.MIN_TOTAL_CHARS})")
            return False
        
        # Check average characters per page
        chars_per_page = len(text) / max(page_count, 1)
        if chars_per_page < self.MIN_CHARS_PER_PAGE:
            logger.warning(f"Insufficient chars per page: {chars_per_page:.1f} (min: {self.MIN_CHARS_PER_PAGE})")
            return False
        
        # Check if mostly whitespace
        non_whitespace_ratio = len(text.strip()) / len(text)
        if non_whitespace_ratio < 0.3:
            logger.warning(f"Too much whitespace: {non_whitespace_ratio:.2%}")
            return False
        
        logger.info(f"Text quality sufficient: {len(text)} chars, {chars_per_page:.1f} chars/page")
        return True
    
    def _extract_with_gemini(self, pdf_path: Path) -> str:
        """
        Extract text from PDF using Gemini Vision API.
        Handles copyright/safety blocks gracefully.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Extracted markdown text
        """
        if not self.gemini_model:
            raise ValueError("Gemini API not configured - set GEMINI_API_KEY environment variable")
        
        try:
            import fitz  # PyMuPDF
            from google.generativeai.types import HarmCategory, HarmBlockThreshold
            
            # Configure safety settings to be less restrictive for legal documents
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
            
            # Open PDF and convert pages to images
            doc = fitz.open(pdf_path)
            page_count = len(doc)
            
            logger.info(f"Extracting {page_count} pages using Gemini Vision API...")
            
            all_text = []
            blocked_pages = []
            
            for page_num in range(page_count):
                page = doc[page_num]
                
                # Convert page to image (PNG format)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
                img_bytes = pix.tobytes("png")
                
                # Prepare image for Gemini
                from PIL import Image
                import io
                img = Image.open(io.BytesIO(img_bytes))
                
                # Call Gemini Vision API with safety settings
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
                    
                    # Check if response was blocked
                    if response.prompt_feedback.block_reason:
                        logger.warning(f"Page {page_num + 1} blocked: {response.prompt_feedback.block_reason}")
                        blocked_pages.append(page_num + 1)
                        all_text.append(f"# Page {page_num + 1}\n\n[Content blocked by Gemini API - block reason: {response.prompt_feedback.block_reason}]")
                        continue
                    
                    # Check if response has valid parts
                    if not response.parts:
                        finish_reason = response.candidates[0].finish_reason if response.candidates else "unknown"
                        logger.warning(f"Page {page_num + 1} returned no content (finish_reason: {finish_reason})")
                        
                        # Handle copyright block (finish_reason=4)
                        if finish_reason == 4 or "RECITATION" in str(finish_reason):
                            logger.info(f"Page {page_num + 1} blocked due to potential copyright - attempting OCR extraction...")
                            # For copyright blocks, just note it and continue
                            all_text.append(f"# Page {page_num + 1}\n\n[Legal document page - content detected as potentially copyrighted]")
                            blocked_pages.append(page_num + 1)
                        else:
                            all_text.append(f"# Page {page_num + 1}\n\n[No content extracted - finish_reason: {finish_reason}]")
                            blocked_pages.append(page_num + 1)
                        continue
                    
                    # Extract text successfully
                    page_text = response.text
                    all_text.append(f"# Page {page_num + 1}\n\n{page_text}")
                    logger.info(f"✓ Extracted page {page_num + 1}/{page_count}")
                    
                except Exception as page_error:
                    logger.error(f"Error extracting page {page_num + 1}: {str(page_error)}")
                    all_text.append(f"# Page {page_num + 1}\n\n[Extraction error: {str(page_error)}]")
                    blocked_pages.append(page_num + 1)
            
            doc.close()
            
            # Check if we got any meaningful content
            if len(blocked_pages) == page_count:
                raise Exception(f"All {page_count} pages were blocked or failed extraction. Gemini Vision cannot process this document.")
            
            markdown_text = "\n\n---\n\n".join(all_text)
            
            if blocked_pages:
                logger.warning(f"Gemini Vision: {len(blocked_pages)}/{page_count} pages blocked or failed: {blocked_pages}")
            
            logger.info(f"Gemini Vision extracted {len(markdown_text)} chars from {page_count} pages ({page_count - len(blocked_pages)} successful)")
            
            return markdown_text
            
        except Exception as e:
            logger.error(f"Gemini Vision extraction failed: {str(e)}")
            raise
    
    def extract(self, pdf_path: Path) -> str:
        """
        Extract markdown from PDF with intelligent fallback.
        
        Strategy:
        1. Try PyMuPDF4LLM extraction (fast, best formatting)
        2. Check if text is sufficient quality
        3. If insufficient, fallback to Gemini Vision API (OCR for scanned docs)
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Extracted markdown text
            
        Raises:
            Exception: If both extraction methods fail
        """
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        logger.info(f"Starting PDF extraction: {pdf_path.name}")
        
        # Stage 1: Try PyMuPDF4LLM
        try:
            if PYMUPDF4LLM_AVAILABLE:
                markdown_text, page_count = self._extract_with_pymupdf4llm(pdf_path)
                
                # Stage 2: Quality check
                if self._is_text_sufficient(markdown_text, page_count):
                    logger.info(f"✓ Primary extraction successful: {pdf_path.name}")
                    return markdown_text
                else:
                    logger.warning(f"Primary extraction insufficient, trying Gemini Vision fallback...")
            else:
                logger.warning("PyMuPDF4LLM not available, using Gemini Vision...")
                
        except Exception as e:
            logger.error(f"Primary extraction failed: {str(e)}, trying fallback...")
        
        # Stage 3: Fallback to Gemini Vision
        try:
            markdown_text = self._extract_with_gemini(pdf_path)
            logger.info(f"✓ Fallback extraction successful: {pdf_path.name}")
            return markdown_text
            
        except Exception as e:
            logger.error(f"All extraction methods failed for {pdf_path.name}: {str(e)}")
            raise Exception(f"Failed to extract PDF: {str(e)}")
