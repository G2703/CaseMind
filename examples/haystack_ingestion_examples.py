"""
Example usage of HaystackIngestionPipeline.
Demonstrates how to use the pure Haystack pipeline for ingesting legal cases.
"""

import asyncio
import logging
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pipelines.haystack_ingestion_pipeline import HaystackIngestionPipeline
from core.models import ProcessingStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def example_single_ingestion():
    """Example: Ingest a single PDF file."""
    
    print("\n" + "="*70)
    print("EXAMPLE 1: Single File Ingestion")
    print("="*70 + "\n")
    
    # Initialize pipeline
    pipeline = HaystackIngestionPipeline()
    
    # Path to your PDF file
    pdf_path = Path("cases/sample_case.pdf")
    
    # Ingest the file
    result = await pipeline.ingest_single(pdf_path)
    
    # Display results
    print(f"Status: {result.status}")
    
    if result.status == ProcessingStatus.COMPLETED:
        print(f"✓ Successfully ingested!")
        print(f"  Case ID: {result.case_id}")
        print(f"  Title: {result.metadata.case_title}")
        print(f"  Court: {result.metadata.court_name}")
        print(f"  Most Appropriate Section: {result.metadata.most_appropriate_section}")
        
    elif result.status == ProcessingStatus.SKIPPED_DUPLICATE:
        print(f"⊘ Document already exists in database")
        
    else:
        print(f"✗ Ingestion failed: {result.error_message}")


async def example_batch_ingestion():
    """Example: Batch ingest multiple PDF files."""
    
    print("\n" + "="*70)
    print("EXAMPLE 2: Batch Ingestion")
    print("="*70 + "\n")
    
    # Initialize pipeline
    pipeline = HaystackIngestionPipeline()
    
    # Directory containing PDF files
    cases_dir = Path("cases/test_ingest")
    pdf_files = list(cases_dir.glob("*.pdf"))
    
    print(f"Found {len(pdf_files)} PDF files\n")
    
    # Statistics
    completed = 0
    duplicates = 0
    failed = 0
    
    # Process each file
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}] Processing: {pdf_file.name}")
        
        result = await pipeline.ingest_single(pdf_file)
        
        if result.status == ProcessingStatus.COMPLETED:
            completed += 1
            print(f"  ✓ Completed - {result.metadata.case_title}")
        elif result.status == ProcessingStatus.SKIPPED_DUPLICATE:
            duplicates += 1
            print(f"  ⊘ Duplicate")
        else:
            failed += 1
            print(f"  ✗ Failed: {result.error_message}")
    
    # Summary
    print("\n" + "-"*70)
    print(f"SUMMARY:")
    print(f"  Completed:  {completed}")
    print(f"  Duplicates: {duplicates}")
    print(f"  Failed:     {failed}")
    print("-"*70 + "\n")


async def example_pipeline_visualization():
    """Example: Visualize the pipeline structure."""
    
    print("\n" + "="*70)
    print("EXAMPLE 3: Pipeline Visualization")
    print("="*70 + "\n")
    
    # Initialize pipeline
    pipeline = HaystackIngestionPipeline()
    
    # Display pipeline structure
    print(pipeline.visualize_pipeline())


async def example_with_error_handling():
    """Example: Proper error handling."""
    
    print("\n" + "="*70)
    print("EXAMPLE 4: Error Handling")
    print("="*70 + "\n")
    
    pipeline = HaystackIngestionPipeline()
    
    pdf_path = Path("cases/test_case.pdf")
    
    try:
        result = await pipeline.ingest_single(pdf_path)
        
        if result.status == ProcessingStatus.COMPLETED:
            print("✓ Success!")
            
            # Access metadata safely
            if result.metadata:
                print(f"  Case: {result.metadata.case_title}")
                print(f"  Sections: {', '.join(result.metadata.sections_invoked)}")
            
            # Access facts summary
            if result.facts_summary:
                print(f"\n  Facts Summary:")
                print(f"  {result.facts_summary[:200]}...")
                
        elif result.status == ProcessingStatus.SKIPPED_DUPLICATE:
            print("⊘ Duplicate detected - skipping")
            
        else:
            print(f"✗ Failed: {result.error_message}")
            
    except FileNotFoundError:
        print(f"✗ Error: File not found - {pdf_path}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")


async def main():
    """Run all examples."""
    
    print("\n" + "="*70)
    print("HAYSTACK INGESTION PIPELINE - EXAMPLES")
    print("="*70)
    
    # Note: Update file paths before running
    print("\nNOTE: Update the file paths in this script before running")
    print("      - cases/sample_case.pdf")
    print("      - cases/input_files/\n")
    
    # Uncomment the examples you want to run:
    
    # await example_single_ingestion()
    # await example_batch_ingestion()
    await example_pipeline_visualization()
    # await example_with_error_handling()


if __name__ == "__main__":
    asyncio.run(main())
