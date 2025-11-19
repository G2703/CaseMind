#!/usr/bin/env python3
"""
Test script for the threshold-based cross-encoder filtering.
"""

import os
import sys
from pathlib import Path

# Add src directory to path
sys.path.append(str(Path(__file__).parent / "src" / "similarity_pipeline"))

def test_threshold_filtering():
    """Test the pipeline with different threshold values."""
    
    print("Testing Threshold-Based Cross-Encoder Filtering")
    print("="*60)
    
    # Test different threshold values
    threshold_values = [0.0, 1.0, 2.0, 5.0]
    
    for threshold in threshold_values:
        print(f"\n{'='*50}")
        print(f"TESTING WITH THRESHOLD: {threshold}")
        print(f"{'='*50}")
        
        # Set environment variables
        os.environ['TOP_K_SIMILAR_CASES'] = '10'
        os.environ['CROSS_ENCODER_THRESHOLD'] = str(threshold)
        os.environ['CROSS_ENCODER_MODEL'] = 'cross-encoder/ms-marco-MiniLM-L6-v2'
        
        try:
            from similarity_search_pipeline import SimilarityCaseSearchPipeline
            
            # Find a test PDF file
            cases_input_dir = Path("cases/input_files/Cases")
            pdf_files = list(cases_input_dir.glob("**/*.pdf"))
            
            if not pdf_files:
                print(f"No PDF files found in {cases_input_dir}")
                continue
            
            test_pdf = pdf_files[0]
            print(f"Using test PDF: {test_pdf.name}")
            
            # Initialize pipeline
            pipeline = SimilarityCaseSearchPipeline("config.json")
            
            print(f"Configuration:")
            print(f"  Top K (cosine similarity): {pipeline.top_k}")
            print(f"  Cross-encoder threshold: {pipeline.cross_encoder_threshold}")
            print(f"  Cross-encoder model: {pipeline.cross_encoder_model_name}")
            
            # Run pipeline
            results = pipeline.run_complete_pipeline(str(test_pdf))
            
            print(f"\n📊 RESULTS SUMMARY:")
            print(f"   Cases above threshold ({threshold}): {len(results)}")
            
            if results:
                print(f"   Highest cross-encoder score: {max(r[2] for r in results):.4f}")
                print(f"   Lowest cross-encoder score: {min(r[2] for r in results):.4f}")
            else:
                print("   No cases found above threshold")
            
        except Exception as e:
            print(f"Error during pipeline execution: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_threshold_filtering()