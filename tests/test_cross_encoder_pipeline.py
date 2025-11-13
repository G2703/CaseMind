#!/usr/bin/env python3
"""
Test script for the enhanced similarity pipeline with cross-encoder re-ranking.
"""

import os
import sys
from pathlib import Path

# Add src directory to path
sys.path.append(str(Path(__file__).parent / "src" / "similarity_pipeline"))

from similarity_search_pipeline import SimilarityCaseSearchPipeline

def test_cross_encoder_pipeline():
    """Test the pipeline with cross-encoder re-ranking."""
    
    # Set environment variables for testing
    os.environ['TOP_K_SIMILAR_CASES'] = '10'  # Get top 10 from cosine similarity
    os.environ['TOP_N_CROSS_ENCODER_RATIO'] = '0.5'  # Then get top 5 from cross-encoder
    os.environ['CROSS_ENCODER_MODEL'] = 'cross-encoder/ms-marco-MiniLM-L6-v2'
    
    # You'll need to set your OpenAI API key
    # os.environ['OPENAI_API_KEY'] = 'your-api-key-here'
    
    print("Testing Cross-Encoder Enhanced Similarity Pipeline")
    print("="*60)
    
    # Find a test PDF file
    cases_input_dir = Path("cases/input_files/Cases")
    pdf_files = list(cases_input_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in {cases_input_dir}")
        print("Please add a PDF file to test with.")
        return
    
    test_pdf = pdf_files[0]
    print(f"Using test PDF: {test_pdf}")
    
    try:
        # Initialize pipeline
        pipeline = SimilarityCaseSearchPipeline("config.json")
        
        print(f"Configuration:")
        print(f"  Top K (cosine similarity): {pipeline.top_k}")
        print(f"  Top N (cross-encoder): {pipeline.top_n}")
        print(f"  Cross-encoder model: {pipeline.cross_encoder_model_name}")
        
        # Run complete pipeline
        results = pipeline.run_complete_pipeline(str(test_pdf))
        
        print(f"\nPipeline completed successfully!")
        print(f"Returned {len(results)} cases with cross-encoder scores:")
        
        for i, (case_id, cosine_sim, cross_encoder_score) in enumerate(results, 1):
            print(f"{i}. {case_id}")
            print(f"   Cosine Similarity: {cosine_sim:.4f}")
            print(f"   Cross-Encoder Score: {cross_encoder_score:.4f}")
        
    except Exception as e:
        print(f"Error during pipeline execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_cross_encoder_pipeline()