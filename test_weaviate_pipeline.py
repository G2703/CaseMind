"""
Test script for Weaviate ingestion pipeline.
Tests the complete flow with a sample PDF file.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.config import Config
from src.pipelines.weaviate_ingestion_pipeline import WeaviateIngestionPipeline
from src.infrastructure.weaviate_client import WeaviateClient
from src.utils.logger import get_logger

logger = get_logger(__name__)


def test_single_file_ingestion():
    """Test ingesting a single PDF file."""
    logger.info("=" * 70)
    logger.info("TEST: Single File Ingestion")
    logger.info("=" * 70)
    
    # Find a test PDF
    cases_dir = Path("cases/input_files")
    if not cases_dir.exists():
        logger.error(f"Cases directory not found: {cases_dir}")
        return False
    
    # Get first PDF file
    pdf_files = list(cases_dir.glob("*.pdf"))
    if not pdf_files:
        logger.error("No PDF files found in cases/input_files")
        return False
    
    test_file = pdf_files[0]
    logger.info(f"Test file: {test_file.name}")
    
    # Initialize pipeline
    pipeline = WeaviateIngestionPipeline()
    
    # Ingest file
    result = pipeline.ingest_single(test_file)
    
    # Check result
    if result.status == "success":
        logger.info(f"✓ Ingestion successful!")
        logger.info(f"  File ID: {result.file_id}")
        logger.info(f"  MD Hash: {result.md_hash[:16]}...")
        logger.info(f"  Sections: {result.sections_count}")
        logger.info(f"  Chunks: {result.chunks_count}")
        
        # Verify in Weaviate
        counts = pipeline.verify_ingestion(result.file_id)
        logger.info(f"\nWeaviate verification:")
        logger.info(f"  CaseDocuments: {counts['documents']}")
        logger.info(f"  CaseMetadata: {counts['metadata']}")
        logger.info(f"  CaseSections: {counts['sections']}")
        logger.info(f"  CaseChunks: {counts['chunks']}")
        
        # Expected ratio: 1:1:9:N
        if counts['documents'] == 1 and counts['metadata'] == 1:
            logger.info(f"✓ Document and metadata counts correct")
        else:
            logger.error(f"✗ Unexpected document/metadata counts")
            return False
        
        if counts['sections'] == result.sections_count:
            logger.info(f"✓ Sections count matches")
        else:
            logger.warning(f"⚠ Sections count mismatch: expected {result.sections_count}, got {counts['sections']}")
        
        if counts['chunks'] == result.chunks_count:
            logger.info(f"✓ Chunks count matches")
        else:
            logger.warning(f"⚠ Chunks count mismatch: expected {result.chunks_count}, got {counts['chunks']}")
        
        # Test metadata extraction
        if result.metadata:
            logger.info(f"\nExtracted metadata:")
            logger.info(f"  Case Number: {result.metadata.case_number}")
            logger.info(f"  Case Title: {result.metadata.case_title}")
            logger.info(f"  Court: {result.metadata.court_name}")
            logger.info(f"  Date: {result.metadata.judgment_date}")
            logger.info(f"  Sections Invoked: {result.metadata.sections_invoked}")
        
        pipeline.close()
        return True
        
    else:
        logger.error(f"✗ Ingestion failed: {result.message}")
        pipeline.close()
        return False


def test_duplicate_detection():
    """Test that duplicate files are properly detected."""
    logger.info("\n" + "=" * 70)
    logger.info("TEST: Duplicate Detection")
    logger.info("=" * 70)
    
    # Get same file again
    cases_dir = Path("cases/input_files")
    pdf_files = list(cases_dir.glob("*.pdf"))
    if not pdf_files:
        logger.error("No PDF files found")
        return False
    
    test_file = pdf_files[0]
    logger.info(f"Re-ingesting file: {test_file.name}")
    
    # Initialize pipeline
    pipeline = WeaviateIngestionPipeline()
    
    # Ingest same file again
    result = pipeline.ingest_single(test_file)
    
    if result.status == "skipped":
        logger.info(f"✓ Duplicate correctly detected and skipped")
        logger.info(f"  Message: {result.message}")
        pipeline.close()
        return True
    else:
        logger.error(f"✗ Duplicate not detected! Status: {result.status}")
        pipeline.close()
        return False


def test_vector_embeddings():
    """Test that vector embeddings are properly generated and stored."""
    logger.info("\n" + "=" * 70)
    logger.info("TEST: Vector Embeddings")
    logger.info("=" * 70)
    
    config = Config()
    client_wrapper = WeaviateClient(config)
    client = client_wrapper.client
    
    # Query a section with vector
    sections_collection = client.collections.get("CaseSections")
    result = sections_collection.query.fetch_objects(
        limit=1,
        include_vector=True
    )
    
    if not result.objects:
        logger.warning("No sections found in database")
        client_wrapper.close()
        return False
    
    section = result.objects[0]
    vector = section.vector
    
    # Check vector properties
    if vector is None:
        logger.error("✗ Section has no vector!")
        client_wrapper.close()
        return False
    
    vector_dim = len(vector["default"]) if isinstance(vector, dict) else len(vector)
    logger.info(f"✓ Vector dimension: {vector_dim}")
    
    if vector_dim != 768:
        logger.error(f"✗ Unexpected vector dimension: {vector_dim} (expected 768)")
        client_wrapper.close()
        return False
    
    # Check L2 normalization (vector magnitude should be ~1.0)
    import math
    vector_data = vector["default"] if isinstance(vector, dict) else vector
    magnitude = math.sqrt(sum(x*x for x in vector_data))
    logger.info(f"✓ Vector magnitude: {magnitude:.6f} (should be ~1.0 for L2 normalized)")
    
    if abs(magnitude - 1.0) > 0.01:
        logger.warning(f"⚠ Vector may not be properly normalized")
    else:
        logger.info(f"✓ Vector is properly L2 normalized")
    
    # Test semantic search
    logger.info("\nTesting semantic search...")
    query_result = sections_collection.query.near_text(
        query="what are the facts of this case",
        limit=3
    )
    
    logger.info(f"✓ Found {len(query_result.objects)} similar sections")
    for i, obj in enumerate(query_result.objects, 1):
        section_name = obj.properties.get("section_name", "unknown")
        text_preview = obj.properties.get("text", "")[:100]
        logger.info(f"  {i}. Section: {section_name}")
        logger.info(f"     Preview: {text_preview}...")
    
    client_wrapper.close()
    return True


def test_batch_ingestion():
    """Test batch ingestion of multiple files."""
    logger.info("\n" + "=" * 70)
    logger.info("TEST: Batch Ingestion")
    logger.info("=" * 70)
    
    # Get multiple test files
    cases_dir = Path("cases/input_files")
    pdf_files = list(cases_dir.glob("*.pdf"))[:3]  # Test with 3 files
    
    if len(pdf_files) < 2:
        logger.warning("Not enough PDF files for batch test (need at least 2)")
        return False
    
    logger.info(f"Batch ingesting {len(pdf_files)} files...")
    
    # Initialize pipeline
    pipeline = WeaviateIngestionPipeline()
    
    # Ingest batch
    results = pipeline.ingest_batch(pdf_files)
    
    # Check results
    success_count = sum(1 for r in results if r.status == "success")
    skipped_count = sum(1 for r in results if r.status == "skipped")
    error_count = sum(1 for r in results if r.status == "error")
    
    logger.info(f"\nBatch results:")
    logger.info(f"  Success: {success_count}")
    logger.info(f"  Skipped: {skipped_count}")
    logger.info(f"  Errors: {error_count}")
    
    if error_count > 0:
        logger.error(f"✗ Some files failed to ingest")
        for result in results:
            if result.status == "error":
                logger.error(f"  Error: {result.message}")
    
    pipeline.close()
    return error_count == 0


def run_all_tests():
    """Run all test cases."""
    logger.info("\n" + "=" * 70)
    logger.info("WEAVIATE INGESTION PIPELINE - TEST SUITE")
    logger.info("=" * 70 + "\n")
    
    tests = [
        ("Single File Ingestion", test_single_file_ingestion),
        ("Duplicate Detection", test_duplicate_detection),
        ("Vector Embeddings", test_vector_embeddings),
        ("Batch Ingestion", test_batch_ingestion)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results[test_name] = success
        except Exception as e:
            logger.error(f"Test '{test_name}' raised exception: {str(e)}", exc_info=True)
            results[test_name] = False
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("TEST SUMMARY")
    logger.info("=" * 70)
    
    for test_name, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        logger.info(f"{status}: {test_name}")
    
    total_tests = len(results)
    passed_tests = sum(1 for s in results.values() if s)
    
    logger.info(f"\nTotal: {passed_tests}/{total_tests} tests passed")
    logger.info("=" * 70)
    
    return passed_tests == total_tests


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Weaviate ingestion pipeline")
    parser.add_argument(
        "--test",
        choices=["single", "duplicate", "embeddings", "batch", "all"],
        default="all",
        help="Which test to run"
    )
    
    args = parser.parse_args()
    
    if args.test == "single":
        success = test_single_file_ingestion()
    elif args.test == "duplicate":
        success = test_duplicate_detection()
    elif args.test == "embeddings":
        success = test_vector_embeddings()
    elif args.test == "batch":
        success = test_batch_ingestion()
    else:
        success = run_all_tests()
    
    sys.exit(0 if success else 1)
