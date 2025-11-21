"""
Example usage of PureHaystackSimilarityPipeline.
Demonstrates similarity search with pure Haystack components.
"""

import asyncio
import logging
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pipelines.pure_haystack_similarity_pipeline import PureHaystackSimilarityPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def example_basic_search():
    """Example: Basic similarity search."""
    
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic Similarity Search")
    print("="*70 + "\n")
    
    # Initialize pipeline
    pipeline = PureHaystackSimilarityPipeline()
    
    # Path to query PDF
    query_pdf = Path("cases/query_case.pdf")
    
    # Search for similar cases
    result = await pipeline.search_similar(query_pdf)
    
    # Display results
    if result.error_message:
        print(f"✗ Error: {result.error_message}")
        return
    
    print(f"Query: {result.query_file}")
    print(f"Found {result.total_above_threshold} similar cases\n")
    
    for i, case in enumerate(result.similar_cases, 1):
        print(f"{i}. {case.case_title}")
        print(f"   Cosine Similarity: {case.cosine_similarity:.4f}")
        print(f"   Cross-Encoder: {case.cross_encoder_score:.4f}\n")


async def example_metadata_search():
    """Example: Search using metadata instead of facts."""
    
    print("\n" + "="*70)
    print("EXAMPLE 2: Metadata-Based Search")
    print("="*70 + "\n")
    
    pipeline = PureHaystackSimilarityPipeline()
    
    query_pdf = Path("cases/query_case.pdf")
    
    # Search using metadata (sections, court, title)
    result = await pipeline.search_similar(
        query_pdf,
        use_metadata_query=True
    )
    
    print(f"Search Mode: {result.search_mode}")
    print(f"Similar Cases: {result.total_above_threshold}\n")
    
    for case in result.similar_cases:
        print(f"- {case.case_title}")
        print(f"  Sections: {', '.join(case.sections_invoked)}")
        print(f"  Score: {case.cross_encoder_score:.4f}\n")


async def example_pipeline_visualization():
    """Example: Visualize the pipeline structure."""
    
    print("\n" + "="*70)
    print("EXAMPLE 3: Pipeline Visualization")
    print("="*70 + "\n")
    
    pipeline = PureHaystackSimilarityPipeline()
    
    # Display pipeline graph
    print(pipeline.visualize_pipeline())


async def example_batch_search():
    """Example: Search multiple query documents."""
    
    print("\n" + "="*70)
    print("EXAMPLE 4: Batch Similarity Search")
    print("="*70 + "\n")
    
    pipeline = PureHaystackSimilarityPipeline()
    
    # Multiple query files
    query_files = [
        Path("cases/query1.pdf"),
        Path("cases/query2.pdf"),
        Path("cases/query3.pdf")
    ]
    
    for query_file in query_files:
        if not query_file.exists():
            print(f"⊘ Skipping {query_file.name} (not found)")
            continue
        
        print(f"\nSearching: {query_file.name}")
        result = await pipeline.search_similar(query_file)
        
        print(f"  Found: {result.total_above_threshold} similar cases")
        
        if result.similar_cases:
            top_case = result.similar_cases[0]
            print(f"  Top Match: {top_case.case_title}")
            print(f"  Score: {top_case.cross_encoder_score:.4f}")


async def example_with_threshold():
    """Example: Using custom threshold."""
    
    print("\n" + "="*70)
    print("EXAMPLE 5: Custom Threshold")
    print("="*70 + "\n")
    
    # Note: Threshold is set in .env file (CROSS_ENCODER_THRESHOLD)
    # For dynamic threshold, you'd need to modify the pipeline
    
    pipeline = PureHaystackSimilarityPipeline()
    
    query_pdf = Path("cases/query_case.pdf")
    result = await pipeline.search_similar(query_pdf)
    
    print(f"Threshold: {pipeline.threshold}")
    print(f"Cases above threshold: {result.total_above_threshold}\n")
    
    for case in result.similar_cases:
        print(f"- {case.case_title}: {case.cross_encoder_score:.4f}")


async def main():
    """Run all examples."""
    
    print("\n" + "="*70)
    print("PURE HAYSTACK SIMILARITY PIPELINE - EXAMPLES")
    print("="*70)
    
    print("\nNOTE: Update the file paths in this script before running")
    print("      - cases/query_case.pdf")
    print("      - cases/query1.pdf, query2.pdf, query3.pdf\n")
    
    # Uncomment the examples you want to run:
    
    # await example_basic_search()
    # await example_metadata_search()
    await example_pipeline_visualization()
    # await example_batch_search()
    # await example_with_threshold()


if __name__ == "__main__":
    asyncio.run(main())
