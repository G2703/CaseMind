"""
Document Content Extraction
Handles raw content extraction from PDFs using various strategies (Gemini, PyMuPDF, Mistral)
"""

import os
import re
import asyncio
import base64
import logging
from pathlib import Path
from abc import ABC, abstractmethod
from typing import List, Tuple
import fitz
import google.generativeai as genai
try:
    from mistralai import Mistral
    from mistralai import DocumentURLChunk
    from mistralai.models import OCRResponse
    MISTRAL_AVAILABLE = True
except ImportError:
    MISTRAL_AVAILABLE = False
from dotenv import load_dotenv
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Any

# Define ImageData dataclass since backend.models.schemas is not available
@dataclass
class ImageData:
    """Represents an extracted image from a PDF document."""
    id: str
    base64_data: str
    page_number: int
    description: Optional[str] = None
    equipment_parts: list = field(default_factory=list)
    image_type: Optional[str] = None

import argparse
import os
import asyncio

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


# Abstract Strategy Interface for Content Extraction
class DocumentContentExtractionStrategy(ABC):
    """Abstract base class defining the interface for document content extraction strategies."""

    @abstractmethod
    async def extract(self, file_path: str) -> Tuple[str, List[ImageData]]:
        """Extract raw content from a document file."""
        pass

    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get the name of the extraction strategy"""
        pass

    @abstractmethod
    async def _process_single_page_async(
        self, page_pdf_data: bytes, page_num: int
    ) -> str:
        """Process a single page and return markdown content.

        Args:
            page_pdf_data: PDF data for a single page
            page_num: Page number (1-indexed)

        Returns:
            Processed markdown content for the page
        """
        pass

    async def _process_pages_batch_async(
        self,
        page_data: List[bytes],
        max_concurrent: int = 8,
        batch_size: int = 20,
    ) -> List[str]:
        """Process pages in batches with controlled concurrency.

        Args:
            page_data: List of PDF page data
            max_concurrent: Maximum concurrent API calls
            batch_size: Number of pages to process per batch

        Returns:
            List of processed page content in correct order
        """
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)

        # Process pages in batches with controlled concurrency
        all_content = []
        total_pages = len(page_data)

        for batch_start in range(0, total_pages, batch_size):
            batch_end = min(batch_start + batch_size, total_pages)
            batch = page_data[batch_start:batch_end]

            logger.info(
                f"Processing batch: pages {batch_start + 1}-{batch_end} of {total_pages}"
            )

            # Create async tasks for this batch with semaphore control
            async def process_page_with_semaphore(page_pdf_data, page_num):
                async with semaphore:
                    try:
                        content = await self._process_single_page_async(
                            page_pdf_data, page_num + 1
                        )
                        return f"## Page {page_num + 1}\n\n{content}"

                    except Exception as e:
                        logger.error(f"Failed to process page {page_num + 1}: {e}")
                        return f"## Page {page_num + 1}\n\n[Error processing page: {str(e)}]"

            # Create tasks for this batch - preserves order
            tasks = [
                process_page_with_semaphore(page_pdf_data, batch_start + j)
                for j, page_pdf_data in enumerate(batch)
            ]

            # Wait for batch completion - results maintain order
            batch_results = await asyncio.gather(*tasks)
            all_content.extend(batch_results)
            
            # Add delay between batches to avoid rate limits (for Gemini)
            if batch_end < total_pages:
                logger.info("Waiting 10 seconds before next batch to avoid rate limits...")
                await asyncio.sleep(10)

        return all_content

    def _post_process_combined_content(self, all_content: List[str]) -> str:
        """Clean and normalize page content before combining."""

        processed_pages = []

        for page_content in all_content:
            # Remove markdown code blocks artifacts
            cleaned = re.sub(r"```markdown\s*", "", page_content)
            cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.MULTILINE)

            # Normalize header levels (make main headers consistent)
            cleaned = re.sub(r"^# ", "## ", cleaned, flags=re.MULTILINE)

            # Remove orphaned page numbers
            cleaned = re.sub(r"^\s*\d+\s*$", "", cleaned, flags=re.MULTILINE)

            # Clean extra whitespace
            cleaned = re.sub(r"\n\s*\n\s*\n", "\n\n", cleaned)

            processed_pages.append(cleaned)

        return "\n\n".join(processed_pages)


# Concrete Strategy: PyMuPDF
class PyMuPDFContentExtractor(DocumentContentExtractionStrategy):
    """Content extraction strategy using PyMuPDF for fast text extraction."""

    def __init__(self):
        self.model_name = "pymupdf"

    async def extract(self, file_path: str) -> Tuple[str, List[ImageData]]:
        """Extract content using PyMuPDF - text only, no images"""
        logger.info(f"Extracting content from {file_path} using PyMuPDF")

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        markdown_content = await loop.run_in_executor(
            None, self._extract_text_with_fitz, file_path
        )

        # PyMuPDF doesn't extract images with base64, so return empty list
        images = []

        logger.info(f"Extracted {len(markdown_content)} characters using PyMuPDF")
        return markdown_content, images

    def _extract_text_with_fitz(self, file_path: str) -> str:
        """Extract text using fitz directly"""
        doc = fitz.open(file_path)
        text_parts = []

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()
            if text.strip():  # Only add non-empty pages
                text_parts.append(f"## Page {page_num + 1}\n\n{text}")

        doc.close()
        return "\n\n".join(text_parts)

    def get_strategy_name(self) -> str:
        return "pymupdf"

    async def _process_single_page_async(
        self, page_pdf_data: bytes, page_num: int
    ) -> str:
        """PyMuPDF doesn't use page-by-page processing, so this method is not implemented"""
        raise NotImplementedError(
            "PyMuPDF processes all pages at once, not page-by-page"
        )


# Concrete Strategy: Gemini
class GeminiContentExtractor(DocumentContentExtractionStrategy):
    """Content extraction strategy using Gemini API with page-by-page processing."""

    def __init__(
        self,
        model_name: str = "gemini-2.5-flash",
        max_concurrent: int = 4,  # Reduced to avoid rate limits
        batch_size: int = 20,  # Reduced batch size
    ):
        self.model_name = model_name
        self.max_concurrent = max_concurrent
        self.batch_size = batch_size

        if not os.getenv("GEMINI_API_KEY"):
            raise ValueError("GEMINI_API_KEY not found in environment variables")

        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.client = genai.GenerativeModel(self.model_name)

    async def extract(self, file_path: str, max_pages: Optional[int] = None, page_range: Optional[Tuple[int, int]] = None) -> Tuple[str, List[ImageData]]:
        """Extract content using Gemini API with batched async processing"""
        logger.info(
            f"Extracting content from {file_path} using Gemini API (batched async, batch_size={self.batch_size}, max_concurrent={self.max_concurrent})"
        )

        loop = asyncio.get_event_loop()

        # Get page data and extract images in a single pass (optimization)
        page_data, images = await loop.run_in_executor(
            None, self._split_pdf_and_extract_images, file_path, max_pages, page_range
        )

        # Process pages using shared batched async method
        all_content = await self._process_pages_batch_async(
            page_data, self.max_concurrent, self.batch_size
        )

        # Post-process and combine content using shared method
        combined_content = self._post_process_combined_content(all_content)

        logger.info(
            f"Extracted {len(combined_content)} characters from {len(all_content)} pages and {len(images)} images"
        )
        return combined_content, images

    def _split_pdf_and_extract_images(
        self, file_path: str, max_pages: Optional[int] = None, page_range: Optional[Tuple[int, int]] = None
    ) -> Tuple[List[bytes], List[ImageData]]:
        """Split PDF into pages and extract images in a single pass for efficiency"""
        doc = fitz.open(file_path)
        page_data_list = []
        all_images = []

        # Determine number of pages to process
        total_pages = len(doc)
        
        if page_range:
            from_page, to_page = page_range
            # Convert to 0-indexed and validate
            start_idx = from_page - 1
            end_idx = min(to_page, total_pages)  # to_page is inclusive, so we use it directly with range
            if start_idx >= total_pages:
                logger.warning(f"Start page {from_page} exceeds total pages {total_pages}")
                doc.close()
                return page_data_list, all_images
            logger.info(f"Processing pages {from_page}-{end_idx} of {total_pages} pages")
        elif max_pages:
            start_idx = 0
            end_idx = min(max_pages, total_pages)
            logger.info(f"Processing first {end_idx} of {total_pages} pages")
        else:
            start_idx = 0
            end_idx = total_pages
            logger.info(f"Processing all {total_pages} pages")

        for page_num in range(start_idx, end_idx):
            # Split: Create a new PDF with just this page
            single_page_doc = fitz.open()  # Create empty PDF
            single_page_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
            page_pdf_data = single_page_doc.tobytes()
            page_data_list.append(page_pdf_data)
            single_page_doc.close()

            # Extract images from the same page
            page = doc.load_page(page_num)
            image_list = page.get_images()

            for img_index, img in enumerate(image_list):
                try:
                    # Get image data
                    xref = img[0]
                    pix = fitz.Pixmap(doc, xref)

                    # Convert to PNG if not already
                    if pix.n - pix.alpha < 4:  # GRAY or RGB
                        img_data = pix.tobytes("png")
                    else:  # CMYK: convert to RGB first
                        pix1 = fitz.Pixmap(fitz.csRGB, pix)
                        img_data = pix1.tobytes("png")
                        pix1 = None

                    # Encode to base64
                    img_base64 = base64.b64encode(img_data).decode()

                    # Create ImageData object
                    image_data = ImageData(
                        id=f"page_{page_num + 1}_img_{img_index + 1}",
                        base64_data=img_base64,
                        page_number=page_num + 1,
                        description=None,  # Will be filled by image analyzer
                        equipment_parts=[],
                        image_type=None,
                    )
                    all_images.append(image_data)

                    pix = None  # Free memory

                except Exception as e:
                    logger.warning(
                        f"Failed to extract image {img_index} from page {page_num + 1}: {e}"
                    )
                    continue

        doc.close()
        logger.info(
            f"Split PDF into {len(page_data_list)} pages and extracted {len(all_images)} images"
        )
        return page_data_list, all_images

    def _clean_extraction_artifacts(self, content: str) -> str:
        """Clean up common extraction artifacts"""

        # Remove excessive repetition of any phrase (more than 3 times)
        lines = content.split("\n")
        cleaned_lines = []
        line_counts = {}

        for line in lines:
            line = line.strip()
            if not line:
                cleaned_lines.append("")
                continue

            line_counts[line] = line_counts.get(line, 0) + 1

            # Only add line if it hasn't appeared too many times
            if line_counts[line] <= 3:
                cleaned_lines.append(line)
            elif line_counts[line] == 4:
                cleaned_lines.append("[Content repeated - truncated]")

        return "\n".join(cleaned_lines)

    async def _call_gemini_api_for_page(self, page_pdf_data: bytes, page_num: int):
        """Process a single page with Gemini API with retry logic"""
        page_prompt = f"""
        **Role:** You are an expert OCR and document transcription service specializing in Indian legal documents.

        **Task:** Extract ALL content from this single page (Page {page_num}) of a legal document. The document may be a court judgment, police report (like a Charge Sheet), or other official legal filing. It may contain both printed and handwritten text, as well as stamps and signatures.

        **Instructions:**

        1.  **Full Extraction:** Transcribe EVERYTHING visible on the page. Do NOT summarize, interpret, or omit any content. This includes:
            *   Headers, footers, and page numbers.
            *   All paragraphs, lists, and titles.
            *   Content inside tables.
            *   Text from stamps or seals.
            *   Handwritten annotations or notes.
            *   If text is in format of form fields (e.g., "Name: __________"), then only retrieve the fields and the values filled in. DO NOT retrieve the underscores or dots or lines meant for filling.

        2.  **Formatting:** Format the output in clean, well-structured Markdown.
            *   Use appropriate heading levels (`##`, `###`) for titles and sections.
            *   Preserve paragraphs and line breaks as they appear in the original document.
            *   Recreate tables using Markdown table syntax (`|`). Ensure all rows and columns are accurately transcribed.
            *   Use bullet points (`-`) or numbered lists (`1.`) for lists.

        3.  **Special Elements:**
            *   If a signature is present, represent it as `[Signature]`.
            *   If a stamp or seal is present, transcribe the text within it and enclose it in brackets, e.g., `[Stamp: Certified True Copy]`.
            *   If some text is illegible, mark it as `[Illegible]`.

        4.  **Language:** The document may contain multiple languages (e.g., English and Marathi). Transcribe all text in its original language. Do not translate.

        **Objective:** The final output should be a complete and accurate Markdown representation of the page, preserving its structure and content as closely as possible.
        """

        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.client.generate_content(
                        contents=[
                            {
                                "parts": [
                                    {
                                        "inline_data": {
                                            "mime_type": "application/pdf",
                                            "data": page_pdf_data,
                                        }
                                    },
                                    {"text": page_prompt},
                                ]
                            }
                        ],
                        generation_config=genai.GenerationConfig(
                            temperature=0.1,
                            max_output_tokens=4000,
                        ),
                    ),
                )
                return response
                
            except Exception as e:
                error_str = str(e)
                # Check if it's a rate limit error
                if "429" in error_str or "quota" in error_str.lower():
                    if attempt < max_retries - 1:
                        # Extract retry delay from error message if available
                        import re
                        delay_match = re.search(r'retry in ([0-9.]+)s', error_str)
                        if delay_match:
                            retry_delay = float(delay_match.group(1)) + 1  # Add 1 second buffer
                        else:
                            retry_delay = retry_delay * 2  # Exponential backoff
                        
                        logger.warning(f"Rate limit hit for page {page_num}, retrying in {retry_delay:.1f}s (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(retry_delay)
                        continue
                # Re-raise if not rate limit or max retries exceeded
                raise

    def get_strategy_name(self) -> str:
        return "gemini"

    async def _process_single_page_async(
        self, page_pdf_data: bytes, page_num: int
    ) -> str:
        """Process a single page with Gemini API"""
        try:
            response = await self._call_gemini_api_for_page(page_pdf_data, page_num)

            # Check if response has valid content
            if response and hasattr(response, 'text'):
                try:
                    text = response.text
                    if text and text.strip():
                        return self._clean_extraction_artifacts(text)
                except (ValueError, AttributeError) as e:
                    # Handle cases where response.text raises an error
                    logger.warning(f"Could not extract text from page {page_num}: {e}")
                    
                    # Try to get content from candidates if available
                    if hasattr(response, 'candidates') and response.candidates:
                        candidate = response.candidates[0]
                        if hasattr(candidate, 'content') and candidate.content:
                            parts_text = []
                            for part in candidate.content.parts:
                                if hasattr(part, 'text'):
                                    parts_text.append(part.text)
                            if parts_text:
                                return self._clean_extraction_artifacts(''.join(parts_text))
                    
                    # Check finish reason
                    finish_reason = getattr(candidate, 'finish_reason', None) if 'candidate' in locals() else None
                    if finish_reason == 1:
                        return "[Content blocked by safety filters - STOP sequence]"
                    elif finish_reason == 2:
                        return "[Content blocked by safety filters - MAX_TOKENS]"
                    elif finish_reason == 3:
                        return "[Content blocked by safety filters - SAFETY]"
                    elif finish_reason == 4:
                        return "[Content blocked by safety filters - RECITATION]"
                    else:
                        return f"[No valid content extracted - finish_reason: {finish_reason}]"
            
            logger.warning(f"No content extracted from page {page_num}")
            return "[No content extracted]"
            
        except Exception as e:
            logger.error(f"Error processing page {page_num}: {e}")
            return f"[Error processing page: {str(e)}]"


# Concrete Strategy: Mistral
class MistralContentExtractor(DocumentContentExtractionStrategy):
    """Content extraction strategy using Mistral API with OCR capabilities."""

    def __init__(self, task="ocr", model_name: str = "mistral-large-2"):
        if not MISTRAL_AVAILABLE:
            raise ImportError("mistralai package is not installed. Install it with: pip install mistralai")
        
        self.task = task
        self.model_name = model_name
        if not os.getenv("MISTRAL_API_KEY"):
            raise ValueError("MISTRAL_API_KEY not found in environment variables")

        self.client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))

    async def extract(self, file_path: str) -> Tuple[str, List[ImageData]]:
        """Extract content using Mistral OCR API with image extraction"""
        logger.info(f"Extracting content from {file_path} using Mistral OCR")

        file_obj = Path(file_path)

        # Run API calls in thread pool
        loop = asyncio.get_event_loop()

        # Upload file
        uploaded_file = await loop.run_in_executor(None, self._upload_file, file_obj)

        # Get signed URL
        signed_url = await loop.run_in_executor(
            None, self._get_signed_url, uploaded_file.id
        )

        # Process with OCR
        pdf_response = await loop.run_in_executor(
            None, self._process_ocr, signed_url.url
        )

        # Extract markdown and images
        markdown_content, images = self._process_ocr_response(pdf_response)

        logger.info(
            f"Extracted {len(markdown_content)} characters and {len(images)} images using Mistral"
        )
        return markdown_content, images

    def _upload_file(self, file_obj: Path):
        """Upload file to Mistral"""
        return self.client.files.upload(
            file={
                "file_name": file_obj.stem,
                "content": file_obj.read_bytes(),
            },
            purpose=self.task,
        )

    def _get_signed_url(self, file_id: str):
        """Get signed URL for uploaded file"""
        return self.client.files.get_signed_url(file_id=file_id, expiry=1)

    def _process_ocr(self, signed_url: str):
        """Process document with OCR"""
        return self.client.ocr.process(
            document=DocumentURLChunk(document_url=signed_url),
            model=self.model_name,
            include_image_base64=True,
        )

    def _process_ocr_response(
        self, ocr_response: Any  # OCRResponse type when mistralai is installed
    ) -> Tuple[str, List[ImageData]]:
        """Process OCR response to extract markdown and images"""
        page_contents = []
        all_images = []

        for page_idx, page in enumerate(ocr_response.pages):
            # Extract images from this page
            page_images = []
            for img in page.images:
                image_data = ImageData(
                    id=img.id,
                    base64_data=img.image_base64,
                    page_number=page_idx + 1,
                    description=None,  # Will be filled by image analyzer
                    equipment_parts=[],
                    image_type=None,
                )
                page_images.append(image_data)
                all_images.append(image_data)

            # Replace image references in markdown
            page_markdown = page.markdown
            for img in page.images:
                # Replace base64 with image reference
                page_markdown = page_markdown.replace(
                    f"![{img.id}]({img.id})",
                    f"![{img.id}](data:image/png;base64,{img.image_base64})",
                )

            # Format as page content for post-processing
            page_contents.append(f"## Page {page_idx + 1}\n\n{page_markdown}")

        # Use shared post-processing for better markdown cleanup
        combined_markdown = self._post_process_combined_content(page_contents)
        return combined_markdown, all_images

    def get_strategy_name(self) -> str:
        return "mistral"

    async def _process_single_page_async(
        self, page_pdf_data: bytes, page_num: int
    ) -> str:
        """Mistral processes entire documents at once via OCR API, not page-by-page"""
        raise NotImplementedError(
            "Mistral processes entire documents at once, not page-by-page"
        )


# Main function
def main():
    parser = argparse.ArgumentParser(description="Extract PDF (image format) to Markdown using Gemini")
    parser.add_argument("pdf_path", type=str, help="Path to the PDF file to extract")
    parser.add_argument("--output", type=str, default=None, help="Optional output markdown file path")
    parser.add_argument("--pages", type=int, default=None, help="Number of pages to convert from start (default: all pages)")
    parser.add_argument("--range", type=str, default=None, help="Page range to convert in format 'from-to' (e.g., '5-10'), both inclusive")
    args = parser.parse_args()

    # Validate that --pages and --range are not used together
    if args.pages and args.range:
        parser.error("Cannot use both --pages and --range arguments together")

    pdf_path = args.pdf_path
    output_path = args.output

    # Default output path: cases/<pdf_basename>.md
    if output_path is None:
        pdf_basename = os.path.splitext(os.path.basename(pdf_path))[0]
        output_path = os.path.join("cases", f"{pdf_basename}.md")

    # Parse page range if provided
    page_range = None
    if args.range:
        try:
            from_page, to_page = map(int, args.range.split('-'))
            if from_page < 1 or to_page < from_page:
                parser.error("Invalid page range. Format: 'from-to' where from >= 1 and to >= from")
            page_range = (from_page, to_page)
        except ValueError:
            parser.error("Invalid page range format. Use 'from-to' (e.g., '5-10')")

    # Run extraction using Gemini
    extractor = GeminiContentExtractor()

    async def run_extraction():
        markdown_content, images = await extractor.extract(pdf_path, max_pages=args.pages, page_range=page_range)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        print(f"Extraction complete. Markdown saved to: {output_path}")

    # Run the async extraction
    asyncio.run(run_extraction())


if __name__ == "__main__":
    main()
