"""
Cleanup Orphans - Database Consistency Tool
Finds and removes inconsistent records from Weaviate collections.

Use cases:
- Remove partial ingestions after failures
- Verify database consistency
- Cleanup specific files
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.infrastructure.weaviate_client import WeaviateClient
from weaviate.classes.query import Filter


def cleanup_file(file_id: str):
    """
    Remove all records for a specific file_id from all collections.
    
    Args:
        file_id: File ID to remove
    """
    print(f"Cleaning up file_id: {file_id}")
    
    client_wrapper = WeaviateClient()
    client = client_wrapper.client
    
    collections = ["CaseDocuments", "CaseMetadata", "CaseSections", "CaseChunks"]
    
    try:
        for collection_name in collections:
            collection = client.collections.get(collection_name)
            
            # Count before deletion
            before = collection.aggregate.over_all(
                filters=Filter.by_property("file_id").equal(file_id)
            )
            before_count = before.total_count
            
            # Delete all objects with this file_id
            if before_count > 0:
                collection.data.delete_many(
                    where=Filter.by_property("file_id").equal(file_id)
                )
                print(f"  ✓ Deleted {before_count} records from {collection_name}")
            else:
                print(f"  - No records in {collection_name}")
        
        print(f"\n✓ Cleanup complete for file_id: {file_id}")
        
    except Exception as e:
        print(f"\n✗ Cleanup failed: {e}")
        return False
    
    finally:
        client_wrapper.close()
    
    return True


def verify_consistency():
    """
    Verify database consistency.
    Checks that all file_ids have records in all 4 collections.
    """
    print("Verifying database consistency...\n")
    
    client_wrapper = WeaviateClient()
    client = client_wrapper.client
    
    try:
        # Get all file_ids from CaseDocuments
        doc_collection = client.collections.get("CaseDocuments")
        all_docs = doc_collection.query.fetch_objects(limit=10000)
        
        file_ids = set()
        for doc in all_docs.objects:
            file_id = doc.properties.get("file_id")
            if file_id:
                file_ids.add(file_id)
        
        print(f"Found {len(file_ids)} file_ids in CaseDocuments\n")
        
        # Check each file_id
        inconsistent = []
        
        for file_id in file_ids:
            counts = {
                "documents": 0,
                "metadata": 0,
                "sections": 0,
                "chunks": 0
            }
            
            # Count in each collection
            doc_result = client.collections.get("CaseDocuments").aggregate.over_all(
                filters=Filter.by_property("file_id").equal(file_id)
            )
            counts["documents"] = doc_result.total_count
            
            metadata_result = client.collections.get("CaseMetadata").aggregate.over_all(
                filters=Filter.by_property("file_id").equal(file_id)
            )
            counts["metadata"] = metadata_result.total_count
            
            sections_result = client.collections.get("CaseSections").aggregate.over_all(
                filters=Filter.by_property("file_id").equal(file_id)
            )
            counts["sections"] = sections_result.total_count
            
            chunks_result = client.collections.get("CaseChunks").aggregate.over_all(
                filters=Filter.by_property("file_id").equal(file_id)
            )
            counts["chunks"] = chunks_result.total_count
            
            # Check for expected ratio (1:1:N:N where N > 0)
            is_consistent = (
                counts["documents"] == 1 and
                counts["metadata"] == 1 and
                counts["sections"] > 0 and
                counts["chunks"] > 0
            )
            
            if not is_consistent:
                inconsistent.append({
                    "file_id": file_id,
                    "counts": counts
                })
        
        # Report results
        if not inconsistent:
            print("✓ All file_ids are consistent!")
            print(f"  {len(file_ids)} files verified")
        else:
            print(f"✗ Found {len(inconsistent)} inconsistent file_ids:\n")
            
            for item in inconsistent:
                print(f"File ID: {item['file_id'][:16]}...")
                print(f"  Documents: {item['counts']['documents']}")
                print(f"  Metadata:  {item['counts']['metadata']}")
                print(f"  Sections:  {item['counts']['sections']}")
                print(f"  Chunks:    {item['counts']['chunks']}")
                print()
            
            print(f"\nTo cleanup these files, run:")
            for item in inconsistent:
                print(f"  python cleanup_orphans.py --file-id {item['file_id']}")
        
        return len(inconsistent) == 0
    
    except Exception as e:
        print(f"\n✗ Verification failed: {e}")
        return False
    
    finally:
        client_wrapper.close()


def list_all_files():
    """List all file_ids in the database with counts."""
    print("Listing all files in database...\n")
    
    client_wrapper = WeaviateClient()
    client = client_wrapper.client
    
    try:
        # Get all file_ids from CaseDocuments
        doc_collection = client.collections.get("CaseDocuments")
        all_docs = doc_collection.query.fetch_objects(limit=10000)
        
        print(f"{'File ID':<40} {'Original Filename':<50} {'Sections':<10} {'Chunks':<10}")
        print("-" * 110)
        
        for doc in all_docs.objects:
            file_id = doc.properties.get("file_id", "")
            filename = doc.properties.get("original_filename", "Unknown")
            
            # Count sections and chunks
            sections_result = client.collections.get("CaseSections").aggregate.over_all(
                filters=Filter.by_property("file_id").equal(file_id)
            )
            sections_count = sections_result.total_count
            
            chunks_result = client.collections.get("CaseChunks").aggregate.over_all(
                filters=Filter.by_property("file_id").equal(file_id)
            )
            chunks_count = chunks_result.total_count
            
            print(f"{file_id:<40} {filename:<50} {sections_count:<10} {chunks_count:<10}")
        
        print(f"\nTotal files: {len(all_docs.objects)}")
        
    except Exception as e:
        print(f"\n✗ List failed: {e}")
        return False
    
    finally:
        client_wrapper.close()
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Cleanup Orphans - Database Consistency Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Verify database consistency
  python cleanup_orphans.py --verify
  
  # List all files
  python cleanup_orphans.py --list
  
  # Cleanup specific file
  python cleanup_orphans.py --file-id abc123...
        """
    )
    
    parser.add_argument("--verify", action="store_true", 
                       help="Verify database consistency")
    parser.add_argument("--list", action="store_true",
                       help="List all files in database")
    parser.add_argument("--file-id", 
                       help="Cleanup specific file by ID")
    
    args = parser.parse_args()
    
    if args.verify:
        success = verify_consistency()
        sys.exit(0 if success else 1)
    
    elif args.list:
        success = list_all_files()
        sys.exit(0 if success else 1)
    
    elif args.file_id:
        success = cleanup_file(args.file_id)
        sys.exit(0 if success else 1)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
