"""
Test script for intelligent PDF extraction service.
Demonstrates PyMuPDF4LLM with Gemini Vision fallback.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.services.pdf_extraction_service import PDFExtractionService
from src.utils.logger import get_logger

logger = get_logger(__name__)


def test_pdf_extraction(pdf_path: str):
    """
    Test PDF extraction on a single file.
    
    Args:
        pdf_path: Path to PDF file to test
    """
    pdf_file = Path(pdf_path)
    
    if not pdf_file.exists():
        logger.error(f"PDF file not found: {pdf_file}")
        return
    
    logger.info(f"Testing PDF extraction on: {pdf_file.name}")
    logger.info("-" * 80)
    
    # Initialize service
    extractor = PDFExtractionService()
    
    try:
        # Extract markdown
        markdown_text = extractor.extract(pdf_file)
        
        # Display results
        logger.info("\n" + "=" * 80)
        logger.info("EXTRACTION RESULTS")
        logger.info("=" * 80)
        logger.info(f"File: {pdf_file.name}")
        logger.info(f"Total characters: {len(markdown_text)}")
        logger.info(f"Total lines: {len(markdown_text.splitlines())}")
        logger.info("\n" + "-" * 80)
        logger.info("First 500 characters:")
        logger.info("-" * 80)
        print(markdown_text[:500])
        logger.info("\n" + "-" * 80)
        logger.info("Last 500 characters:")
        logger.info("-" * 80)
        print(markdown_text[-500:])
        logger.info("\n" + "=" * 80)
        
    except Exception as e:
        logger.error(f"Extraction failed: {str(e)}", exc_info=True)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test PDF extraction with intelligent fallback")
    parser.add_argument("pdf_path", help="Path to PDF file to test")
    
    args = parser.parse_args()
    
    test_pdf_extraction(args.pdf_path)


if __name__ == "__main__":
    main()
