"""
Quick validation test for CrossEncoder import and basic functionality.
"""

def test_cross_encoder_import():
    """Test that CrossEncoder can be imported and instantiated."""
    try:
        from sentence_transformers import CrossEncoder
        print("✓ CrossEncoder import successful")
        
        # Test model loading (this will download the model if not present)
        print("Loading cross-encoder model...")
        model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L6-v2")
        print("✓ CrossEncoder model loaded successfully")
        
        # Test basic prediction
        scores = model.predict([
            ("This is a test query", "This is a relevant document"),
            ("This is a test query", "This is not relevant")
        ])
        print(f"✓ CrossEncoder prediction test successful: {scores}")
        
        return True
        
    except ImportError as e:
        print(f"✗ CrossEncoder import failed: {e}")
        return False
    except Exception as e:
        print(f"✗ CrossEncoder test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_cross_encoder_import()
    if success:
        print("\n🎉 CrossEncoder validation completed successfully!")
    else:
        print("\n❌ CrossEncoder validation failed!")
        print("Make sure sentence-transformers is installed: pip install sentence-transformers")