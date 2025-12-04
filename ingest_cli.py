"""
Simple CLI for Weaviate ingestion pipeline.
Quick and easy ingestion of legal case documents using Haystack.

Features:
- Progress bars for batch and single file processing
- Failure tracking with retry capability
- Comprehensive reporting (JSON + human-readable text)
- Automatic rollback on partial failures
"""

import sys
import os
from pathlib import Path
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.pipelines.weaviate_ingestion_pipeline import create_weaviate_ingestion_pipeline
from src.utils.logger import get_logger
from src.utils.failure_tracker import FailureTracker
from src.utils.report_generator import ReportGenerator
from src.utils.progress_tracker import ProgressTracker, SingleFileProgressTracker

logger = get_logger(__name__)


def ingest_file(file_path: str):
    """Ingest a single PDF or markdown file."""
    file_path = Path(file_path)
    
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return False
    
    logger.info(f"Ingesting file: {file_path.name}")
    
    # Create Haystack pipeline
    pipeline = create_weaviate_ingestion_pipeline()
    
    # Initialize trackers
    failure_tracker = FailureTracker()
    
    # Progress bar for single file
    with SingleFileProgressTracker(file_path.name, disable=False) as progress:
        # Run pipeline
        result = pipeline.run({
            "pdf_converter": {"file_paths": [file_path]}
        })
        
        # Extract results
        results = result.get("weaviate_writer", {}).get("results", [])
        
        if not results:
            logger.error(f"✗ Failed: No results from pipeline")
            return False
        
        res = results[0]
        status = res.get("status", "error")
        
        if status == "success":
            logger.info(f"✓ Success!")
            logger.info(f"  File ID: {res.get('file_id', '')}")
            logger.info(f"  Sections: {res.get('sections_count', 0)}")
            logger.info(f"  Chunks: {res.get('chunks_count', 0)}")
            
            # Clear from failures if previously failed
            failure_tracker.record_success(file_path)
            progress.complete()
            
        elif status == "skipped":
            logger.warning(f"⊘ Skipped: {res.get('message', '')}")
            progress.complete()
            
        else:
            logger.error(f"✗ Failed: {res.get('message', '')}")
            
            # Record failure
            error_details = res.get("error_details", {})
            stage = error_details.get("stage", "unknown")
            error = res.get("message", "Unknown error")
            
            should_retry = failure_tracker.record_failure(file_path, stage, error)
            
            if not should_retry:
                logger.error(f"  Max retry attempts reached ({failure_tracker.max_attempts})")
            else:
                attempts = failure_tracker.get_attempt_count(file_path)
                logger.info(f"  Attempt {attempts}/{failure_tracker.max_attempts}")
    
    return status == "success"


def ingest_directory(directory: str, pattern: str = "*.pdf", retry_failed: bool = False):
    """Ingest all matching files in a directory."""
    directory = Path(directory)
    
    if not directory.exists():
        logger.error(f"Directory not found: {directory}")
        return False
    
    # Initialize trackers
    failure_tracker = FailureTracker()
    report_generator = ReportGenerator()
    
    # Get files to process
    if retry_failed:
        # Only process previously failed files
        files = failure_tracker.get_retryable_files(directory)
        if not files:
            logger.info(f"No failed files to retry in {directory}")
            return True
        logger.info(f"Retrying {len(files)} previously failed files")
    else:
        # Process all matching files
        files = list(directory.glob(pattern))
    
    if not files:
        logger.warning(f"No files matching '{pattern}' found in {directory}")
        return False
    
    logger.info(f"Found {len(files)} files to ingest")
    
    # Create Haystack pipeline
    pipeline = create_weaviate_ingestion_pipeline()
    
    # Progress tracking
    with ProgressTracker(total_files=len(files)) as progress:
        progress.start_batch(f"Processing {len(files)} files")
        
        # Run pipeline with all files
        result = pipeline.run({
            "pdf_converter": {"file_paths": files}
        })
        
        # Extract results
        results_data = result.get("weaviate_writer", {}).get("results", [])
        
        # Process each result
        for res, file_path in zip(results_data, files):
            status = res.get("status", "error")
            
            if status == "success":
                # Clear from failures
                failure_tracker.record_success(file_path)
                progress.complete_file()
                
            elif status == "skipped":
                progress.complete_file()
                
            else:
                # Record failure
                error_details = res.get("error_details", {})
                stage = error_details.get("stage", "unknown")
                error = res.get("message", "Unknown error")
                
                failure_tracker.record_failure(file_path, stage, error)
                progress.fail_file()
    
    # Generate report
    report = report_generator.generate_report(results_data, str(directory), save=True)
    
    # Print summary
    report_generator.print_summary(report)
    
    # Show failure statistics
    failure_summary = failure_tracker.get_summary()
    if failure_summary['total_failures'] > 0:
        logger.info(f"\nFailure tracking:")
        logger.info(f"  Total failures: {failure_summary['total_failures']}")
        logger.info(f"  Retryable: {failure_summary['retryable']}")
        logger.info(f"  Max attempts reached: {failure_summary['max_attempts_reached']}")
        
        if retry_failed and failure_summary['retryable'] > 0:
            logger.info(f"\nTo retry failed files again, run:")
            logger.info(f"  python ingest_cli.py ingest --directory {directory} --retry-failed")
    
    return report['failed'] == 0


def verify_file(file_id: str):
    """Verify ingestion of a specific file."""
    from src.infrastructure.weaviate_client import WeaviateClient
    from weaviate.classes.query import Filter
    
    logger.info(f"Verifying file_id: {file_id}")
    
    client_wrapper = WeaviateClient()
    client = client_wrapper.client
    
    counts = {
        "documents": 0,
        "metadata": 0,
        "sections": 0,
        "chunks": 0
    }
    
    try:
        # Count in each collection
        doc_collection = client.collections.get("CaseDocuments")
        doc_result = doc_collection.query.fetch_objects(
            filters=Filter.by_property("file_id").equal(file_id),
            limit=1
        )
        counts["documents"] = len(doc_result.objects)
        
        metadata_collection = client.collections.get("CaseMetadata")
        metadata_result = metadata_collection.query.fetch_objects(
            filters=Filter.by_property("file_id").equal(file_id),
            limit=1
        )
        counts["metadata"] = len(metadata_result.objects)
        
        sections_collection = client.collections.get("CaseSections")
        sections_result = sections_collection.aggregate.over_all(
            filters=Filter.by_property("file_id").equal(file_id)
        )
        counts["sections"] = sections_result.total_count
        
        chunks_collection = client.collections.get("CaseChunks")
        chunks_result = chunks_collection.aggregate.over_all(
            filters=Filter.by_property("file_id").equal(file_id)
        )
        counts["chunks"] = chunks_result.total_count
        
        logger.info(f"Verification results:")
        logger.info(f"  Documents: {counts['documents']}")
        logger.info(f"  Metadata: {counts['metadata']}")
        logger.info(f"  Sections: {counts['sections']}")
        logger.info(f"  Chunks: {counts['chunks']}")
        
        # Check expected ratio (1:1:9:N)
        if counts['documents'] == 1 and counts['metadata'] == 1:
            logger.info(f"✓ Document and metadata counts correct")
        else:
            logger.warning(f"⚠ Unexpected document/metadata counts")
        
        if counts['sections'] > 0:
            logger.info(f"✓ Sections found")
        else:
            logger.warning(f"⚠ No sections found")
        
        if counts['chunks'] > 0:
            logger.info(f"✓ Chunks found")
        else:
            logger.warning(f"⚠ No chunks found")
        
    finally:
        client_wrapper.close()
    
    return True


def search_sections(query: str, limit: int = 5):
    """Search sections semantically."""
    from src.infrastructure.weaviate_client import WeaviateClient
    from src.core.config import Config
    
    logger.info(f"Searching sections for: '{query}'")
    
    client_wrapper = WeaviateClient()
    client = client_wrapper.client
    
    sections = client.collections.get("CaseSections")
    results = sections.query.near_text(query=query, limit=limit)
    
    logger.info(f"\nFound {len(results.objects)} results:")
    logger.info("=" * 70)
    
    for i, obj in enumerate(results.objects, 1):
        section_name = obj.properties.get("section_name", "unknown")
        file_id = obj.properties.get("file_id", "unknown")
        text = obj.properties.get("text", "")
        
        logger.info(f"\n{i}. Section: {section_name} (File: {file_id[:8]}...)")
        logger.info(f"   {text[:200]}{'...' if len(text) > 200 else ''}")
    
    logger.info("=" * 70)
    client_wrapper.close()
    return True


def main():
    parser = argparse.ArgumentParser(
        description="CaseMind Weaviate Ingestion CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Ingest single file
  python ingest_cli.py ingest --file cases/input_files/case1.pdf
  
  # Ingest directory
  python ingest_cli.py ingest --directory cases/input_files
  
  # Ingest with pattern
  python ingest_cli.py ingest --directory cases/input_files --pattern "*.pdf"
  
  # Retry only failed files
  python ingest_cli.py ingest --directory cases/input_files --retry-failed
  
  # Verify ingestion
  python ingest_cli.py verify --file-id abc123...
  
  # Search sections
  python ingest_cli.py search --query "what are the facts of the case" --limit 10
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest files into Weaviate")
    ingest_group = ingest_parser.add_mutually_exclusive_group(required=True)
    ingest_group.add_argument("--file", help="Single file to ingest")
    ingest_group.add_argument("--directory", help="Directory of files to ingest")
    ingest_parser.add_argument("--pattern", default="*.pdf", help="File pattern (default: *.pdf)")
    ingest_parser.add_argument("--retry-failed", action="store_true", 
                              help="Retry only previously failed files in the directory")
    
    # Verify command
    verify_parser = subparsers.add_parser("verify", help="Verify ingestion of a file")
    verify_parser.add_argument("--file-id", required=True, help="File ID to verify")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search sections semantically")
    search_parser.add_argument("--query", required=True, help="Search query")
    search_parser.add_argument("--limit", type=int, default=5, help="Number of results (default: 5)")
    
    args = parser.parse_args()
    
    if args.command == "ingest":
        if args.file:
            success = ingest_file(args.file)
        else:
            success = ingest_directory(args.directory, args.pattern, args.retry_failed)
        sys.exit(0 if success else 1)
    
    elif args.command == "verify":
        success = verify_file(args.file_id)
        sys.exit(0 if success else 1)
    
    elif args.command == "search":
        success = search_sections(args.query, args.limit)
        sys.exit(0 if success else 1)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
