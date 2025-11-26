"""
Test script for the optimized ingestion pipeline.
Run this to verify the new pipeline works correctly.
"""

import asyncio
import sys
from pathlib import Path

# Add src directory to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from pipelines.haystack_ingestion_pipeline import HaystackIngestionPipeline
from core.models import ProcessingStatus


async def test_pipeline():
    """Test the optimized ingestion pipeline."""
    print("=" * 80)
    print("TESTING OPTIMIZED INGESTION PIPELINE")
    print("=" * 80)
    
    # Initialize pipeline
    print("\n[1] Initializing pipeline...")
    try:
        pipeline = HaystackIngestionPipeline()
        print("✓ Pipeline initialized successfully")
        print(f"✓ Database connection established")
        print(f"✓ legal_cases table created/verified")
    except Exception as e:
        print(f"✗ Pipeline initialization failed: {e}")
        return
    
    # Visualize pipeline
    print("\n[2] Pipeline architecture:")
    try:
        viz = pipeline.visualize_pipeline()
        print(viz)
    except Exception as e:
        print(f"Note: Pipeline visualization not available: {e}")
    
    # Test with a sample PDF (you'll need to provide a path)
    print("\n[3] Testing ingestion...")
    print("Please provide the path to a test PDF file:")
    print("(Or press Enter to skip ingestion test)")
    
    pdf_path = input("PDF path: ").strip()
    
    if not pdf_path:
        print("Skipping ingestion test")
        return
    
    if not Path(pdf_path).exists():
        print(f"✗ File not found: {pdf_path}")
        return
    
    print(f"\n[4] Ingesting: {pdf_path}")
    try:
        result = await pipeline.ingest_single(Path(pdf_path))
        
        print("\n" + "=" * 80)
        print("INGESTION RESULT")
        print("=" * 80)
        print(f"Status: {result.status}")
        print(f"Case ID: {result.case_id}")
        print(f"Document ID: {result.document_id}")
        
        if result.metadata:
            print(f"\nMetadata:")
            print(f"  Case Title: {result.metadata.case_title}")
            print(f"  Court: {result.metadata.court_name}")
            print(f"  Date: {result.metadata.judgment_date}")
            print(f"  Sections Invoked: {result.metadata.sections_invoked}")
            print(f"  Most Appropriate: {result.metadata.most_appropriate_section}")
        
        if result.status == ProcessingStatus.COMPLETED:
            print("\n✓ Ingestion completed successfully!")
            print(f"  Facts summary length: {len(result.facts_summary)} characters")
        elif result.status == ProcessingStatus.SKIPPED_DUPLICATE:
            print("\n⚠ Document is a duplicate")
        elif result.status == ProcessingStatus.FAILED:
            print(f"\n✗ Ingestion failed: {result.error_message}")
        
    except Exception as e:
        print(f"\n✗ Ingestion error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


async def verify_database():
    """Verify the legal_cases table structure."""
    print("\n" + "=" * 80)
    print("VERIFYING DATABASE SCHEMA")
    print("=" * 80)
    
    try:
        from core.config import Config
        import psycopg2
        
        config = Config()
        conn_str = f"postgresql://{config.db_user}:{config.db_password}@{config.db_host}:{config.db_port}/{config.db_name}"
        conn = psycopg2.connect(conn_str)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'legal_cases'
            );
        """)
        
        exists = cursor.fetchone()[0]
        
        if exists:
            print("✓ legal_cases table exists")
            
            # Get column info
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'legal_cases'
                ORDER BY ordinal_position;
            """)
            
            columns = cursor.fetchall()
            print(f"✓ Table has {len(columns)} columns:")
            for col_name, col_type in columns:
                print(f"  - {col_name}: {col_type}")
            
            # Count documents
            cursor.execute("SELECT COUNT(*) FROM legal_cases;")
            count = cursor.fetchone()[0]
            print(f"\n✓ Total cases in database: {count}")
            
        else:
            print("✗ legal_cases table does not exist")
            print("  It will be created when you run the pipeline for the first time")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"✗ Database verification failed: {e}")


if __name__ == "__main__":
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "CaseMind Optimized Pipeline Test" + " " * 25 + "║")
    print("╚" + "═" * 78 + "╝")
    
    # Run verification
    asyncio.run(verify_database())
    
    # Run test
    asyncio.run(test_pipeline())
