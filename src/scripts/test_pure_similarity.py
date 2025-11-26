"""
Test script for Pure Haystack Similarity Pipeline.
Tests similarity search with pure Haystack components.
"""

import asyncio
import logging
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipelines.pure_haystack_similarity_pipeline import PureHaystackSimilarityPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_similarity_search():
    """Test similarity search with a query PDF."""
    
    # Initialize pipeline
    logger.info("Initializing Pure Haystack Similarity Pipeline...")
    pipeline = PureHaystackSimilarityPipeline()
    
    # Visualize pipeline structure
    logger.info("\n" + "="*60)
    logger.info("PIPELINE STRUCTURE:")
    logger.info("="*60)
    print(pipeline.visualize_pipeline())
    logger.info("="*60 + "\n")
    
    # Test file path (update this to your test PDF)
    query_file = Path("cases/query_case.pdf")
    
    if not query_file.exists():
        logger.error(f"Query file not found: {query_file}")
        logger.info("Please update the query_file path in the script")
        return
    
    # Run similarity search
    logger.info(f"Searching for cases similar to: {query_file.name}")
    result = await pipeline.search_similar(query_file)
    
    # Display results
    logger.info("\n" + "="*60)
    logger.info("SIMILARITY SEARCH RESULTS:")
    logger.info("="*60)
    
    if result.error_message:
        logger.error(f"Error: {result.error_message}")
        return
    
    logger.info(f"Query File: {result.query_file}")
    logger.info(f"Search Mode: {result.search_mode}")
    logger.info(f"Total Similar Cases: {result.total_above_threshold}")
    
    if result.input_case and result.input_case.metadata:
        logger.info(f"\nQuery Case:")
        logger.info(f"  Title: {result.input_case.metadata.case_title}")
        logger.info(f"  Court: {result.input_case.metadata.court_name}")
        logger.info(f"  Most Appropriate Section: {result.input_case.metadata.most_appropriate_section}")
    
    logger.info(f"\nSimilar Cases Found:")
    logger.info("-" * 60)
    
    for i, case in enumerate(result.similar_cases, 1):
        logger.info(f"\n{i}. {case.case_title}")
        logger.info(f"   Court: {case.court_name}")
        logger.info(f"   Date: {case.judgment_date}")
        logger.info(f"   Cosine Similarity: {case.cosine_similarity:.4f}")
        logger.info(f"   Cross-Encoder Score: {case.cross_encoder_score:.4f}")
        logger.info(f"   Sections: {', '.join(case.sections_invoked[:3])}...")
        logger.info(f"   Facts: {case.facts_summary[:150]}...")
    
    logger.info("\n" + "="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(test_similarity_search())
