"""
Test script for Haystack Ingestion Pipeline.
Tests single file ingestion with the pure Haystack pipeline.
"""

import asyncio
import logging
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipelines.haystack_ingestion_pipeline import HaystackIngestionPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_single_ingestion():
    """Test ingesting a single PDF file."""
    
    # Initialize pipeline
    logger.info("Initializing Haystack Ingestion Pipeline...")
    pipeline = HaystackIngestionPipeline()
    
    # Visualize pipeline structure
    logger.info("\n" + "="*60)
    logger.info("PIPELINE STRUCTURE:")
    logger.info("="*60)
    print(pipeline.visualize_pipeline())
    logger.info("="*60 + "\n")
    
    # Test file path (update this to your test PDF)
    test_file = Path("cases/sample.pdf")
    
    if not test_file.exists():
        logger.error(f"Test file not found: {test_file}")
        logger.info("Please update the test_file path in the script")
        return
    
    # Run ingestion
    logger.info(f"Ingesting file: {test_file.name}")
    result = await pipeline.ingest_single(test_file)
    
    # Display results
    logger.info("\n" + "="*60)
    logger.info("INGESTION RESULT:")
    logger.info("="*60)
    logger.info(f"Status: {result.status}")
    logger.info(f"Case ID: {result.case_id}")
    logger.info(f"Document ID: {result.document_id}")
    
    if result.metadata:
        logger.info(f"\nMetadata:")
        logger.info(f"  Title: {result.metadata.case_title}")
        logger.info(f"  Court: {result.metadata.court_name}")
        logger.info(f"  Date: {result.metadata.judgment_date}")
        logger.info(f"  Most Appropriate Section: {result.metadata.most_appropriate_section}")
        logger.info(f"  Sections Invoked: {result.metadata.sections_invoked}")
    
    if result.facts_summary:
        logger.info(f"\nFacts Summary (first 500 chars):")
        logger.info(result.facts_summary[:500] + "...")
    
    if result.error_message:
        logger.error(f"\nError: {result.error_message}")
    
    logger.info("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(test_single_ingestion())
