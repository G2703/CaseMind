"""
Simple test for the simplified case embedder
"""

import sys
import os
sys.path.append('src')

from case_embedder import CaseEmbedder
import json

def test_simple_embedder():
    """Test the simplified case embedder."""
    print("="*60)
    print("TESTING SIMPLIFIED CASE EMBEDDER")
    print("="*60)
    
    try:
        # Initialize embedder
        print("1. Initializing embedder...")
        embedder = CaseEmbedder(model_name='all-mpnet-base-v2')
        print("✅ Embedder initialized successfully")
        
        # Test with a sample case file
        print("\n2. Testing embedding generation...")
        case_file = 'cases/extracted/Aakash Ramchandra Chavan Vs. State of Maharashtra_facts.json'
        
        if os.path.exists(case_file):
            result = embedder.embed_case_file(case_file)
            print(f"✅ Successfully embedded case: {result['case_id']}")
            print(f"   - Embedding dimension: {result['embedding_dimension']}")
            print(f"   - Text length: {len(result['case_text'])}")
            
            # Show sample of the raw JSON text
            print(f"\n3. Sample of embedded text:")
            print(f"   {result['case_text'][:200]}...")
            
            # Save embeddings
            print(f"\n4. Saving embeddings...")
            saved_files = embedder.save_embeddings('simple_test')
            print("✅ Saved embedding files:")
            for file_type, path in saved_files.items():
                print(f"   - {file_type}: {path}")
            
            # Get summary
            print(f"\n5. Embedding summary:")
            summary = embedder.get_embedding_summary()
            print(f"   - Total cases: {summary['total_cases']}")
            print(f"   - Model used: {summary['model_name']}")  
            print(f"   - Embedding dimension: {summary['embedding_dimension']}")
            print(f"   - Average text length: {summary['text_statistics']['avg_length']:.0f}")
            
        else:
            print(f"❌ Test case file not found: {case_file}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple_embedder()
    print("\n" + "="*60)
    print("SIMPLE EMBEDDING TEST COMPLETED")
    print("="*60)